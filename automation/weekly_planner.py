#!/usr/bin/env python3
"""
weekly_planner.py — Reads latest brief + analysis summary, determines post count
by phase, calls Claude API to generate drafts, creates Notion draft pages with
status=待审批.

Runs Sunday 22:30 via launchd, after weekly_brief.py has finished.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: load .env before anything else (launchd has no shell env)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_env, read_state_field, update_state_field, send_notification
load_env()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR = Path.home() / "claude" / "xiaohongshu-ops"
BRIEFS_DIR = PROJECT_DIR / "briefs"
ANALYSIS_DIR = PROJECT_DIR / "analysis"
LOG_DIR = PROJECT_DIR / "logs"
IDS_FILE = PROJECT_DIR / "notion-ids.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "weekly_planner.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

# Phase -> post plan: list of (account_type, day_label)
PHASE_POST_PLANS = {
    "repair":   [("company", "周三")],
    "修复期":    [("company", "周三")],
    "building": [("company", "周三"), ("company", "周日"), ("personal", "周二")],
    "建量期":    [("company", "周三"), ("company", "周日"), ("personal", "周二")],
    "stable":   [("company", "周三"), ("company", "周日"), ("personal", "周二"), ("personal", "周四")],
    "稳定期":    [("company", "周三"), ("company", "周日"), ("personal", "周二"), ("personal", "周四")],
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_latest_brief() -> str:
    """Read most recent brief markdown file."""
    brief_files = sorted(BRIEFS_DIR.glob("*-brief.md"), reverse=True)
    if not brief_files:
        logger.warning("No brief files found in %s", BRIEFS_DIR)
        return ""
    latest = brief_files[0]
    logger.info("Loading brief from %s", latest)
    return latest.read_text(encoding="utf-8")


def load_latest_analysis() -> dict:
    """Read analysis/latest-summary.json."""
    summary_path = ANALYSIS_DIR / "latest-summary.json"
    if not summary_path.exists():
        logger.warning("latest-summary.json not found")
        return {}
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read latest-summary.json: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Content generation
# ---------------------------------------------------------------------------
def generate_draft(brief_text: str, analysis: dict, account_type: str, day_label: str) -> str:
    """Call Claude API to generate a post draft."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return f"[需要手动生成 — {account_type}号 {day_label} 草稿]\n\n请将以下brief粘贴到Claude对话中生成：\n\n{brief_text[:500]}"

    try:
        import anthropic  # type: ignore
    except ImportError:
        logger.error("anthropic SDK not installed")
        return f"[SDK未安装 — {account_type}号 {day_label}]"

    # Import prompts from gen_content
    try:
        from gen_content import COMPANY_SYSTEM_PROMPT, PERSONAL_SYSTEM_PROMPT
    except ImportError:
        logger.warning("Could not import gen_content prompts, using fallback")
        COMPANY_SYSTEM_PROMPT = "你是Shaw，作品集辅导老师。生成小红书帖子。"
        PERSONAL_SYSTEM_PROMPT = "你是Shaw，纯创作者。生成小红书帖子。"

    system_prompt = PERSONAL_SYSTEM_PROMPT if account_type == "personal" else COMPANY_SYSTEM_PROMPT

    phase_info = ""
    if analysis:
        phase_info = f"\n当前阶段：{analysis.get('phase', '未知')}\n薯条建议：{analysis.get('shudiao_recommendation', 'N/A')}"

    user_message = (
        f"请为{day_label}生成一篇小红书帖子草稿。\n\n"
        f"以下是本周竞品分析周报：\n{brief_text}\n"
        f"{phase_info}\n\n"
        f"要求：标题（含emoji）| 正文（200字以内）| 标签（10个）| 封面建议"
    )

    client = anthropic.Anthropic(api_key=api_key)
    logger.info("Calling Claude API for %s %s draft", account_type, day_label)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    content = message.content[0].text if message.content else ""
    logger.info("Generated %d chars for %s %s", len(content), account_type, day_label)
    return content


