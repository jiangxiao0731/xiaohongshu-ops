#!/usr/bin/env python3
"""
TD Video Auto-Music Tool

Watches ~/Desktop/td/export/ for new .mov files, analyzes video mood via
Claude Vision, generates matching ambient music via Suno API, and outputs
ready-to-upload .mp4 files with fade in/out.

Usage:
    python3 add_music.py <file.mov>          # process single file
    python3 add_music.py --watch             # watch folder mode
    python3 add_music.py --dry-run <file.mov> # mood analysis only, no Suno
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

# Bootstrap: load .env before anything else
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_env, send_notification

load_env()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FFMPEG = Path.home() / "bin" / "ffmpeg"
FFPROBE = Path.home() / "bin" / "ffprobe"
EXPORT_DIR = Path.home() / "Desktop" / "td" / "export"
READY_DIR = EXPORT_DIR / "ready"
PROCESSED_FILE = EXPORT_DIR / ".processed.json"
PROJECT_DIR = Path.home() / "claude" / "xiaohongshu-ops"
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SUNO_API_KEY = os.environ.get("SUNO_API_KEY", "")
SUNO_BASE_URL = "https://api.sunoapi.org"

WATCH_INTERVAL = 30  # seconds
FADE_DURATION = 2  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "add_music.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            str(FFPROBE),
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def detect_visual_changes(video_path: Path, threshold: float = 0.03) -> list[dict]:
    """Detect visual change points in the video using ffmpeg scene detection.

    Returns a list of dicts with 'time' (seconds) and 'score' (change intensity 0-1).
    """
    result = subprocess.run(
        [
            str(FFMPEG),
            "-i", str(video_path),
            "-vf", f"select='gte(scene,{threshold})',metadata=print:file=-",
            "-an", "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )

    changes = []
    current_time = None
    for line in result.stderr.splitlines() + result.stdout.splitlines():
        if "pts_time:" in line:
            try:
                current_time = float(line.split("pts_time:")[1].split()[0])
            except (IndexError, ValueError):
                pass
        if "lavfi.scene_score=" in line and current_time is not None:
            try:
                score = float(line.split("lavfi.scene_score=")[1].strip())
                changes.append({"time": round(current_time, 2), "score": round(score, 3)})
                current_time = None
            except (IndexError, ValueError):
                pass

    logger.info("Detected %d visual change points", len(changes))
    return changes


def extract_keyframes(video_path: Path, n: int = 4,
                      change_points: Optional[list[dict]] = None) -> list[Path]:
    """Extract keyframes from video -- at change points if available, else evenly-spaced."""
    duration = get_video_duration(video_path)
    tmpdir = Path(tempfile.mkdtemp(prefix="td_frames_"))
    frames = []

    # Pick timestamps: prefer visual change points, fill with evenly-spaced
    if change_points and len(change_points) >= n:
        # Take the N strongest change points
        sorted_changes = sorted(change_points, key=lambda c: c["score"], reverse=True)[:n]
        timestamps = sorted([c["time"] for c in sorted_changes])
    elif change_points:
        # Use all change points + fill remaining with evenly-spaced
        timestamps = [c["time"] for c in change_points]
        remaining = n - len(timestamps)
        for i in range(remaining):
            t = duration * (i + 1) / (remaining + 1)
            timestamps.append(t)
        timestamps = sorted(set(timestamps))[:n]
    else:
        timestamps = [duration * (i + 1) / (n + 1) for i in range(n)]

    for i, t in enumerate(timestamps):
        out_path = tmpdir / f"frame_{i:02d}.jpg"
        subprocess.run(
            [
                str(FFMPEG),
                "-ss", str(t),
                "-i", str(video_path),
                "-vframes", "1",
                "-vf", "scale='min(1280,iw)':'-1'",
                "-q:v", "5",
                str(out_path),
            ],
            capture_output=True,
        )
        if out_path.exists():
            frames.append(out_path)

    logger.info("Extracted %d keyframes from %s", len(frames), video_path.name)
    return frames


def _format_rhythm_analysis(duration: float, changes: list[dict]) -> str:
    """Format visual change data into a rhythm description for the music prompt."""
    if not changes:
        return "No significant visual transitions detected; the video has smooth, continuous motion."

    # Calculate average interval between changes
    times = [c["time"] for c in changes]
    if len(times) >= 2:
        intervals = [times[i + 1] - times[i] for i in range(len(times) - 1)]
        avg_interval = sum(intervals) / len(intervals)
        implied_bpm = round(60 / avg_interval) if avg_interval > 0 else 0
    else:
        avg_interval = duration
        implied_bpm = 0

    # Identify strong vs subtle changes
    strong = [c for c in changes if c["score"] > 0.3]
    medium = [c for c in changes if 0.15 <= c["score"] <= 0.3]

    lines = [
        f"Video duration: {duration:.1f}s",
        f"Total visual change points: {len(changes)}",
        f"Average interval between changes: {avg_interval:.2f}s",
    ]
    if implied_bpm > 0:
        lines.append(f"Implied visual rhythm: ~{implied_bpm} BPM")
    if strong:
        strong_times = ", ".join(f"{c['time']:.1f}s" for c in strong)
        lines.append(f"Strong transitions (beat drop moments) at: {strong_times}")
    if medium:
        medium_times = ", ".join(f"{c['time']:.1f}s" for c in medium)
        lines.append(f"Medium transitions at: {medium_times}")

    # Timeline summary
    lines.append("Change timeline: " + " -> ".join(
        f"{c['time']:.1f}s({'strong' if c['score'] > 0.3 else 'subtle'})"
        for c in changes[:15]
    ))

    return "\n".join(lines)


def describe_video_mood(frames: list[Path], duration: float = 0,
                        changes: Optional[list[dict]] = None) -> str:
    """Send frames + rhythm analysis to Claude Vision API, return a music generation prompt."""
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    rhythm_info = _format_rhythm_analysis(duration, changes or [])

    # Build image content blocks
    content = [
        {
            "type": "text",
            "text": (
                "These are keyframes extracted at visual change points from a TouchDesigner "
                "generative art video. Your job is to write a music generation prompt that "
                "produces a track whose RHYTHM and ENERGY match the video's visual transitions.\n\n"
                f"## Visual rhythm analysis\n{rhythm_info}\n\n"
                "## Instructions\n"
                "1. Analyze the visual mood, color palette, and energy of each frame.\n"
                "2. Note how the frames differ -- these represent moments of visual change.\n"
                "3. Write a music prompt (under 200 chars) for an instrumental track where:\n"
                "   - The TEMPO matches the visual change rhythm (use the implied BPM if available)\n"
                "   - DRUM HITS / BEAT ACCENTS align with the visual transition pace\n"
                "   - Build-ups and drops reflect the intensity pattern of the visual changes\n"
                "   - The mood and texture match the visual aesthetic\n\n"
                "Example: 'dark ambient techno, precise kick drums at 72bpm, glitchy hi-hats sync to visual pulses, "
                "deep bass swells, tension builds with snare rolls, atmospheric pads'\n\n"
                "Return ONLY the music prompt, nothing else."
            ),
        }
    ]

    for frame_path in frames:
        img_data = base64.b64encode(frame_path.read_bytes()).decode("utf-8")
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_data,
                },
            }
        )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{"role": "user", "content": content}],
    )

    prompt = response.content[0].text.strip().strip('"').strip("'")
    logger.info("Music prompt: %s", prompt)
    return prompt


def _suno_request(method: str, url: str, data: Optional[dict] = None) -> dict:
    """Make an HTTP request to Suno API with proper headers to avoid Cloudflare."""
    import urllib.request
    import urllib.error

    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def generate_music(prompt: str, duration_seconds: int) -> Path:
    """Call Suno API to generate instrumental music, return path to downloaded audio."""
    import urllib.request

    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY not set in .env")

    # Step 1: Submit generation request
    # callBackUrl is required by the API but we poll instead;
    # use a no-op URL that won't cause issues
    result = _suno_request("POST", f"{SUNO_BASE_URL}/api/v1/generate", {
        "customMode": True,
        "instrumental": True,
        "model": "V4_5",
        "style": prompt,
        "title": "TD Background",
        "prompt": "",
        "callBackUrl": "https://httpbin.org/post",
    })

    if result.get("code") != 200:
        raise RuntimeError(f"Suno API error: {result}")

    task_id = result["data"]["taskId"]
    logger.info("Suno task submitted: %s", task_id)

    # Step 2: Poll for completion
    poll_url = f"{SUNO_BASE_URL}/api/v1/generate/record-info?taskId={task_id}"

    audio_url = None
    for attempt in range(60):  # up to 5 minutes
        time.sleep(5)
        status_data = _suno_request("GET", poll_url)

        status = status_data.get("data", {}).get("status", "")
        logger.info("Poll attempt %d: status=%s", attempt + 1, status)

        if status == "SUCCESS":
            suno_data = status_data["data"]["response"]["sunoData"]
            # Pick the track closest to desired duration
            best = min(suno_data, key=lambda s: abs(s.get("duration", 0) - duration_seconds))
            audio_url = best.get("audioUrl")
            break
        elif status in ("CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED",
                        "CALLBACK_EXCEPTION", "SENSITIVE_WORD_ERROR"):
            raise RuntimeError(f"Suno generation failed: {status} - {status_data}")

    if not audio_url:
        raise RuntimeError("Suno generation timed out after 5 minutes")

    # Step 3: Download audio (use curl to avoid Cloudflare blocks)
    audio_path = Path(tempfile.mktemp(suffix=".mp3", prefix="td_music_"))
    subprocess.run(
        ["curl", "-sL", "-o", str(audio_path), audio_url],
        check=True,
    )
    logger.info("Downloaded music: %s (%.1f KB)", audio_path, audio_path.stat().st_size / 1024)
    return audio_path


def merge_audio_video(video: Path, audio: Path, output: Path) -> None:
    """Merge video + audio into H.264 .mp4 with fade in/out."""
    duration = get_video_duration(video)
    fade_out_start = max(0, duration - FADE_DURATION)

    subprocess.run(
        [
            str(FFMPEG),
            "-i", str(video),
            "-i", str(audio),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-af", (
                f"afade=t=in:st=0:d={FADE_DURATION},"
                f"afade=t=out:st={fade_out_start}:d={FADE_DURATION}"
            ),
            "-t", str(duration),
            "-shortest",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-movflags", "+faststart",
            "-y",
            str(output),
        ],
        check=True,
    )
    logger.info("Merged output: %s", output)


# ---------------------------------------------------------------------------
# XHS Post Generation + Notion Sync
# ---------------------------------------------------------------------------

NOTION_IDS_FILE = PROJECT_DIR / "notion-ids.json"

XHS_POST_PROMPT = """你是Shaw，NYU IDM毕业，在纽约做数媒/交互的纯创作者。

