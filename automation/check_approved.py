#!/usr/bin/env python3
"""
check_approved.py — Polls Notion for items with status '已批准' and triggers
content generation for each. Designed to run hourly via launchd or cron.
"""

import json
import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: load .env before anything else (launchd has no shell env)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from utils import load_env, read_state_field, update_state_field, send_notification, send_all_notifications
load_env()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR = Path.home() / "claude" / "xiaohongshu-ops"
LOG_DIR = PROJECT_DIR / "logs"
STATE_FILE = PROJECT_DIR / "WORKFLOW-STATE.md"
IDS_FILE = Path.home() / "claude" / "xiaohongshu-ops" / "notion-ids.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "check_approved.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

ROOT_PAGE_ID = "32693fe4326480e386e3fc6a049fff07"
APPROVED_STATUS = "已批准"
GENERATING_STATUS = "草稿生成中"
DONE_STATUS = "草稿就绪"


# ---------------------------------------------------------------------------
# Notion helpers
# ---------------------------------------------------------------------------
def get_draft_databases() -> list[dict]:
    """Read draft database IDs from notion-ids.json."""
    with open(IDS_FILE, "r", encoding="utf-8") as f:
        ids = json.load(f)
    databases = [
        {"id": ids["company_drafts"], "ds_id": ids["company_drafts_ds"], "account": "company"},
        {"id": ids["personal_drafts"], "ds_id": ids["personal_drafts_ds"], "account": "personal"},
    ]
    for db in databases:
        logger.info("Loaded draft database: account=%s id=%s ds_id=%s", db["account"], db["id"], db["ds_id"])
    return databases


