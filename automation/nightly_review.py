#!/usr/bin/env python3
"""
nightly_review.py — Run at 23:45 NYC every night.
1. Read Notion 今日待办 page, check which items are done/undone.
2. Log the result to logs/nightly_review.jsonl (append).
3. Send Slack summary of what was missed.
4. If critical items missed (e.g. setting up scheduled post), flag urgently.
5. Write undone items to WORKFLOW-STATE.md missed_tasks field for future reference.
"""

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import load_env, read_state_field, update_state_field

load_env()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL", "")

if not NOTION_TOKEN:
    print("ERROR: NOTION_TOKEN not set")
    sys.exit(1)

try:
    from notion_client import Client
except ImportError:
    print("ERROR: notion-client not installed")
    sys.exit(1)

notion = Client(auth=NOTION_TOKEN)

ROOT_PAGE_ID = "32693fe4326480e386e3fc6a049fff07"
PROJECT_DIR = Path.home() / "claude" / "xiaohongshu-ops"
LOG_FILE = PROJECT_DIR / "logs" / "nightly_review.jsonl"
IDS_FILE = PROJECT_DIR / "notion-ids.json"

today = datetime.date.today()
dow = today.isoweekday()
dow_names = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}


def send_slack(message):
    if not SLACK_WEBHOOK:
        return
    payload = json.dumps({
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": message}}
        ]
    })
    subprocess.run(
        ["curl", "-s", "-X", "POST", "-H", "Content-type: application/json",
         "--data", payload, SLACK_WEBHOOK],
        check=False, capture_output=True,
    )


def find_todo_callout_id():
    """Find the callout block ID from stored IDs or by scanning the root page."""
    if IDS_FILE.exists():
        ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
        stored_id = ids.get("todo_callout_block")
        if stored_id:
            try:
                block = notion.blocks.retrieve(block_id=stored_id)
                if not block.get("archived", False):
                    return stored_id
            except Exception:
                pass

    # Fallback: scan first 10 blocks for the clipboard callout
    children = notion.blocks.children.list(block_id=ROOT_PAGE_ID, page_size=10)
    for block in children["results"]:
        if block["type"] == "callout":
            icon = block["callout"].get("icon", {}).get("emoji", "")
            if icon == "\U0001f4cb":  # clipboard emoji
                return block["id"]
    return None


def read_todos(callout_id):
    """Read all to_do blocks from the callout children. Return (done_list, undone_list)."""
    done = []
    undone = []
    children = notion.blocks.children.list(block_id=callout_id, page_size=100)
    for block in children["results"]:
        if block["type"] == "to_do":
            text_parts = block["to_do"].get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in text_parts)
            if block["to_do"].get("checked", False):
                done.append(text)
            else:
                undone.append(text)
    return done, undone


def is_critical(item_text):
    """Check if an undone item is critical (posting-related)."""
    critical_keywords = ["定时发布", "发布", "薯条", "草稿", "封面"]
    return any(kw in item_text for kw in critical_keywords)


def log_review(done, undone):
    """Append review to JSONL log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": today.isoformat(),
        "dow": dow_names[dow],
        "total": len(done) + len(undone),
        "done": done,
        "undone": undone,
        "completion_rate": round(len(done) / max(len(done) + len(undone), 1) * 100),
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def update_state_missed(undone):
    """Write missed tasks to WORKFLOW-STATE.md for future scripts to read."""
    if undone:
        # Keep only the most recent missed tasks (overwrite)
        missed_str = " | ".join(undone[:5])  # max 5 items
        update_state_field("last_missed_tasks", missed_str)
        update_state_field("last_missed_date", today.isoformat())
    else:
        update_state_field("last_missed_tasks", "none")
        update_state_field("last_missed_date", today.isoformat())


def build_slack_message(done, undone):
    """Build Slack nightly summary."""
    total = len(done) + len(undone)
    if total == 0:
        return None  # No TODOs today, skip

    rate = round(len(done) / total * 100)

    critical_missed = [item for item in undone if is_critical(item)]

    lines = []
    lines.append(f":moon: *{today.isoformat()} {dow_names[dow]} 今日回顾*")
    lines.append(f"完成率: {len(done)}/{total} ({rate}%)")

    if not undone:
        lines.append(":white_check_mark: 全部完成！")
    else:
        lines.append("")
        lines.append("*未完成:*")
        for item in undone:
            prefix = ":rotating_light:" if is_critical(item) else ":x:"
            lines.append(f"{prefix} {item}")

    if critical_missed:
        lines.append("")
        lines.append(":warning: *关键任务未完成 — 可能影响明天发帖，请立即处理*")

    if done:
        lines.append("")
        lines.append("*已完成:*")
        for item in done:
            lines.append(f":white_check_mark: {item}")

    return "\n".join(lines)


def main():
    callout_id = find_todo_callout_id()
    if not callout_id:
        print("No TODO callout found, skipping review")
        return

    done, undone = read_todos(callout_id)

    if not done and not undone:
        print("No TODO items found, skipping review")
        return

    # Log
    entry = log_review(done, undone)
    print(f"Review: {entry['done'].__len__()} done, {entry['undone'].__len__()} undone, {entry['completion_rate']}%")

    # Update state
    update_state_missed(undone)

    # Slack
    msg = build_slack_message(done, undone)
    if msg:
        send_slack(msg)
        print("Slack review sent")

    # If critical items missed on Tuesday (tomorrow is posting day), extra alert
    if dow == 2:  # Tuesday night
        critical = [item for item in undone if is_critical(item)]
        if critical:
            alert = ":rotating_light: :rotating_light: *警告: 明天是发帖日但定时发布还没设好！*\n"
            alert += "现在去设：XHS 创作者中心 → 发布 → 定时 19:00 北京"
            send_slack(alert)
            print("CRITICAL: Posting day prep not done!")


if __name__ == "__main__":
    main()
