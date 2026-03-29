#!/usr/bin/env python3
"""
notion_daily_todo.py — Update the 今晚待办 callout on the root page inline.
Runs every evening at 21:00 NYC. Deletes old callout children, inserts new ones.
The nightly_review.py reads the to_do blocks from this callout at 23:45.
"""

import os
import sys
import json
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import load_env, read_state_field

load_env()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
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
IDS_FILE = Path.home() / "claude" / "xiaohongshu-ops" / "notion-ids.json"

# Data source IDs (read from notion-ids.json)
_ids_data = json.loads(IDS_FILE.read_text(encoding="utf-8")) if IDS_FILE.exists() else {}
COMPANY_DRAFTS_DS = _ids_data.get("company_drafts_ds", "")
PERSONAL_DRAFTS_DS = _ids_data.get("personal_drafts_ds", "")

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
phase = read_state_field("phase") or "repair"
phase_week = read_state_field("current_phase_week") or "1"
last_publish = read_state_field("last_publish_date") or ""
warmup_complete = read_state_field("warmup_complete") or "no"

today = datetime.date.today()
tomorrow = today + datetime.timedelta(days=1)
dow = today.isoweekday()
tomorrow_dow = tomorrow.isoweekday()

dow_names = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
phase_cn = {"repair": "修复期", "building": "建量期", "stable": "稳定期"}.get(phase, phase)

POSTING_TIME = "北京 19:00（纽约 7:00AM）"
COMPANY = "公司号「蕉蕉椒椒（作品集版）」"
PERSONAL = "个人号「蕉蕉椒椒」"

in_warmup = (phase == "repair" and phase_week == "1" and warmup_complete != "yes")


# ---------------------------------------------------------------------------
# Fetch drafts from Notion databases (returns list of {title, url})
# ---------------------------------------------------------------------------
def page_url(page_id):
    """Build a Notion page URL from a page ID."""
    return "https://www.notion.so/" + page_id.replace("-", "")


def fetch_drafts(data_source_id):
    """Query a Notion data source. Return list of {title, url}, excluding published items."""
    try:
        results = notion.data_sources.query(data_source_id=data_source_id, page_size=20)
        drafts = []
        for page in results["results"]:
            pid = page.get("id", "")
            props = page.get("properties", {})

            # Skip items with status "已发布" (auto-detect status property name)
            skip = False
            for status_key in ("状态", "Status", "审批状态"):
                status_prop = props.get(status_key, {})
                if status_prop.get("type") == "status":
                    status_name = (status_prop.get("status") or {}).get("name", "")
                    if status_name == "已发布":
                        skip = True
                        break
                elif status_prop.get("type") == "select":
                    status_name = (status_prop.get("select") or {}).get("name", "")
                    if status_name == "已发布":
                        skip = True
                        break
            if skip:
                continue

            # Extract title (auto-detect title property name)
            title = ""
            for title_key in ("名称", "Name", "标题", "Title"):
                title_prop = props.get(title_key, {})
                if title_prop.get("type") == "title":
                    parts = title_prop.get("title", [])
                    title = "".join(t.get("plain_text", "") for t in parts)
                    break

            if title:
                drafts.append({"title": title, "url": page_url(pid)})
        return drafts
    except Exception as e:
        print(f"Warning: could not fetch drafts from {data_source_id}: {e}")
        return []


def find_draft(drafts, pattern):
    """Find a draft whose title contains pattern."""
    for d in drafts:
        if pattern in d["title"]:
            return d
    return None


def find_all_drafts(drafts, pattern):
    """Find all drafts whose title contains pattern."""
    return [d for d in drafts if pattern in d["title"]]


# ---------------------------------------------------------------------------
# Block builders
# ---------------------------------------------------------------------------
def make_todo(text, link=None):
    """Build a to_do block. If link provided, append it as a clickable link."""
    rich = [{"type": "text", "text": {"content": text}}]
    if link:
        rich.append({"type": "text", "text": {"content": " → "}, "annotations": {"color": "gray"}})
        rich.append({
            "type": "text",
            "text": {"content": "打开草稿", "link": {"url": link}},
            "annotations": {"color": "blue", "underline": True},
        })
    return {
        "object": "block", "type": "to_do",
        "to_do": {"rich_text": rich, "checked": False},
    }