def get_approved_items(notion, data_source_id: str) -> list[dict]:
    """Query a data source for items with status == APPROVED_STATUS."""
    approved = []
    try:
        # Try querying with a status filter; status property names vary
        # We query all items and filter locally to be robust
        cursor = None
        while True:
            kwargs = {"data_source_id": data_source_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = notion.data_sources.query(**kwargs)
            for page in response.get("results", []):
                props = page.get("properties", {})
                # Check any property named 状态 or Status
                for prop_name, prop_val in props.items():
                    if prop_name.lower() in ("状态", "status", "审批状态"):
                        ptype = prop_val.get("type", "")
                        status_text = ""
                        if ptype == "status":
                            status_text = (prop_val.get("status") or {}).get("name", "")
                        elif ptype == "select":
                            status_text = (prop_val.get("select") or {}).get("name", "")
                        elif ptype == "rich_text":
                            rts = prop_val.get("rich_text", [])
                            status_text = "".join(t.get("plain_text", "") for t in rts)
                        if status_text == APPROVED_STATUS:
                            approved.append(page)
                            break
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
    except Exception as exc:
        logger.warning("Failed to query data source %s: %s", data_source_id, exc)
    return approved


def update_item_status(notion, page_id: str, new_status: str, status_prop_name: str, status_prop_type: str) -> None:
    """Update a Notion page's status property."""
    try:
        if status_prop_type == "status":
            prop_value = {"status": {"name": new_status}}
        elif status_prop_type == "select":
            prop_value = {"select": {"name": new_status}}
        else:
            prop_value = {"rich_text": [{"text": {"content": new_status}}]}

        notion.pages.update(
            page_id=page_id,
            properties={status_prop_name: prop_value},
        )
        logger.info("Updated page %s status to '%s'", page_id, new_status)
    except Exception as exc:
        logger.warning("Failed to update status for page %s: %s", page_id, exc)


def extract_page_brief(page: dict) -> dict:
    """Extract a brief dict from a Notion page's properties."""
    props = page.get("properties", {})
    brief = {"notion_page_id": page.get("id", "")}

    for prop_name, prop_val in props.items():
        ptype = prop_val.get("type", "")
        value = ""
        if ptype == "title":
            value = "".join(t.get("plain_text", "") for t in prop_val.get("title", []))
        elif ptype == "rich_text":
            value = "".join(t.get("plain_text", "") for t in prop_val.get("rich_text", []))
        elif ptype == "select":
            value = (prop_val.get("select") or {}).get("name", "")
        elif ptype == "status":
            value = (prop_val.get("status") or {}).get("name", "")
        elif ptype == "date":
            value = (prop_val.get("date") or {}).get("start", "")
        brief[prop_name] = value

    return brief


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    notion_token = os.environ.get("NOTION_TOKEN", "")
    if not notion_token:
        # Exit quietly — no token, no work to do
        sys.exit(0)

    try:
        from notion_client import Client  # type: ignore
    except ImportError:
        logger.error("notion-client not installed. Run: pip install notion-client")
        sys.exit(1)

    notion = Client(auth=notion_token)
    logger.info("check_approved.py starting")

    # Find all 内容草稿库 databases
    databases = get_draft_databases()
    if not databases:
        logger.info("No 内容草稿库 databases found — nothing to do")
        sys.exit(0)

    # Collect all approved items across all databases
    all_approved: list[tuple[dict, dict, str, str, str]] = []  # (page, db, status_prop_name, status_prop_type, account_type)
    for db in databases:
        db_id = db["id"]
        account_type = db.get("account", "company")
        # Determine status property name and type
        status_prop_name = "状态"
        status_prop_type = "status"
        try:
            db_detail = notion.databases.retrieve(database_id=db_id)
            db_props = db_detail.get("properties", {})
            for pname, pval in db_props.items():
                if pname.lower() in ("状态", "status", "审批状态"):
                    status_prop_name = pname
                    status_prop_type = pval.get("type", "status")
                    break
        except Exception as exc:
            logger.warning("Could not retrieve database schema for %s: %s", db_id, exc)

        approved = get_approved_items(notion, db["ds_id"])
        logger.info("Database %s (%s): %d approved item(s)", db_id, account_type, len(approved))
        for page in approved:
            all_approved.append((page, db, status_prop_name, status_prop_type, account_type))

    if not all_approved:
        logger.info("No approved items found — exiting quietly")
        sys.exit(0)

    logger.info("Found %d approved item(s) total — generating content", len(all_approved))

    # Import gen_content
    automation_dir = Path(__file__).parent
    if str(automation_dir) not in sys.path:
        sys.path.insert(0, str(automation_dir))

    try:
        import gen_content  # type: ignore
    except ImportError as exc:
        logger.error("Could not import gen_content: %s", exc)
        sys.exit(1)

    content_generated = 0
    for page, db, status_prop_name, status_prop_type, account_type in all_approved:
        page_id = page["id"]
        brief = extract_page_brief(page)
        title = brief.get("名称") or brief.get("Title") or brief.get("标题") or page_id

        logger.info("Processing approved item: %s", title)

        # Mark as generating
        update_item_status(notion, page_id, GENERATING_STATUS, status_prop_name, status_prop_type)

        # Generate content
        try:
            content = gen_content.generate(brief, account_type=account_type)
            logger.info("Content generated for: %s", title)
        except Exception as exc:
            logger.error("gen_content.generate() failed for %s: %s", title, exc)
            # Revert status to approved so it can be retried
            update_item_status(notion, page_id, APPROVED_STATUS, status_prop_name, status_prop_type)
            continue

        # Mark as done
        update_item_status(notion, page_id, DONE_STATUS, status_prop_name, status_prop_type)
        content_generated += 1

    if content_generated > 0:
        # macOS notification
        send_notification(
            f"本周草稿已生成（{content_generated}篇），查看Notion",
            "XHS运营",
        )

        # Update workflow state
        update_state_field("workflow_step", "content_ready")
        today = datetime.now().strftime("%Y-%m-%d")
        update_state_field("last_content_gen_date", today)
        logger.info(
            "WORKFLOW-STATE.md updated: phase=content_ready, last_content_gen_date=%s", today
        )

    logger.info("check_approved.py done — generated %d drafts", content_generated)


if __name__ == "__main__":
    main()
