#!/usr/bin/env python3
"""
setup_notion.py
Creates the full Notion database structure for the XHS automation system
under parent page 32693fe4326480e386e3fc6a049fff07.
Saves database IDs to ~/xiaohongshu-ops/notion-ids.json.
"""

import os
import sys
import json
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
try:
    from notion_client import Client
    from notion_client.errors import APIResponseError
except ImportError:
    print("ERROR: notion-client is not installed.")
    print("Install it with:")
    print("  ~/xiaohongshu-ops/.venv/bin/pip install notion-client")
    print("  -- or --")
    print("  pip install notion-client")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Token check
# ---------------------------------------------------------------------------
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
if not NOTION_TOKEN:
    print("ERROR: NOTION_TOKEN environment variable is not set.")
    print()
    print("Steps to fix:")
    print("  1. Go to https://www.notion.so/my-integrations")
    print("  2. Create an integration and copy the Internal Integration Token")
    print("  3. Share your parent page with the integration")
    print("  4. Run:  export NOTION_TOKEN='secret_xxxx'")
    print("  5. Re-run this script")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PARENT_PAGE_ID = "32693fe4326480e386e3fc6a049fff07"
IDS_OUTPUT_PATH = Path.home() / "claude" / "xiaohongshu-ops" / "notion-ids.json"

notion = Client(auth=NOTION_TOKEN)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sleep():
    """Pause briefly between API calls to respect rate limits."""
    time.sleep(0.5)


def make_title_prop():
    return {"title": {}}


def make_number_prop():
    return {"number": {"format": "number"}}


def make_date_prop():
    return {"date": {}}


def make_checkbox_prop():
    return {"checkbox": {}}


def make_rich_text_prop():
    return {"rich_text": {}}


def make_select_prop(options):
    """
    options: list of str  →  [{"name": str, "color": "default"}, ...]
    """
    return {
        "select": {
            "options": [{"name": o, "color": "default"} for o in options]
        }
    }


def create_database(parent_page_id, title, properties):
    """Create a Notion database under parent_page_id and return the response."""
    print(f"  Creating database: {title} ...")
    response = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": title}}],
        properties=properties,
    )
    sleep()
    print(f"    Done — ID: {response['id']}")
    return response


# ---------------------------------------------------------------------------
# Database definitions
# ---------------------------------------------------------------------------

def create_company_drafts(parent_id):
    """a) 公司号内容草稿库"""
    props = {
        "标题": make_title_prop(),
        "周次": make_number_prop(),
        "类型": make_select_prop([
            "创意技术教程",
            "作品集方法论",
            "方向信息干货",
            "offer案例拆解",
            "碎片感想",
        ]),
        "正文": make_rich_text_prop(),
        "标签": make_rich_text_prop(),
        "状态": make_select_prop([
            "待审批",
            "已批准",
            "草稿生成中",
            "草稿就绪",
            "已发布",
        ]),
        "发布日期": make_date_prop(),
        "封面建议": make_rich_text_prop(),
    }
    return create_database(parent_id, "公司号内容草稿库", props)


def create_company_performance(parent_id):
    """b) 公司号发布表现记录"""
    props = {
        "标题": make_title_prop(),
        "发布日期": make_date_prop(),
        "赞": make_number_prop(),
        "藏": make_number_prop(),
        "评论": make_number_prop(),
        "私信": make_number_prop(),
        "薯条投放": make_checkbox_prop(),
        "薯条金额": make_number_prop(),
        "聚光CTR": make_number_prop(),
        "有机赞藏均值": make_rich_text_prop(),
        "备注": make_rich_text_prop(),
    }
    return create_database(parent_id, "公司号发布表现记录", props)


def create_personal_drafts(parent_id):
    """c) 个人号内容草稿库 — same as company drafts minus 周次"""
    props = {
        "标题": make_title_prop(),
        "类型": make_select_prop([
            "创意技术教程",
            "作品集方法论",
            "方向信息干货",
            "offer案例拆解",
            "碎片感想",
        ]),
        "正文": make_rich_text_prop(),
        "标签": make_rich_text_prop(),
        "状态": make_select_prop([
            "待审批",
            "已批准",
            "草稿生成中",
            "草稿就绪",
            "已发布",
        ]),
        "发布日期": make_date_prop(),
        "封面建议": make_rich_text_prop(),
    }
    return create_database(parent_id, "个人号内容草稿库", props)


