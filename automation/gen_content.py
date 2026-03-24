#!/usr/bin/env python3
"""
gen_content.py — Generates a XHS post draft using Claude API (or a manual fallback).

Can be run standalone (reads from the latest brief file) or imported by
check_approved.py via generate(brief_dict).
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

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
BRIEFS_DIR = PROJECT_DIR / "briefs"
CONTENT_DIR = PROJECT_DIR / "content"
LOG_DIR = PROJECT_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "gen_content.log"

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
# System prompt
# ---------------------------------------------------------------------------
COMPANY_SYSTEM_PROMPT = """你是Shaw，NYU IDM毕业，在纽约做数媒/交互设计的作品集辅导老师。

身份：作品集辅导老师Shaw
- 第一人称，活人感，不出现机构用语（不说「我们」「本机构」「专业辅导」）
- 结尾CTA用「评论区聊聊」而非「私信我」
- 绝对禁止：低GPA/X个月拿offer/保证录取/加微信/站外引流
- 不提另一个号（矩阵运营违规）

通用要求：
- 格式：标题（含emoji）| 正文（200字以内）| 标签（10个，平台上限）| 封面建议
- 所有内容需符合小红书2026年留学行业合规要求"""

PERSONAL_SYSTEM_PROMPT = """你是Shaw，NYU IDM毕业，在纽约做数媒/交互的纯创作者。

身份：纯创作者，关注TouchDesigner、AI工具、展览、数字艺术
- 绝对不出现：留学/申请/辅导/offer/录取/院校/作品集辅导
- 不提另一个号（矩阵运营违规）
- 内容方向：TD教程、AI工具测评、展览打卡、创作过程分享

通用要求：
- 格式：标题（含emoji）| 正文（200字以内）| 标签（10个，平台上限）| 封面建议
- 所有内容需符合小红书2026年社区规范"""

MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Brief loading
# ---------------------------------------------------------------------------
def load_latest_brief() -> dict:
    """Read the most recently written brief markdown file and return it as a dict."""
    brief_files = sorted(BRIEFS_DIR.glob("*-brief.md"), reverse=True)
    if not brief_files:
        logger.warning("No brief files found in %s", BRIEFS_DIR)
        return {}

    latest = brief_files[0]
    logger.info("Loading brief from %s", latest)
    text = latest.read_text(encoding="utf-8")
    return {"date": latest.name.split("-brief.md")[0], "raw_markdown": text}


def brief_to_user_message(brief: dict) -> str:
    """Convert a brief dict to a user message string for the Claude API."""
    if "raw_markdown" in brief:
        return f"以下是本周竞品分析周报，请基于此生成小红书帖子：\n\n{brief['raw_markdown']}"

    # Structured brief dict (from check_approved or weekly_brief)
    lines = ["以下是本周内容简报，请基于此生成小红书帖子：", ""]
    if brief.get("date"):
        lines.append(f"日期：{brief['date']}")
    if brief.get("top_tags"):
        tags = brief["top_tags"]
        if isinstance(tags, list):
            tag_str = "、".join(
                f"#{t[0]}" if isinstance(t, (list, tuple)) else f"#{t}"
                for t in tags[:10]
            )
        else:
            tag_str = str(tags)
        lines.append(f"本周热门标签：{tag_str}")
    if brief.get("top_posts"):
        lines.append("本周高互动帖子：")
        posts = brief["top_posts"]
        for p in posts[:3]:
            if isinstance(p, dict):
                lines.append(f"  - {p.get('title', '')} （赞{p.get('liked_count', 0)}+藏{p.get('collected_count', 0)}）")
            else:
                lines.append(f"  - {p}")
    if brief.get("content_recommendation"):
        lines.append(f"内容建议：{brief['content_recommendation']}")
    if brief.get("phase"):
        lines.append(f"账号当前阶段：{brief['phase']}")
    # Include any extra Notion page fields
    for key, val in brief.items():
        if key not in ("date", "top_tags", "top_posts", "content_recommendation", "phase",
                       "raw_markdown", "notion_page_id", "total_posts_analyzed"):
            if val:
                lines.append(f"{key}：{val}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def generate_with_claude(brief: dict, api_key: str, account_type: str = "company") -> str:
    """Call Claude API and return the generated post string."""
    try:
        import anthropic  # type: ignore
    except ImportError:
        logger.error("anthropic SDK not installed. Run: pip install anthropic")
        raise

    client = anthropic.Anthropic(api_key=api_key)
    user_message = brief_to_user_message(brief)
    system_prompt = PERSONAL_SYSTEM_PROMPT if account_type == "personal" else COMPANY_SYSTEM_PROMPT

    logger.info("Calling Claude API (model=%s, account=%s)", MODEL, account_type)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    content = message.content[0].text if message.content else ""
    logger.info("Claude API returned %d characters", len(content))
    return content


def generate_placeholder(brief: dict) -> str:
    """Return a manual-generation prompt when no API key is available."""
    user_message = brief_to_user_message(brief)
    return (
        "需要手动生成：打开Claude对话，粘贴以下brief：\n\n"
        "---\n"
        f"系统提示：\n{SYSTEM_PROMPT}\n\n"
        f"用户消息：\n{user_message}\n"
        "---"
    )


def write_draft(content: str, date: str) -> Path:
    """Write the generated content to a dated draft file."""
    draft_path = CONTENT_DIR / f"{date}-draft.md"
    draft_path.write_text(content, encoding="utf-8")
    logger.info("Draft written to %s", draft_path)
    return draft_path


# ---------------------------------------------------------------------------
# Public API (imported by check_approved.py)
# ---------------------------------------------------------------------------
def generate(brief: dict, account_type: str = "company") -> str:
    """
    Generate XHS post content for a given brief dict.
    Returns the content string and writes it to ~/claude/xiaohongshu-ops/content/YYYY-MM-DD-draft.md.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    today = datetime.now().strftime("%Y-%m-%d")

    if api_key:
        content = generate_with_claude(brief, api_key, account_type=account_type)
    else:
        logger.warning("ANTHROPIC_API_KEY not set — generating placeholder")
        content = generate_placeholder(brief)

    write_draft(content, today)
    return content


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("gen_content.py starting standalone")
    brief = load_latest_brief()
    if not brief:
        logger.warning("No brief available — generating with empty context")
        brief = {"date": datetime.now().strftime("%Y-%m-%d")}

    content = generate(brief)
    print("\n" + "=" * 60)
    print(content)
    print("=" * 60)


if __name__ == "__main__":
    main()