# ---------------------------------------------------------------------------
# Notion draft creation
# ---------------------------------------------------------------------------
def create_notion_draft(notion, db_id: str, title: str, body: str, status_prop_name: str, status_prop_type: str) -> str:
    """Create a Notion page in the draft DB with status=待审批. Returns page ID."""
    # Build status property value
    if status_prop_type == "status":
        status_value = {status_prop_name: {"status": {"name": "待审批"}}}
    elif status_prop_type == "select":
        status_value = {status_prop_name: {"select": {"name": "待审批"}}}
    else:
        status_value = {status_prop_name: {"rich_text": [{"text": {"content": "待审批"}}]}}

    # Detect title property name from DB schema
    title_prop_name = "Name"
    try:
        db_detail = notion.databases.retrieve(database_id=db_id)
        db_props = db_detail.get("properties", {})
        for pname, pval in db_props.items():
            if pval.get("type") == "title":
                title_prop_name = pname
                break
        # Also detect status property
        for pname, pval in db_props.items():
            if pname.lower() in ("状态", "status", "审批状态"):
                status_prop_name = pname
                status_prop_type = pval.get("type", "status")
                if status_prop_type == "status":
                    status_value = {status_prop_name: {"status": {"name": "待审批"}}}
                elif status_prop_type == "select":
                    status_value = {status_prop_name: {"select": {"name": "待审批"}}}
                break
    except Exception as exc:
        logger.warning("Could not retrieve DB schema for %s: %s", db_id, exc)

    properties = {
        title_prop_name: {"title": [{"text": {"content": title}}]},
        **status_value,
    }

    # Split body into blocks (Notion max 2000 chars per rich_text block)
    body_blocks = []
    for i in range(0, len(body), 1900):
        chunk = body[i:i + 1900]
        body_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            },
        })

    page = notion.pages.create(
        parent={"database_id": db_id},
        properties=properties,
        children=body_blocks,
    )
    page_id = page.get("id", "")
    logger.info("Created Notion draft page: %s", page_id)
    return page_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly content planner")
    parser.add_argument("--dry-run", action="store_true", help="Print generated content without touching Notion")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    logger.info("weekly_planner.py starting — date=%s, dry_run=%s", today, args.dry_run)

    # Load inputs
    brief_text = load_latest_brief()
    analysis = load_latest_analysis()

    # Determine phase and post plan
    phase = analysis.get("phase") or read_state_field("phase") or "repair"
    post_plan = PHASE_POST_PLANS.get(phase, PHASE_POST_PLANS["repair"])
    logger.info("Phase=%s, planning %d posts", phase, len(post_plan))

    # Load notion-ids.json
    try:
        ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Could not read notion-ids.json: %s", exc)
        ids = {}

    db_ids = {
        "company": ids.get("company_drafts"),
        "personal": ids.get("personal_drafts"),
    }

    # Generate drafts
    drafts = []
    for account_type, day_label in post_plan:
        content = generate_draft(brief_text, analysis, account_type, day_label)
        # Extract title from first line if possible
        first_line = content.split("\n")[0].strip()
        title = f"[{today}] {day_label} {'公司' if account_type == 'company' else '个人'}号"
        if first_line and len(first_line) < 100:
            title = f"[{today}] {first_line}"
        drafts.append({
            "account_type": account_type,
            "day_label": day_label,
            "title": title,
            "content": content,
        })

    if args.dry_run:
        for draft in drafts:
            print(f"\n{'='*60}")
            print(f"[{draft['account_type']}号 {draft['day_label']}] {draft['title']}")
            print(f"{'='*60}")
            print(draft["content"])
        print(f"\n--- Dry run complete: {len(drafts)} drafts generated ---")
        return

    # Push to Notion
    notion_token = os.environ.get("NOTION_TOKEN", "")
    if not notion_token:
        logger.error("NOTION_TOKEN not set — cannot create Notion drafts")
        for draft in drafts:
            print(f"[{draft['account_type']}] {draft['title']}")
            print(draft["content"][:200] + "...")
        return

    try:
        from notion_client import Client  # type: ignore
    except ImportError:
        logger.error("notion-client not installed")
        return

    notion = Client(auth=notion_token)
    created_count = 0

    for draft in drafts:
        db_id = db_ids.get(draft["account_type"])
        if not db_id:
            logger.warning("No DB ID for account type %s — skipping", draft["account_type"])
            continue
        try:
            create_notion_draft(notion, db_id, draft["title"], draft["content"], "状态", "status")
            created_count += 1
        except Exception as exc:
            logger.error("Failed to create Notion draft for %s: %s", draft["title"], exc)

    # Update state
    update_state_field("phase", "plan_ready")
    update_state_field("last_planner_date", today)
    logger.info("Created %d/%d drafts in Notion", created_count, len(drafts))

    # Notify
    if created_count > 0:
        send_notification(
            f"本周草稿已规划（{created_count}篇待审批），去Notion查看",
            "XHS运营 -- 周计划就绪",
        )


if __name__ == "__main__":
    main()
