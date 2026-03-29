#!/bin/bash
# slack_post_reminder.sh — Send "30 min until posting time" Slack reminder.
# Runs at 07:00 NYC daily via launchd. Only sends on posting days.

PROJECT_DIR="$HOME/claude/xiaohongshu-ops"
STATE_FILE="$PROJECT_DIR/WORKFLOW-STATE.md"
ENV_FILE="$PROJECT_DIR/.env"
LOG_FILE="$PROJECT_DIR/logs/slack_post_reminder.log"

mkdir -p "$PROJECT_DIR/logs"

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

send_slack() {
    local payload="$1"
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        log "SLACK_WEBHOOK_URL not set"
        return
    fi
    curl -s -o /dev/null -w '' \
        -X POST -H 'Content-type: application/json' \
        --data "$payload" "$SLACK_WEBHOOK_URL" >> "$LOG_FILE" 2>&1
    log "Slack sent"
}

read_field() {
    grep "^${1}:" "$STATE_FILE" 2>/dev/null | sed "s/^${1}:[[:space:]]*//" | sed 's/  #.*//' | xargs
}

PHASE="$(read_field "phase")"
DOW="$(date '+%u')"  # 1=Mon … 7=Sun

# ---------------------------------------------------------------------------
# Determine if today is a posting day
# ---------------------------------------------------------------------------
POSTING=0
MSG=""

# Wednesday = always a company posting day
if [ "$DOW" = "3" ]; then
    POSTING=1
    MSG=":alarm_clock: *30分钟后发帖* — 北京 19:00 / 纽约 7:00AM\n\n:office: 公司号「蕉蕉椒椒（作品集版）」\n\n:white_check_mark: Notion 草稿库复制文案\n:white_check_mark: XHS 创作者中心 → 发布 → 定时发布 19:00\n:white_check_mark: 勾选「AI辅助生成」标注\n:white_check_mark: 发布表现记录新建一行"
fi

# Saturday = company posting day (all phases, v4.0)
if [ "$DOW" = "6" ]; then
    POSTING=1
    MSG=":alarm_clock: *30分钟后发帖* — 北京 19:00 / 纽约 7:00AM\n\n:office: 公司号（周六档）\n\n:white_check_mark: Notion 草稿库复制文案\n:white_check_mark: 定时发布 19:00\n:white_check_mark: 勾选「AI辅助生成」标注"
fi

# Sunday = posting day in building/stable phase
if [ "$DOW" = "7" ] && [ "$PHASE" = "building" -o "$PHASE" = "stable" ]; then
    POSTING=1
    MSG=":alarm_clock: *30分钟后发帖* — 北京 19:00 / 纽约 7:00AM\n\n:office: 公司号（周日档）\n\n:white_check_mark: Notion 草稿库复制文案\n:white_check_mark: 定时发布 19:00\n:white_check_mark: 勾选「AI辅助生成」标注"
fi

# Tuesday/Thursday = personal account posting days (optional reminder)
if [ "$DOW" = "2" ] || [ "$DOW" = "4" ]; then
    POSTING=1
    MSG=":alarm_clock: *个人号发帖提醒* — 北京 19:00 / 纽约 7:00AM\n\n:art: 个人号「蕉蕉椒椒」\n有 TD/AI 作品就今天发。没有就跳过，不凑数。\n\n:white_check_mark: 个人号草稿库检查是否有待发内容"
fi

if [ "$POSTING" -eq 0 ]; then
    log "Not a posting day (dow=${DOW}, phase=${PHASE})"
    exit 0
fi

read -r -d '' PAYLOAD << ENDJSON
{
  "blocks": [
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "${MSG}"}
    }
  ]
}
ENDJSON

send_slack "$PAYLOAD"
