#!/bin/bash
# slack_daily.sh — Evening TODO: what to do tonight + what's coming tomorrow.
# Runs via launchd at 21:00 NYC every day.
# Logic: "you can't wake up at 7:30 AM, so set up scheduled publish TONIGHT."

PROJECT_DIR="$HOME/claude/xiaohongshu-ops"
STATE_FILE="$PROJECT_DIR/WORKFLOW-STATE.md"
ENV_FILE="$PROJECT_DIR/.env"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/slack_daily.log"

mkdir -p "$LOG_DIR"

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

send_slack() {
    local payload="$1"
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        log "SLACK_WEBHOOK_URL not set — skipping"
        return 1
    fi
    local http_code
    http_code=$(curl -s -o /dev/null -w '%{http_code}' \
        -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" 2>> "$LOG_FILE")
    if [ "$http_code" = "200" ]; then
        log "Slack sent OK"
    else
        log "Slack error: HTTP $http_code"
    fi
}

# ---------------------------------------------------------------------------
# Read state
# ---------------------------------------------------------------------------
read_field() {
    local field="$1"
    if [ -f "$STATE_FILE" ]; then
        grep "^${field}:" "$STATE_FILE" | sed "s/^${field}:[[:space:]]*//" | sed 's/  #.*//' | xargs
    fi
}

PHASE="$(read_field "phase")"
PHASE_WEEK="$(read_field "current_phase_week")"
LAST_PUBLISH="$(read_field "last_publish_date")"
LAST_DATA="$(read_field "last_data_entry_date")"
COMPANY_COUNT="$(read_field "company_post_count_this_month")"

TODAY="$(date '+%Y-%m-%d')"
DOW="$(date '+%u')"  # 1=Mon … 7=Sun

# Tomorrow's day of week
TOMORROW_DOW=$(( DOW % 7 + 1 ))
TOMORROW_DATE="$(date -v+1d '+%Y-%m-%d')"

# Day names
DOW_NAMES=("" "周一" "周二" "周三" "周四" "周五" "周六" "周日")
TODAY_CN="${DOW_NAMES[$DOW]}"
TOMORROW_CN="${DOW_NAMES[$TOMORROW_DOW]}"

case "$PHASE" in
    repair)   PHASE_CN="修复期" ;;
    building) PHASE_CN="建量期" ;;
    stable)   PHASE_CN="稳定期" ;;
    *)        PHASE_CN="$PHASE" ;;
esac

# ---------------------------------------------------------------------------
# Build TODO list: evening perspective (tonight + tomorrow)
# ---------------------------------------------------------------------------
TODOS=""
URGENT=""

# Data entry overdue
if [ -n "$LAST_PUBLISH" ]; then
    PUBLISH_EPOCH="$(date -j -f '%Y-%m-%d' "$LAST_PUBLISH" '+%s' 2>/dev/null || echo 0)"
    NOW_EPOCH="$(date +%s)"
    if [ "$PUBLISH_EPOCH" -gt 0 ]; then
        DIFF_H=$(( (NOW_EPOCH - PUBLISH_EPOCH) / 3600 ))
        if [ "$DIFF_H" -ge 72 ] && [ -z "$LAST_DATA" -o "$LAST_DATA" \< "$LAST_PUBLISH" ]; then
            URGENT="${URGENT}:bar_chart: *数据录入逾期* — 帖子已发布 ${DIFF_H}h，今晚录入赞/藏/评/私信\n"
        fi
    fi
fi

# --- Tonight + tomorrow logic ---