def make_heading(content):
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{
            "type": "text",
            "text": {"content": content},
            "annotations": {"bold": True},
        }]},
    }


def make_note(content):
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{
            "type": "text",
            "text": {"content": content},
            "annotations": {"italic": True, "color": "gray"},
        }]},
    }


# ---------------------------------------------------------------------------
# Build TODO children (blocks inside the callout)
# ---------------------------------------------------------------------------
def build_todo_children():
    """Return list of block dicts to go inside the callout as children."""
    blocks = []

    # Fetch current drafts from Notion
    company_drafts = fetch_drafts(COMPANY_DRAFTS_DS)
    personal_drafts = fetch_drafts(PERSONAL_DRAFTS_DS)

    week_draft = find_draft(company_drafts, f"[Week{phase_week}]")
    personal_warmup = find_all_drafts(personal_drafts, "[暖号")
    company_warmup = find_all_drafts(company_drafts, "[暖号")
    sunday_draft = find_draft(company_drafts, f"[Week{phase_week}-日]")

    # Fallback display names
    wd_title = week_draft["title"] if week_draft else f"Week {phase_week} 草稿（未找到）"
    wd_url = week_draft["url"] if week_draft else None
    sd_title = sunday_draft["title"] if sunday_draft else f"Week {phase_week} 周日草稿（未找到）"
    sd_url = sunday_draft["url"] if sunday_draft else None

    # --- Data entry overdue (any day) ---
    if last_publish:
        try:
            pub = datetime.date.fromisoformat(last_publish)
            if (today - pub).days >= 3:
                blocks.append(make_todo(
                    f"数据录入逾期 — {COMPANY} 帖子 {last_publish} 已超72h，去 Notion 发布表现记录填写赞/藏/评/私信数"
                ))
        except ValueError:
            pass

    # --- WARMUP MODE: both accounts warm up before formal content ---
    if in_warmup:
        blocks.append(make_heading("暖号期 — 两个号都先发暖号帖，正式内容暂不发"))
        blocks.append(make_note(
            "个人号休眠6个月 + 公司号刚隐藏大量旧帖并改名，算法需要重新识别两个账号。"
            "先各发2条轻量暖号帖，不追数据。发完等2-3天再上正式内容。"
        ))

        # Personal account warmup
        blocks.append(make_heading(f"{PERSONAL} 暖号帖"))
        for wd in personal_warmup:
            blocks.append(make_todo(
                f"发暖号帖「{wd['title']}」→ 小红书直接发布（随手发，不定时）",
                link=wd["url"],
            ))
        if not personal_warmup:
            blocks.append(make_todo("随手拍一段TD录屏发出去"))

        # Company account warmup
        blocks.append(make_heading(f"{COMPANY} 暖号帖"))
        for wd in company_warmup:
            blocks.append(make_todo(
                f"发暖号帖「{wd['title']}」→ 小红书直接发布（随手发，不定时）",
                link=wd["url"],
            ))
        if not company_warmup:
            blocks.append(make_todo("发一条轻量作品集相关内容（排版tip/方向科普）"))

        # Daily warmup behavior
        blocks.append(make_heading("每天养号操作（两个号都做）"))
        blocks.append(make_todo("小红书搜索「作品集」「交互设计留学」「数媒留学」→ 浏览同赛道内容10分钟"))
        blocks.append(make_todo("给3-5条同赛道帖子点赞 + 留有价值的评论（不要广告）"))
        blocks.append(make_todo("发完后回来勾选，全部发完后把 WORKFLOW-STATE.md warmup_complete 改为 yes"))
        blocks.append(make_note(
            f"暖号完成后，下次运行本脚本会自动切换到正常周计划（{COMPANY}周三发「{wd_title}」）"
        ))
        return blocks

    # --- NORMAL MODE: day-specific TODOs ---

    if dow == 1:  # Monday
        blocks.append(make_heading("今晚 — 本周规划"))
        blocks.append(make_todo("打开 Notion 竞品周报（昨晚自动生成）→ 花5分钟看看竞品本周发了什么"))
        blocks.append(make_todo(
            f"打开{COMPANY}草稿库 → 检查本周草稿「{wd_title}」→ 补充/修改 → 状态改「已批准」",
            link=wd_url,
        ))
        blocks.append(make_todo("更新 WORKFLOW-STATE.md → current_phase_week 改为本周周数"))

        blocks.append(make_heading(f"明天 {dow_names[tomorrow_dow]} 预告"))
        blocks.append(make_todo(f"明晚是关键夜 — 要为{COMPANY}设好周三定时发布"))

    elif dow == 2:  # Tuesday — CRITICAL: set up Wednesday company post
        blocks.append(make_heading(f"今晚必须完成 — 明天周三是{COMPANY}发帖日"))
        blocks.append(make_todo(
            f"打开草稿「{wd_title}」→ 复制正文内容",
            link=wd_url,
        ))
        blocks.append(make_todo(f"打开小红书创作者中心 → {COMPANY} → 点「发布笔记」"))
        blocks.append(make_todo(f"粘贴正文 + 配图/封面 → 设定时发布：{POSTING_TIME}"))
        blocks.append(make_todo("发布设置里勾选「AI辅助生成」标注（国家法规强制要求）"))
        blocks.append(make_todo("检查标签（不超过10个）、封面图、正文排版"))
        blocks.append(make_todo(
            f"打开 Notion 发布表现记录 → 新建一行：日期 {tomorrow.isoformat()}，标题「{wd_title}」"
        ))
        if phase == "repair":
            budget = "150元" if phase_week == "1" else "50元"
            blocks.append(make_heading("明早帖子发出后"))
            blocks.append(make_todo(
                f"帖子发出后（明早 7:30AM NYC）去开薯条：目标「互动」，时长3天，预算 {budget}"
            ))
            if phase_week == "1":
                blocks.append(make_note("Week 1 投150元是为了加量诊断账号是否被限流，不是常规预算"))

    elif dow == 3:  # Wednesday — company post day
        blocks.append(make_heading(f"今晚 — {COMPANY}发帖日检查"))
        blocks.append(make_todo(f"确认{COMPANY}帖子「{wd_title}」已按时发出（{POSTING_TIME}）"))
        blocks.append(make_todo("如果还没开薯条 → 现在去开：目标「互动」，3天"))
        blocks.append(make_todo(f"去{COMPANY}帖子下面回复前3-5条评论（发布当天互动有算法加权）"))
        blocks.append(make_todo(f"去{PERSONAL}回复评论和私信"))
        blocks.append(make_heading(f"明天 {dow_names[tomorrow_dow]} 预告"))
        blocks.append(make_todo("明天无发帖任务，回复评论即可"))

    elif dow == 4:  # Thursday
        blocks.append(make_heading("今晚 — 互动 + 数据检查"))
        blocks.append(make_todo(f"{COMPANY} → 回复新评论和私信"))
        blocks.append(make_todo(f"{PERSONAL} → 回复新评论和私信"))
        blocks.append(make_todo(
            f"{COMPANY} → 查看帖子「{wd_title}」的曝光/赞藏数据（创作者中心 → 数据中心）"
        ))
        blocks.append(make_todo("如果曝光 <100 → 可能被限流，记录到 WORKFLOW-STATE.md notes"))

    elif dow == 5:  # Friday
        blocks.append(make_heading("今晚 — 薯条效果 + 周末规划"))
        blocks.append(make_todo(f"{COMPANY} + {PERSONAL} → 回复评论和私信"))
        blocks.append(make_todo(
            f"检查薯条投放效果：小红书 → 推广中心 → 查看「{wd_title}」的薯条数据"
        ))
        blocks.append(make_todo("薯条判断：曝光>500 = 没被限流 / <100 = 确认限流"))
        if phase in ("building", "stable"):
            blocks.append(make_heading(f"周末要发周日帖 — {COMPANY}"))
            blocks.append(make_todo(
                f"明晚设好周日帖「{sd_title}」的定时发布",
                link=sd_url,
            ))

    elif dow == 6:  # Saturday
        if phase in ("building", "stable"):
            blocks.append(make_heading(f"今晚必须完成 — 明天周日是{COMPANY}第二篇发帖日"))
            blocks.append(make_todo(
                f"打开草稿「{sd_title}」→ 复制正文",
                link=sd_url,
            ))
            blocks.append(make_todo(f"小红书创作者中心 → {COMPANY} → 发布 → 定时 {POSTING_TIME}"))
            blocks.append(make_todo("勾选「AI辅助生成」标注"))
            blocks.append(make_todo("检查标签、封面图、正文排版"))
            blocks.append(make_todo(
                f"Notion 发布表现记录新建一行：{tomorrow.isoformat()}，标题「{sd_title}」"
            ))
        else:
            blocks.append(make_heading("今晚 — 轻松日"))
            blocks.append(make_todo(f"{COMPANY} + {PERSONAL} → 回复评论和私信"))

    elif dow == 7:  # Sunday
        blocks.append(make_heading("今晚 — 本周收尾"))
        blocks.append(make_todo(f"{COMPANY} + {PERSONAL} → 回复评论和私信"))
        if phase in ("building", "stable"):
            blocks.append(make_todo(f"确认{COMPANY}周日帖已按时发出"))
            blocks.append(make_todo("回复周日帖下的前几条评论"))
        blocks.append(make_heading(f"明天 {dow_names[tomorrow_dow]} 预告"))
        blocks.append(make_todo("明晚：查看竞品周报 + 审批本周草稿 + 更新 phase_week"))

    return blocks


