#!/usr/bin/env python3
"""
weekly_brief.py — Reads competitor observations from Notion (manually logged by Shaw),
computes tag frequency and top posts, generates a weekly brief, optionally pushes to
Notion, and updates WORKFLOW-STATE.md.

Falls back to CSV parsing if Notion read fails.
"""

import os
import sys
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# ---------------------------------------------------------------------------
# Bootstrap: load .env before anything else (launchd has no shell env)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_env
load_env()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR = Path.home() / "claude" / "xiaohongshu-ops"
DATA_DIR = PROJECT_DIR / "data"
BRIEFS_DIR = PROJECT_DIR / "briefs"
LOG_DIR = PROJECT_DIR / "logs"
STATE_FILE = PROJECT_DIR / "WORKFLOW-STATE.md"

LOG_DIR.mkdir(parents=True, exist_ok=True)
BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "weekly_brief.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Baseline tag frequencies (hardcoded from initial 120-post competitor analysis)
# Used to detect trending tags (>50% increase vs baseline)
# ---------------------------------------------------------------------------
TAG_BASELINE: dict[str, int] = {
    "作品集": 100,
    "艺术留学": 80,
    "数媒作品集": 60,
    "交互设计": 50,
    "留学作品集辅导": 45,
    "数字媒体艺术": 40,
    "作品集辅导": 55,
    "艺术生留学": 35,
    "交互设计作品集": 30,
    "艺术留学作品集": 38,
    "服务设计": 10,
    "HCI": 10,
    "平面设计留学": 15,
    "UX设计": 20,
    "设计留学": 25,
    "平面设计作品集": 15,
    "作品集机构": 20,
    "艺术留学中介": 15,
    "作品集排版": 20,
}

# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------
def parse_csvs(data_dir: Path, days: int = 7) -> list[dict]:
    """Load all CSV files from data_dir whose filename date is within last `days` days."""
    cutoff = datetime.now() - timedelta(days=days)
    rows = []

    try:
        from pandas import read_csv, isna  # type: ignore
        use_pandas = True
    except ImportError:
        use_pandas = False
        logger.info("pandas not available, falling back to csv module")

    for csv_file in sorted(DATA_DIR.glob("*.csv")):
        # Expect filenames like 2026-03-16-数媒作品集.csv
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", csv_file.name)
        if not date_match:
            continue
        try:
            file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
        except ValueError:
            logger.warning("Skipping %s — could not parse date '%s'", csv_file.name, date_match.group(1))
            continue
        if file_date < cutoff:
            continue

        logger.info("Parsing %s", csv_file)
        try:
            if use_pandas:
                import pandas as pd  # type: ignore
                df = pd.read_csv(csv_file, encoding="utf-8-sig")
                for _, row in df.iterrows():
                    rows.append({k: (None if pd.isna(v) else v) for k, v in row.items()})
            else:
                import csv
                with open(csv_file, encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        rows.append(dict(row))
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", csv_file, exc)

    logger.info("Loaded %d rows from %d CSV files", len(rows), len(list(DATA_DIR.glob("*.csv"))))
    return rows


# ---------------------------------------------------------------------------
# Notion competitor observations parsing
# ---------------------------------------------------------------------------
IDS_FILE = Path.home() / "claude" / "xiaohongshu-ops" / "notion-ids.json"


def parse_notion_observations(notion_token: str, days: int = 7) -> list[dict]:
    """Read from Notion 竞品观察 database, return rows in same format as parse_csvs()."""
    import json
    try:
        from notion_client import Client  # type: ignore
    except ImportError:
        logger.warning("notion-client not installed — cannot read Notion observations")
        return []

    try:
        ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read notion-ids.json: %s", exc)
        return []

    ds_id = ids.get("competitor_observations_ds")
    if not ds_id:
        logger.warning("competitor_observations_ds not found in notion-ids.json")
        return []

    notion = Client(auth=notion_token)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    rows = []
    try:
        cursor = None
        while True:
            kwargs = {
                "data_source_id": ds_id,
                "page_size": 100,
                "filter": {
                    "property": "观察日期",
                    "date": {"on_or_after": cutoff},
                },
            }
            if cursor:
                kwargs["start_cursor"] = cursor
            response = notion.data_sources.query(**kwargs)
            for page in response.get("results", []):
                props = page.get("properties", {})
                # Extract fields
                title = ""
                title_prop = props.get("标题", {})
                if title_prop.get("type") == "title":
                    title = "".join(t.get("plain_text", "") for t in title_prop.get("title", []))

                likes_saves = 0
                ls_prop = props.get("赞藏", {})
                if ls_prop.get("type") == "number":
                    likes_saves = ls_prop.get("number") or 0

                tags = ""
                tags_prop = props.get("标签", {})
                if tags_prop.get("type") == "rich_text":
                    tags = "".join(t.get("plain_text", "") for t in tags_prop.get("rich_text", []))

                keyword = ""
                kw_prop = props.get("来源关键词", {})
                if kw_prop.get("type") == "select":
                    keyword = (kw_prop.get("select") or {}).get("name", "")

                nickname = ""
                nn_prop = props.get("账号名", {})
                if nn_prop.get("type") == "rich_text":
                    nickname = "".join(t.get("plain_text", "") for t in nn_prop.get("rich_text", []))

                # Map to CSV-compatible format
                rows.append({
                    "title": title,
                    "liked_count": likes_saves // 2,  # approximate split
                    "collected_count": likes_saves - likes_saves // 2,
                    "comment_count": 0,
                    "share_count": 0,
                    "tag_list": tags,
                    "note_url": "",
                    "nickname": nickname,
                    "source_keyword": keyword,
                })
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
    except Exception as exc:
        logger.warning("Failed to query Notion competitor_observations: %s", exc)

    logger.info("Loaded %d observations from Notion 竞品观察", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Tag frequency
# ---------------------------------------------------------------------------
def extract_tags(rows: list[dict]) -> Counter:
    """Parse the tag_list column (comma-separated) from all rows."""
    counter: Counter = Counter()
    for row in rows:
        raw = row.get("tag_list") or ""
        if not raw:
            continue
        tags = [t.strip() for t in str(raw).split(",") if t.strip()]
        counter.update(tags)
    return counter


# ---------------------------------------------------------------------------
# Top posts by engagement
# ---------------------------------------------------------------------------
def safe_int(value) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return 0


def top_posts(rows: list[dict], n: int = 5) -> list[dict]:
    """Return top n posts ranked by liked_count + collected_count."""
    scored = []
    for row in rows:
        liked = safe_int(row.get("liked_count"))
        collected = safe_int(row.get("collected_count"))
        score = liked + collected
        scored.append({
            "title": str(row.get("title") or ""),
            "liked_count": liked,
            "collected_count": collected,
            "comment_count": safe_int(row.get("comment_count")),
            "share_count": safe_int(row.get("share_count")),
            "engagement": score,
            "note_url": str(row.get("note_url") or ""),
            "nickname": str(row.get("nickname") or ""),
            "source_keyword": str(row.get("source_keyword") or ""),
        })
    scored.sort(key=lambda x: x["engagement"], reverse=True)
    return scored[:n]


# ---------------------------------------------------------------------------
# Content recommendation
# ---------------------------------------------------------------------------
def build_recommendation(tag_counts: Counter, phase: str) -> str:
    lines = []

    # Detect trending tags (>50% above baseline)
    trending = []
    for tag, baseline_count in TAG_BASELINE.items():
        current = tag_counts.get(tag, 0)
        if baseline_count > 0 and current > baseline_count * 1.5:
            trending.append((tag, current, baseline_count))

    if trending:
        trending.sort(key=lambda x: x[1] / x[2], reverse=True)
        top_trending = trending[0]
        lines.append(
            f"本周热点标签: #{top_trending[0]} "
            f"（当前出现{top_trending[1]}次，基线{top_trending[2]}次，增幅"
            f"{(top_trending[1]/top_trending[2]-1)*100:.0f}%）"
        )

    # Phase-based content type recommendation
    phase_recommendations = {
        "repair": "建议本周发布：真实案例拆解类内容，重点展示改稿前后对比，增强可信度。",
        "building": "建议本周发布：高价值干货教程（如「数媒作品集5大误区」），搭配强封面配图，提升收藏率。",
        "stable": "建议本周发布：互动型内容（如选题投票、FAQ合集），维持账号活跃度和粉丝粘性。",
        "brief_ready": "简报已就绪，等待审批后生成草稿。",
        "content_ready": "草稿已生成，按计划发布即可。",
        "awaiting_data": "等待数据录入，发布72小时后记录曝光/点赞/收藏。",
    }
    rec = phase_recommendations.get(phase, "根据账号当前状态，建议继续按内容日历执行。")
    lines.append(f"内容策略建议：{rec}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# WORKFLOW-STATE.md helpers (imported from utils)
# ---------------------------------------------------------------------------
from utils import read_state_field, update_state_field


# ---------------------------------------------------------------------------
# Brief formatting
# ---------------------------------------------------------------------------
def format_brief_markdown(brief: dict) -> str:
    lines = [
        f"# 竞品周报 {brief['date']}",
        "",
        "## 本周热门标签 Top 10",
        "",
    ]
    for i, (tag, count) in enumerate(brief["top_tags"], 1):
        lines.append(f"{i}. #{tag} — {count}次")

    lines += [
        "",
        "## 高互动帖子 Top 5",
        "",
    ]
    for i, post in enumerate(brief["top_posts"], 1):
        lines.append(
            f"{i}. **{post['title']}**  "
            f"赞{post['liked_count']} 藏{post['collected_count']} "
            f"评{post['comment_count']}  "
            f"来源关键词: {post['source_keyword']}  "
            f"账号: {post['nickname']}"
        )
        if post["note_url"]:
            lines.append(f"   {post['note_url']}")

    lines += [
        "",
        "## 内容建议",
        "",
        brief["content_recommendation"],
        "",
        "---",
        f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Notion push
# ---------------------------------------------------------------------------
def push_to_notion(brief: dict, notion_token: str) -> None:
    """Push brief to Notion 竞品周报 database and update 本周状态 callout."""
    try:
        from notion_client import Client  # type: ignore
    except ImportError:
        logger.warning("notion-client not installed. Run: pip install notion-client")
        return

    import json
    notion = Client(auth=notion_token)
    ROOT_PAGE_ID = "32693fe4326480e386e3fc6a049fff07"

    # Read 竞品周报 DB ID from notion-ids.json
    db_id = None
    try:
        ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
        db_id = ids.get("competitor_weekly")
        if db_id:
            logger.info("Using 竞品周报 database from notion-ids.json: %s", db_id)
    except Exception as exc:
        logger.warning("Could not read competitor_weekly from notion-ids.json: %s", exc)

    if not db_id:
        logger.warning("竞品周报 database not found in Notion — skipping database push")
    else:
        # Build top tags text
        top_tags_text = "、".join(
            f"#{tag}({count})" for tag, count in brief["top_tags"][:5]
        )
        # Build top posts text
        top_posts_lines = []
        for post in brief["top_posts"][:3]:
            top_posts_lines.append(
                f"{post['title']} (赞{post['liked_count']}+藏{post['collected_count']}={post['engagement']})"
            )
        top_posts_text = "\n".join(top_posts_lines)

        try:
            notion.pages.create(
                parent={"database_id": db_id},
                properties={
                    "Name": {
                        "title": [{"text": {"content": f"竞品周报 {brief['date']}"}}]
                    },
                    "日期": {
                        "date": {"start": brief["date"]}
                    },
                },
                children=[
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "本周热门标签"}}]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": top_tags_text}}]
                        },
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "高互动帖子 Top 5"}}]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": top_posts_text}}]
                        },
                    },
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "内容建议"}}]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": brief["content_recommendation"]}}
                            ]
                        },
                    },
                ],
            )
            logger.info("Created new page in 竞品周报 database")
        except Exception as exc:
            logger.warning("Failed to create page in 竞品周报 database: %s", exc)

    # Update 本周状态 callout block on the root page
    try:
        blocks = notion.blocks.children.list(block_id=ROOT_PAGE_ID).get("results", [])
        for block in blocks:
            block_type = block.get("type", "")
            rich_text = block.get(block_type, {}).get("rich_text", [])
            plain = "".join(t.get("plain_text", "") for t in rich_text)
            if "本周状态" in plain:
                new_content = (
                    f"本周状态 | {brief['date']} | 周报已生成 | "
                    f"热门标签: {', '.join(t for t, _ in brief['top_tags'][:3])}"
                )
                try:
                    notion.blocks.update(
                        block_id=block["id"],
                        **{
                            block_type: {
                                "rich_text": [
                                    {"type": "text", "text": {"content": new_content}}
                                ]
                            }
                        },
                    )
                    logger.info("Updated 本周状态 callout block")
                except Exception as exc:
                    logger.warning("Failed to update 本周状态 block: %s", exc)
                break
    except Exception as exc:
        logger.warning("Failed to search for 本周状态 block: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    notion_token = os.environ.get("NOTION_TOKEN", "")

    logger.info("weekly_brief.py starting — date=%s", today)

    # Load data: Notion first, CSV fallback
    rows = []
    if notion_token:
        rows = parse_notion_observations(notion_token, days=7)
    if not rows:
        logger.info("Falling back to CSV parsing")
        rows = parse_csvs(DATA_DIR, days=7)
    if not rows:
        logger.warning("No data found (Notion or CSV) for the past 7 days")
        # Still proceed to write an empty brief rather than crashing

    # Compute stats
    tag_counts = extract_tags(rows)
    top_tag_list = tag_counts.most_common(10)
    posts = top_posts(rows, n=5)

    # Read current phase
    phase = read_state_field("phase") or "未知"

    # Build recommendation
    recommendation = build_recommendation(tag_counts, phase)

    brief = {
        "date": today,
        "top_tags": top_tag_list,
        "top_posts": posts,
        "content_recommendation": recommendation,
        "phase": phase,
        "total_posts_analyzed": len(rows),
    }

    # Write markdown brief
    brief_path = BRIEFS_DIR / f"{today}-brief.md"
    md = format_brief_markdown(brief)
    brief_path.write_text(md, encoding="utf-8")
    logger.info("Brief written to %s", brief_path)

    # Push to Notion if token available
    if notion_token:
        logger.info("NOTION_TOKEN found — pushing to Notion")
        push_to_notion(brief, notion_token)
    else:
        logger.warning(
            "NOTION_TOKEN not set — brief written to local file only: %s", brief_path
        )

    # Update WORKFLOW-STATE.md
    update_state_field("phase", "brief_ready")
    update_state_field("last_brief_date", today)
    logger.info("WORKFLOW-STATE.md updated: phase=brief_ready, last_brief_date=%s", today)


if __name__ == "__main__":
    main()
