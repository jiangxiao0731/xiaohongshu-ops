#!/usr/bin/env python3
"""
analyze_performance.py — Reads TRACKER.md (or Notion 发布表现记录 database) and
produces a performance analysis with phase determination, 薯条 ROI, and 聚光 CTR.
Writes a report and updates WORKFLOW-STATE.md.
"""

import os
import sys
import re
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
TRACKER_FILE = PROJECT_DIR / "TRACKER.md"
ANALYSIS_DIR = PROJECT_DIR / "analysis"
LOG_DIR = PROJECT_DIR / "logs"
STATE_FILE = PROJECT_DIR / "WORKFLOW-STATE.md"

LOG_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "analyze_performance.log"

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
# Phase thresholds
# ---------------------------------------------------------------------------
PHASE_THRESHOLDS = {
    "修复期": (0, 50),      # avg < 50
    "建量期": (50, 200),    # 50 <= avg < 200
    "稳定期": (200, 99999), # avg >= 200
}


# ---------------------------------------------------------------------------
# WORKFLOW-STATE.md helpers (imported from utils)
# ---------------------------------------------------------------------------
from utils import read_state_field, update_state_field


# ---------------------------------------------------------------------------
# Parse TRACKER.md
# ---------------------------------------------------------------------------
def safe_int(val: str) -> int:
    val = val.strip().replace(",", "")
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def safe_float(val: str) -> float:
    val = val.strip().replace("%", "").replace(",", "")
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def parse_markdown_table(text: str) -> list[dict]:
    """Parse a simple Markdown table into a list of dicts."""
    rows = []
    lines = text.splitlines()
    headers = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not headers:
                headers = cells
                in_table = True
                continue
            # Skip separator row (---|---|...)
            if all(re.match(r"^[-:]+$", c) for c in cells if c):
                continue
            if in_table and headers:
                row = {headers[i]: cells[i] if i < len(cells) else "" for i in range(len(headers))}
                # Skip empty rows (all values empty or placeholder)
                if any(v.strip() and v.strip() != "" for v in row.values()):
                    rows.append(row)
        else:
            in_table = False
            headers = []
    return rows