身份：纯创作者，关注TouchDesigner、AI工具、展览、数字艺术
- 绝对不出现：留学/申请/辅导/offer/录取/院校/作品集辅导
- 不提另一个号（矩阵运营违规）
- 内容方向：TD教程、AI工具测评、展览打卡、创作过程分享

这是一个TD生成艺术视频的关键帧。请为这个视频写一篇小红书个人号发帖文案。

要求：
1. 标题：带emoji，吸引眼球，15字以内
2. 正文：200字以内，活人感，分享创作过程/灵感/技术亮点，像朋友聊天
3. 标签：10个，包含#TouchDesigner #生成艺术 #数字艺术 等相关标签
4. 封面建议：简短描述用哪一帧或什么风格的封面

格式严格按照：
标题：xxx
正文：xxx
标签：#xx #xx #xx ...
封面建议：xxx"""


def generate_xhs_post(frames: list[Path], mood_prompt: str) -> dict:
    """Generate XHS personal account post copy based on video frames."""
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    content = [
        {
            "type": "text",
            "text": (
                f"{XHS_POST_PROMPT}\n\n"
                f"音乐风格参考（AI生成的配乐描述）：{mood_prompt}"
            ),
        }
    ]

    for frame_path in frames[:4]:
        img_data = base64.b64encode(frame_path.read_bytes()).decode("utf-8")
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": img_data,
            },
        })

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )

    text = response.content[0].text.strip()
    logger.info("Generated XHS post:\n%s", text)

    # Parse structured output
    post = {"raw": text, "title": "", "body": "", "tags": "", "cover": ""}
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("标题：") or line.startswith("标题:"):
            post["title"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        elif line.startswith("正文：") or line.startswith("正文:"):
            post["body"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        elif line.startswith("标签：") or line.startswith("标签:"):
            post["tags"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        elif line.startswith("封面建议：") or line.startswith("封面建议:"):
            post["cover"] = line.split("：", 1)[-1].split(":", 1)[-1].strip()

    # If body wasn't on a single line, grab everything between 正文 and 标签
    if not post["body"]:
        in_body = False
        body_lines = []
        for line in text.split("\n"):
            if "正文" in line and ("：" in line or ":" in line):
                body_lines.append(line.split("：", 1)[-1].split(":", 1)[-1].strip())
                in_body = True
            elif in_body and ("标签" in line):
                in_body = False
            elif in_body:
                body_lines.append(line.strip())
        post["body"] = "\n".join(body_lines).strip()

    return post


def sync_to_notion(post: dict, video_name: str) -> Optional[str]:
    """Create a draft page in the personal drafts Notion database via REST API."""
    import urllib.request
    import urllib.error

    notion_token = os.environ.get("NOTION_TOKEN", "")
    if not notion_token:
        logger.warning("NOTION_TOKEN not set, skipping Notion sync")
        return None

    if not NOTION_IDS_FILE.exists():
        logger.warning("notion-ids.json not found, skipping Notion sync")
        return None

    ids = json.loads(NOTION_IDS_FILE.read_text(encoding="utf-8"))
    # Use the unified 内容草稿库 (company_drafts) with 账号=个人号
    db_id = ids.get("company_drafts", "")
    if not db_id:
        logger.warning("company_drafts DB ID not found, skipping Notion sync")
        return None

    title = post.get("title", "") or f"TD视频 - {video_name}"
    body = post.get("body", "")
    tags = post.get("tags", "")
    cover_note = post.get("cover", "")
    full_content = f"{body}\n\n{tags}\n\n封面建议：{cover_note}\n\n---\n视频文件：{video_name}"

    # Build content blocks (Notion 2000 char limit per rich_text)
    children = []
    for i in range(0, len(full_content), 1900):
        chunk = full_content[i:i + 1900]
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            },
        })

    payload = json.dumps({
        "parent": {"database_id": db_id},
        "icon": {"type": "emoji", "emoji": "🎬"},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "状态": {"select": {"name": "待审批"}},
            "账号": {"select": {"name": "个人号"}},
        },
        "children": children,
    }).encode()

    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=payload,
        headers={
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
        page_url = result.get("url", "")
        logger.info("Notion draft created: %s (%s)", title, page_url)
        return page_url
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logger.error("Notion API error %d: %s", e.code, error_body)
        # If integration lacks DB access, log clear instructions
        if "not find" in error_body or e.code == 404:
            logger.error("Fix: share the personal_drafts database with the 'xhs-ops' integration in Notion")
        return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def process_video(video_path: Path, dry_run: bool = False) -> Optional[Path]:
    """Full pipeline: keyframes -> mood -> music -> merge -> XHS post -> Notion."""
    video_path = video_path.resolve()
    logger.info("Processing: %s", video_path)

    if not video_path.exists():
        logger.error("File not found: %s", video_path)
        return None

    # 1. Get duration
    duration = get_video_duration(video_path)
    logger.info("Duration: %.1f seconds", duration)

    # 2. Detect visual change points (rhythm analysis)
    changes = detect_visual_changes(video_path)
    if changes:
        logger.info("Visual changes: %s",
                     ", ".join(f"{c['time']:.1f}s(score={c['score']})" for c in changes[:10]))

    # 3. Extract keyframes at change points
    frames = extract_keyframes(video_path, change_points=changes)
    if not frames:
        logger.error("No keyframes extracted")
        return None

    # 4. Describe mood + rhythm via Claude Vision
    mood_prompt = describe_video_mood(frames, duration=duration, changes=changes)

    # 5. Generate XHS post copy
    post = generate_xhs_post(frames, mood_prompt)
    logger.info("XHS post title: %s", post.get("title", ""))

    if dry_run:
        logger.info("DRY RUN -- mood prompt: %s", mood_prompt)
        logger.info("DRY RUN -- XHS post:\n%s", post.get("raw", ""))
        _cleanup_frames(frames)
        return None

    # 6. Generate music via Suno
    audio_path = generate_music(mood_prompt, int(duration))

    # 7. Merge into .mp4
    READY_DIR.mkdir(parents=True, exist_ok=True)
    output_name = video_path.stem + ".mp4"
    output_path = READY_DIR / output_name
    merge_audio_video(video_path, audio_path, output_path)

    # 8. Sync to Notion (personal drafts, status=待审批)
    try:
        notion_url = sync_to_notion(post, output_name)
        if notion_url:
            logger.info("Notion page: %s", notion_url)
    except Exception:
        logger.exception("Notion sync failed (non-fatal)")

    # 9. Notify
    notify_msg = f"视频处理完成: {output_name}"
    if post.get("title"):
        notify_msg += f"\n文案: {post['title']}"
    send_notification(notify_msg, "TD Auto-Music")
    logger.info("Done! Output: %s", output_path)

    # 10. Cleanup temp files
    _cleanup_frames(frames)
    audio_path.unlink(missing_ok=True)

    return output_path


def _cleanup_frames(frames: list[Path]) -> None:
    """Remove temp frame files and their directory."""
    if not frames:
        return
    tmpdir = frames[0].parent
    for f in frames:
        f.unlink(missing_ok=True)
    try:
        tmpdir.rmdir()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Watch folder mode
# ---------------------------------------------------------------------------


def _load_processed() -> set[str]:
    """Load set of already-processed file paths."""
    if PROCESSED_FILE.exists():
        data = json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
        return set(data)
    return set()


def _save_processed(processed: set[str]) -> None:
    """Save processed file paths."""
    PROCESSED_FILE.write_text(
        json.dumps(sorted(processed), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def scan_folder() -> None:
    """One-shot scan: process any new .mov files, then exit. Used by launchd WatchPaths."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    READY_DIR.mkdir(parents=True, exist_ok=True)

    processed = _load_processed()
    mov_files = sorted(EXPORT_DIR.glob("*.mov"))
    new_files = [m for m in mov_files if str(m.resolve()) not in processed]

    if not new_files:
        logger.info("No new files in %s", EXPORT_DIR)
        return

    for mov in new_files:
        key = str(mov.resolve())
        logger.info("New file detected: %s", mov.name)
        try:
            result = process_video(mov)
            if result:
                processed.add(key)
                _save_processed(processed)
        except Exception:
            logger.exception("Failed to process %s", mov.name)


def watch_folder() -> None:
    """Poll export folder for new .mov files every WATCH_INTERVAL seconds."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    READY_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Watching %s (every %ds)...", EXPORT_DIR, WATCH_INTERVAL)

    while True:
        try:
            scan_folder()
        except Exception:
            logger.exception("Watch loop error")

        time.sleep(WATCH_INTERVAL)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TD Video Auto-Music: add AI-generated ambient music to TouchDesigner videos"
    )
    parser.add_argument(
        "video",
        nargs="?",
        type=Path,
        help="Path to a .mov file to process",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch ~/Desktop/td/export/ for new .mov files (polling mode)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="One-shot scan for new files, process, then exit (for launchd)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract frames and describe mood only (no Suno call)",
    )

    args = parser.parse_args()

    if args.scan:
        scan_folder()
    elif args.watch:
        watch_folder()
    elif args.video:
        result = process_video(args.video, dry_run=args.dry_run)
        if result:
            print(f"Output: {result}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