case "$DOW" in
    1)  # Monday evening → tomorrow is Tuesday (personal post day)
        TODOS=":clipboard: *今晚*\n"
        TODOS="${TODOS}:one: 查看 Notion 竞品周报\n"
        TODOS="${TODOS}:two: Notion 草稿库填写本周背景（有新TD？有新案例？）→ 改「已批准」\n"
        TODOS="${TODOS}:three: 更新 WORKFLOW-STATE.md 的 current_phase_week\n\n"
        TODOS="${TODOS}:crystal_ball: *明天周二*\n"
        TODOS="${TODOS}:art: 个人号有 TD 作品可以发（提前设好定时 19:30 北京）"
        ;;
    2)  # Tuesday evening → tomorrow is Wednesday (COMPANY POSTING DAY)
        TODOS=":mega: *今晚必须完成 — 明天是公司号发帖日*\n\n"
        TODOS="${TODOS}:one: 打开 Notion 草稿库 → 复制本周公司号草稿\n"
        TODOS="${TODOS}:two: XHS 创作者中心 → 发布 → *设定时发布：北京 19:30*\n"
        TODOS="${TODOS}:three: 勾选「AI辅助生成」标注\n"
        TODOS="${TODOS}:four: 确认封面和配图已准备好\n"
        TODOS="${TODOS}:five: Notion 发布表现记录新建一行：${TOMORROW_DATE} + 标题\n"
        if [ "$PHASE" = "repair" ]; then
            if [ "$PHASE_WEEK" = "1" ]; then
                TODOS="${TODOS}:six: *明早帖子发出后*开薯条：互动，3天，*150元*（加量诊断）"
            else
                TODOS="${TODOS}:six: *明早帖子发出后*开薯条：互动，3天，*50元*"
            fi
        fi
        ;;
    3)  # Wednesday evening → post already scheduled, now monitor
        TODOS=":white_check_mark: *今晚*\n"
        TODOS="${TODOS}:one: 确认公司号帖子已按时发出（北京 19:30）\n"
        TODOS="${TODOS}:two: 开薯条（如果还没开）\n"
        TODOS="${TODOS}:three: 回复前几条评论（发布后互动有加权）\n\n"
        TODOS="${TODOS}:crystal_ball: *明天周四*\n"
        TODOS="${TODOS}:art: 个人号有新 TD/AI 作品可以发（提前设好定时）"
        ;;
    4)  # Thursday evening
        TODOS=":speech_balloon: *今晚*\n"
        TODOS="${TODOS}:one: 回复公司号 + 个人号的评论和私信\n"
        TODOS="${TODOS}:two: 检查公司号帖曝光初步数据"
        ;;
    5)  # Friday evening
        TODOS=":speech_balloon: *今晚*\n"
        TODOS="${TODOS}:one: 回复评论和私信\n"
        TODOS="${TODOS}:two: 检查薯条投放效果（曝光>500? <100?）"
        if [ "$PHASE" = "building" ] || [ "$PHASE" = "stable" ]; then
            TODOS="${TODOS}\n\n:crystal_ball: *周末要发周日帖*\n"
            TODOS="${TODOS}:pencil2: 明晚设好周日帖的定时发布"
        fi
        ;;
    6)  # Saturday evening → Sunday might be posting day
        if [ "$PHASE" = "building" ] || [ "$PHASE" = "stable" ]; then
            TODOS=":mega: *今晚必须完成 — 明天是公司号周日档*\n\n"
            TODOS="${TODOS}:one: Notion 草稿库 → 复制周日草稿\n"
            TODOS="${TODOS}:two: XHS → 定时发布：*北京 19:30*\n"
            TODOS="${TODOS}:three: 勾选「AI辅助生成」标注\n"
            TODOS="${TODOS}:four: Notion 发布记录新建一行"
        else
            TODOS=":palm_tree: 修复期周末无公司号发帖\n"
            TODOS="${TODOS}:speech_balloon: 回复评论和私信"
        fi
        ;;
    7)  # Sunday evening → Monday tasks preview
        TODOS=":speech_balloon: *今晚*\n"
        TODOS="${TODOS}:one: 回复评论和私信\n\n"
        TODOS="${TODOS}:crystal_ball: *明天周一*\n"
        TODOS="${TODOS}:clipboard: 查看竞品周报 + 填本周背景 + 批准草稿"
        ;;
esac

# ---------------------------------------------------------------------------
# Build Slack message
# ---------------------------------------------------------------------------
STATUS=":pushpin: ${PHASE_CN} Week ${PHASE_WEEK:-?} · 本月公司号已发 ${COMPANY_COUNT:-0} 篇"

read -r -d '' PAYLOAD << ENDJSON
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "XHS \u8fd0\u8425 \u00b7 ${TODAY} ${TODAY_CN}\u665a"}
    },
    {
      "type": "context",
      "elements": [{"type": "mrkdwn", "text": "${STATUS}"}]
    },
    {"type": "divider"},
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "${URGENT}${TODOS}"}
    }
  ]
}
ENDJSON

log "Sending evening Slack (dow=${DOW}, phase=${PHASE})"
send_slack "$PAYLOAD"

# ---------------------------------------------------------------------------
# Update Notion daily TODO page
# ---------------------------------------------------------------------------
PYTHON="$PROJECT_DIR/.venv/bin/python3"
if [ -x "$PYTHON" ]; then
    "$PYTHON" "$PROJECT_DIR/automation/notion_daily_todo.py" >> "$LOG_FILE" 2>&1
    log "Notion daily TODO updated"
else
    log "Python venv not found at $PYTHON — skipping Notion TODO update"
fi