def create_personal_performance(parent_id):
    """d) 个人号发布表现记录"""
    props = {
        "标题": make_title_prop(),
        "发布日期": make_date_prop(),
        "赞": make_number_prop(),
        "藏": make_number_prop(),
        "新粉": make_number_prop(),
        "加热投放": make_checkbox_prop(),
        "备注": make_rich_text_prop(),
    }
    return create_database(parent_id, "个人号发布表现记录", props)


def create_competitor_weekly(parent_id):
    """e) 竞品周报"""
    props = {
        "周次": make_title_prop(),
        "日期": make_date_prop(),
        "热门标签": make_rich_text_prop(),
        "TOP5帖子": make_rich_text_prop(),
        "标题格式趋势": make_rich_text_prop(),
        "内容建议": make_rich_text_prop(),
    }
    return create_database(parent_id, "竞品周报", props)


def create_spend_log(parent_id):
    """f) 花钱决策日志"""
    props = {
        "标题": make_title_prop(),
        "日期": make_date_prop(),
        "渠道": make_select_prop(["薯条", "聚光", "其他"]),
        "金额": make_number_prop(),
        "原因": make_rich_text_prop(),
        "结果": make_rich_text_prop(),
    }
    return create_database(parent_id, "花钱决策日志", props)


# ---------------------------------------------------------------------------
# Callout block on parent page
# ---------------------------------------------------------------------------

def create_status_callout(parent_page_id):
    """Prepend a yellow callout block to the parent page."""
    print("  Adding 本周状态 callout to parent page ...")
    notion.blocks.children.append(
        block_id=parent_page_id,
        children=[
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "本周状态"
                            },
                            "annotations": {"bold": True},
                        },
                        {
                            "type": "text",
                            "text": {"content": "\n"},
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": (
                                    "当前阶段: 修复期 Week 1 | "
                                    "待办: 改名+隐藏违规帖+发第一篇 | "
                                    "付费: 薯条待开"
                                )
                            },
                        },
                    ],
                    "icon": {"type": "emoji", "emoji": "📌"},
                    "color": "yellow_background",
                },
            }
        ],
    )
    sleep()
    print("    Done.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("XHS Notion Setup")
    print(f"Parent page: {PARENT_PAGE_ID}")
    print("=" * 60)

    # Verify parent page is accessible
    print("\nVerifying parent page access ...")
    try:
        notion.pages.retrieve(page_id=PARENT_PAGE_ID)
        sleep()
        print("  Parent page accessible.")
    except APIResponseError as e:
        print(f"ERROR: Cannot access parent page — {e}")
        print()
        print("Make sure you have shared the page with your integration:")
        print("  1. Open the page in Notion")
        print("  2. Click '...' menu → Connections → Add connection → your integration")
        sys.exit(1)

    print("\nCreating databases ...")
    ids = {}

    try:
        r = create_company_drafts(PARENT_PAGE_ID)
        ids["company_drafts"] = r["id"]

        r = create_company_performance(PARENT_PAGE_ID)
        ids["company_performance"] = r["id"]

        r = create_personal_drafts(PARENT_PAGE_ID)
        ids["personal_drafts"] = r["id"]

        r = create_personal_performance(PARENT_PAGE_ID)
        ids["personal_performance"] = r["id"]

        r = create_competitor_weekly(PARENT_PAGE_ID)
        ids["competitor_weekly"] = r["id"]

        r = create_spend_log(PARENT_PAGE_ID)
        ids["spend_log"] = r["id"]

    except APIResponseError as e:
        print(f"\nERROR during database creation: {e}")
        sys.exit(1)

    print("\nAdding status callout ...")
    try:
        create_status_callout(PARENT_PAGE_ID)
    except APIResponseError as e:
        # Non-fatal — databases were created successfully
        print(f"  WARNING: Could not add callout block — {e}")

    # Save IDs
    IDS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(IDS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)

    print(f"\nDatabase IDs saved to: {IDS_OUTPUT_PATH}")

    print("\n" + "=" * 60)
    print("Setup complete. Databases created:")
    labels = {
        "company_drafts":      "公司号内容草稿库",
        "company_performance": "公司号发布表现记录",
        "personal_drafts":     "个人号内容草稿库",
        "personal_performance":"个人号发布表现记录",
        "competitor_weekly":   "竞品周报",
        "spend_log":           "花钱决策日志",
    }
    for key, db_id in ids.items():
        print(f"  {labels.get(key, key):20s}  {db_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