def parse_tracker_md(tracker_path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Returns (company_posts, personal_posts, ad_records) parsed from TRACKER.md.
    """
    if not tracker_path.exists():
        logger.warning("TRACKER.md not found at %s", tracker_path)
        return [], [], []

    text = tracker_path.read_text(encoding="utf-8")

    # Split sections by heading
    sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
    company_posts = []
    personal_posts = []
    ad_records = []

    for section in sections:
        first_line = section.split("\n")[0].strip()
        if "公司号" in first_line:
            company_posts = parse_markdown_table(section)
        elif "个人号" in first_line:
            personal_posts = parse_markdown_table(section)
        elif "聚光" in first_line:
            ad_records = parse_markdown_table(section)

    logger.info(
        "Parsed TRACKER.md: %d company posts, %d personal posts, %d ad records",
        len(company_posts), len(personal_posts), len(ad_records),
    )
    return company_posts, personal_posts, ad_records


# ---------------------------------------------------------------------------
# Parse from Notion 发布表现记录 database
# ---------------------------------------------------------------------------
def parse_notion_performance(notion, notion_token: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Fetch posts from Notion 发布表现记录 databases using fixed IDs from notion-ids.json."""
    import json
    ids_file = Path.home() / "claude" / "xiaohongshu-ops" / "notion-ids.json"
    company_posts = []
    personal_posts = []

    try:
        ids = json.loads(ids_file.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read notion-ids.json: %s", exc)
        return [], [], []

    db_map = [
        (ids.get("company_performance_ds"), company_posts),
        (ids.get("personal_performance_ds"), personal_posts),
    ]

    for ds_id, target_list in db_map:
        if not ds_id:
            continue
        logger.info("Querying performance data source: %s", ds_id)
        try:
            cursor = None
            while True:
                kwargs = {"data_source_id": ds_id, "page_size": 100}
                if cursor:
                    kwargs["start_cursor"] = cursor
                response = notion.data_sources.query(**kwargs)
                for page in response.get("results", []):
                    props = page.get("properties", {})
                    row = {}
                    for pname, pval in props.items():
                        ptype = pval.get("type", "")
                        if ptype == "title":
                            row[pname] = "".join(t.get("plain_text", "") for t in pval.get("title", []))
                        elif ptype == "rich_text":
                            row[pname] = "".join(t.get("plain_text", "") for t in pval.get("rich_text", []))
                        elif ptype == "number":
                            row[pname] = str(pval.get("number") or 0)
                        elif ptype == "select":
                            row[pname] = (pval.get("select") or {}).get("name", "")
                        elif ptype == "date":
                            row[pname] = (pval.get("date") or {}).get("start", "")
                        elif ptype == "checkbox":
                            row[pname] = "yes" if pval.get("checkbox") else "no"
                        else:
                            row[pname] = ""
                    target_list.append(row)
                if not response.get("has_more"):
                    break
                cursor = response.get("next_cursor")
        except Exception as exc:
            logger.warning("Failed to fetch from performance data source %s: %s", ds_id, exc)

    return company_posts, personal_posts, []


# ---------------------------------------------------------------------------
# Analysis logic
# ---------------------------------------------------------------------------
def determine_phase(avg_engagement: float) -> str:
    for phase, (low, high) in PHASE_THRESHOLDS.items():
        if low <= avg_engagement < high:
            return phase
    return "修复期"


def compute_average_engagement(posts: list[dict]) -> float:
    """Average of 点赞 + 收藏 per post."""
    if not posts:
        return 0.0
    total = 0
    count = 0
    for post in posts:
        liked = safe_int(post.get("点赞", post.get("liked", "0")))
        collected = safe_int(post.get("收藏", post.get("collected", "0")))
        combined = liked + collected
        if combined > 0:
            total += combined
            count += 1
    return total / count if count > 0 else 0.0


def analyze_shudiao_roi(posts: list[dict]) -> dict:
    """
    Compare average 赞+藏 for posts with/without 薯条 investment.
    Returns a recommendation dict.
    """
    with_shudiao = []
    without_shudiao = []

    for post in posts:
        invest = post.get("是否投流", post.get("投流", "")).lower()
        liked = safe_int(post.get("点赞", "0"))
        collected = safe_int(post.get("收藏", "0"))
        combined = liked + collected
        if "是" in invest or "yes" in invest:
            with_shudiao.append(combined)
        else:
            without_shudiao.append(combined)

    avg_with = sum(with_shudiao) / len(with_shudiao) if with_shudiao else 0.0
    avg_without = sum(without_shudiao) / len(without_shudiao) if without_shudiao else 0.0

    if not with_shudiao:
        recommendation = f"暂无薯条投放数据（有机均值{avg_without:.0f}）"
        suggest = "暂不投"
    elif avg_with > avg_without * 1.3:
        recommendation = f"建议投（有机均值{avg_without:.0f}，历史薯条后均值{avg_with:.0f}，提升{((avg_with/avg_without-1)*100):.0f}%）"
        suggest = "建议投"
    else:
        recommendation = f"不投（有机均值{avg_without:.0f}，历史薯条后均值{avg_with:.0f}，提升不显著）"
        suggest = "不投"

    return {
        "avg_organic": avg_without,
        "avg_with_shudiao": avg_with,
        "posts_with_shudiao": len(with_shudiao),
        "posts_without_shudiao": len(without_shudiao),
        "recommendation": recommendation,
        "suggest": suggest,
    }


def analyze_jiguang_ctr(ad_records: list[dict]) -> dict:
    """Compute average CTR trend from 聚光 records and recommend action."""
    if not ad_records:
        return {
            "ctr_avg": 0.0,
            "records_count": 0,
            "recommendation": "暂无聚光数据",
        }

    ctrs = []
    for record in ad_records:
        ctr_raw = record.get("CTR", record.get("ctr", "0"))
        ctr = safe_float(ctr_raw)
        if ctr > 0:
            ctrs.append(ctr)

    if not ctrs:
        return {"ctr_avg": 0.0, "records_count": len(ad_records), "recommendation": "CTR数据为空"}

    avg_ctr = sum(ctrs) / len(ctrs)

    # Simple trend: compare first half vs second half
    midpoint = len(ctrs) // 2
    if midpoint > 0:
        early_avg = sum(ctrs[:midpoint]) / midpoint
        late_avg = sum(ctrs[midpoint:]) / (len(ctrs) - midpoint)
        if late_avg > early_avg * 1.1:
            trend = "上升"
            action = "增量"
        elif late_avg < early_avg * 0.9:
            trend = "下降"
            action = "减量"
        else:
            trend = "稳定"
            action = "维持"
    else:
        trend = "数据不足"
        action = "维持"

    recommendation = f"{action}（CTR={avg_ctr:.1f}%，趋势{trend}）"

    return {
        "ctr_avg": avg_ctr,
        "records_count": len(ad_records),
        "trend": trend,
        "action": action,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------
def format_report(
    today: str,
    avg_engagement: float,
    phase: str,
    previous_phase: str,
    shudiao: dict,
    jiguang: dict,
    total_posts: int,
) -> str:
    phase_changed = phase != previous_phase and previous_phase not in ("", "未知")
    phase_note = f"（从{previous_phase}升级）" if phase_changed else ""

    lines = [
        f"# 发布表现分析 {today}",
        "",
        "## 总览",
        "",
        f"- 分析帖子总数：{total_posts}",
        f"- 平均有机赞藏：{avg_engagement:.1f}",
        f"- 当前阶段：**{phase}**{phase_note}",
        "",
        "## 薯条投放建议",
        "",
        f"- {shudiao['recommendation']}",
        f"- 有机均值：{shudiao['avg_organic']:.0f}",
        f"- 薯条后均值：{shudiao['avg_with_shudiao']:.0f}（基于{shudiao['posts_with_shudiao']}篇投流帖）",
        "",
        "## 聚光投放建议",
        "",
        f"- {jiguang['recommendation']}",
    ]

    if jiguang.get("records_count", 0) > 0:
        lines.append(f"- 分析投放记录：{jiguang['records_count']}条")

    lines += [
        "",
        "---",
        f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Notion push
# ---------------------------------------------------------------------------
def push_to_notion_expense_log(notion, today: str, avg_engagement: float,
                                phase: str, shudiao: dict, jiguang: dict) -> None:
    """Append analysis result to 花钱决策日志 database."""
    import json
    ids_file = Path.home() / "claude" / "xiaohongshu-ops" / "notion-ids.json"
    db_id = None
    try:
        ids = json.loads(ids_file.read_text(encoding="utf-8"))
        db_id = ids.get("spend_log")
    except Exception as exc:
        logger.warning("Could not read spend_log from notion-ids.json: %s", exc)

    if not db_id:
        logger.warning("花钱决策日志 database not found — skipping Notion push")
        return

    try:
        notion.pages.create(
            parent={"database_id": db_id},
            properties={
                "Name": {
                    "title": [{"text": {"content": f"分析报告 {today}"}}]
                },
                "日期": {"date": {"start": today}},
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        f"阶段：{phase} | 有机均值：{avg_engagement:.1f}\n"
                                        f"薯条：{shudiao['recommendation']}\n"
                                        f"聚光：{jiguang['recommendation']}"
                                    )
                                },
                            }
                        ]
                    },
                }
            ],
        )
        logger.info("Appended to 花钱决策日志 database")
    except Exception as exc:
        logger.warning("Failed to push to 花钱决策日志: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    notion_token = os.environ.get("NOTION_TOKEN", "")

    logger.info("analyze_performance.py starting — date=%s", today)

    # Load data
    company_posts: list[dict] = []
    personal_posts: list[dict] = []
    ad_records: list[dict] = []

    if notion_token:
        try:
            from notion_client import Client  # type: ignore
            notion = Client(auth=notion_token)
            company_posts, personal_posts, _ = parse_notion_performance(notion, notion_token)
        except ImportError:
            logger.warning("notion-client not installed — falling back to TRACKER.md")
            company_posts, personal_posts, ad_records = parse_tracker_md(TRACKER_FILE)
    else:
        logger.info("NOTION_TOKEN not set — reading TRACKER.md")
        company_posts, personal_posts, ad_records = parse_tracker_md(TRACKER_FILE)

    all_posts = company_posts + personal_posts
    total_posts = len(all_posts)

    if total_posts == 0:
        logger.warning("No post data found — writing minimal report")
        avg_engagement = 0.0
    else:
        avg_engagement = compute_average_engagement(all_posts)

    phase = determine_phase(avg_engagement)
    previous_phase = read_state_field("current_phase") or "未知"

    shudiao = analyze_shudiao_roi(all_posts)
    jiguang = analyze_jiguang_ctr(ad_records)

    logger.info(
        "Results: avg_engagement=%.1f, phase=%s, shudiao=%s, jiguang=%s",
        avg_engagement, phase, shudiao["suggest"], jiguang.get("action", "N/A"),
    )

    # Write report
    report = format_report(today, avg_engagement, phase, previous_phase, shudiao, jiguang, total_posts)
    report_path = ANALYSIS_DIR / f"performance-{today}.md"
    report_path.write_text(report, encoding="utf-8")
    logger.info("Report written to %s", report_path)

    # Push to Notion if available
    if notion_token:
        try:
            from notion_client import Client  # type: ignore
            notion = Client(auth=notion_token)
            push_to_notion_expense_log(notion, today, avg_engagement, phase, shudiao, jiguang)
        except ImportError:
            logger.warning("notion-client not installed — skipping Notion push")
        except Exception as exc:
            logger.warning("Notion push failed: %s", exc)

    # Write summary JSON for downstream scripts (weekly_planner.py)
    import json
    summary = {
        "date": today,
        "avg_engagement": avg_engagement,
        "phase": phase,
        "previous_phase": previous_phase,
        "shudiao_suggest": shudiao["suggest"],
        "shudiao_recommendation": shudiao["recommendation"],
        "jiguang_action": jiguang.get("action", "N/A"),
        "jiguang_recommendation": jiguang["recommendation"],
        "total_posts": total_posts,
    }
    summary_path = ANALYSIS_DIR / "latest-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Summary JSON written to %s", summary_path)

    # Update WORKFLOW-STATE.md
    update_state_field("current_phase", phase)
    update_state_field("last_analysis_date", today)
    logger.info(
        "WORKFLOW-STATE.md updated: current_phase=%s, last_analysis_date=%s", phase, today
    )

    print(report)


if __name__ == "__main__":
    main()