# ---------------------------------------------------------------------------
# Find existing callout block by scanning page children
# ---------------------------------------------------------------------------
def find_todo_callout_id():
    """Find the callout block at top of root page."""
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

    children = notion.blocks.children.list(block_id=ROOT_PAGE_ID, page_size=10)
    for block in children["results"]:
        if block["type"] == "callout":
            icon = block["callout"].get("icon", {}).get("emoji", "")
            if icon == "\U0001f4cb":
                return block["id"]
    return None


def save_block_id(block_id):
    """Update notion-ids.json with new callout block ID."""
    ids = {}
    if IDS_FILE.exists():
        ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    ids["todo_callout_block"] = block_id
    IDS_FILE.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main: update callout in-place
# ---------------------------------------------------------------------------
def update_todo():
    """Update existing callout in-place, or create if missing."""
    phase_label = "暖号期" if in_warmup else phase_cn
    header = f"{today.isoformat()} {dow_names[dow]}晚 · {phase_label} Week {phase_week}"
    todo_children = build_todo_children()

    old_id = find_todo_callout_id()

    if old_id:
        notion.blocks.update(
            block_id=old_id,
            callout={
                "rich_text": [
                    {"type": "text", "text": {"content": "今晚待办"}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": f" · {header}"}},
                ],
                "icon": {"type": "emoji", "emoji": "\U0001f4cb"},
                "color": "blue_background",
            },
        )

        existing = notion.blocks.children.list(block_id=old_id, page_size=100)
        for block in existing["results"]:
            try:
                notion.blocks.delete(block_id=block["id"])
            except Exception:
                pass

        if todo_children:
            notion.blocks.children.append(block_id=old_id, children=todo_children)

        print(f"Updated TODO callout in-place: {old_id}")
    else:
        callout_block = {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": "今晚待办"}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": f" · {header}"}},
                ],
                "icon": {"type": "emoji", "emoji": "\U0001f4cb"},
                "color": "blue_background",
                "children": todo_children,
            },
        }
        result = notion.blocks.children.append(
            block_id=ROOT_PAGE_ID,
            children=[callout_block],
        )
        new_id = result["results"][0]["id"]
        save_block_id(new_id)
        print(f"Created TODO callout: {new_id}")

    print(f"Done: {today.isoformat()} {dow_names[dow]}晚 ({phase_label})")


if __name__ == "__main__":
    update_todo()
