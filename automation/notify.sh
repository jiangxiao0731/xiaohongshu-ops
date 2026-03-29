#!/bin/bash
# notify.sh — Reads WORKFLOW-STATE.md and sends Slack + macOS notifications.
# Designed to run via launchd.

PROJECT_DIR="$HOME/claude/xiaohongshu-ops"
STATE_FILE="$PROJECT_DIR/WORKFLOW-STATE.md"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/notify.log"
ENV_FILE="$PROJECT_DIR/.env"
PENDING_FILE="$HOME/Library/Mobile Documents/com~apple~CloudDocs/xhs-pending.md"

mkdir -p "$LOG_DIR"

# Load env vars (SLACK_WEBHOOK_URL lives here, not in ~/.zshrc which launchd can't read)
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# ---------------------------------------------------------------------------
# Slack helper
# ---------------------------------------------------------------------------
send_slack() {
    local message="$1"
    local title="$2"
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        log "SLACK_WEBHOOK_URL not set — skipping Slack"
        return
    fi
    local payload
    payload=$(printf '{"text":"*%s*\n%s"}' "$title" "$message")
    curl -s -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" >> "$LOG_FILE" 2>&1
}

# ---------------------------------------------------------------------------
# Combined notification helper (Slack + macOS)
# ---------------------------------------------------------------------------
send_notification() {
    local message="$1"
    local title="$2"
    send_slack "$message" "$title"
    osascript -e "display notification \"${message}\" with title \"${title}\" sound name \"Ping\"" 2>/dev/null || true
    log "SENT: title='${title}' message='${message}'"
}

# ---------------------------------------------------------------------------
# Read WORKFLOW-STATE.md fields
# ---------------------------------------------------------------------------
read_state_field() {
    local field="$1"
    if [ -f "$STATE_FILE" ]; then
        grep "^${field}:" "$STATE_FILE" | sed "s/^${field}:[[:space:]]*//" | sed 's/  #.*//' | xargs
    else
        echo ""
    fi
}

PHASE="$(read_state_field "phase")"
WORKFLOW_STEP="$(read_state_field "workflow_step")"
LAST_DATA_ENTRY_DATE="$(read_state_field "last_data_entry_date")"
LAST_PUBLISH_DATE="$(read_state_field "last_publish_date")"

DOW="$(date '+%u')"  # 1=Mon … 7=Sun

NOTIFICATION_SENT=0

# ---------------------------------------------------------------------------
# Day-of-week + phase rules
# ---------------------------------------------------------------------------
if [ "$DOW" = "1" ] && [ "$WORKFLOW_STEP" = "brief_ready" ]; then
    send_notification \
        "本周简报就绪，打开Notion审批内容方向" \
        "XHS运营 — 周一任务"
    NOTIFICATION_SENT=1
fi

if [ "$DOW" = "1" ] && [ "$WORKFLOW_STEP" = "content_ready" ]; then
    send_notification \
        "本周草稿已生成，查看Notion草稿库" \
        "XHS运营 — 草稿就绪"
    NOTIFICATION_SENT=1
fi

if [ "$DOW" = "3" ] && [ "$WORKFLOW_STEP" = "content_ready" ]; then
    send_notification \
        "今天北京时间7:30PM发帖（高峰前30分钟），Notion草稿库复制文案，记得勾选AI标注" \
        "XHS运营 — 周三发帖"
    NOTIFICATION_SENT=1
fi

if [ "$DOW" = "7" ]; then
    send_notification \
        "浏览竞品时间 -- 打开小红书刷15分钟同赛道内容，记录到Notion竞品观察表" \
        "XHS运营 -- 周日竞品观察"
    NOTIFICATION_SENT=1
fi

# Tuesday: posting prep reminder
if [ "$DOW" = "2" ]; then
    send_notification \
        "明天周三发帖日 -- 今晚去Notion复制文案，小红书创作者中心设定时发布（北京19:00）" \
        "XHS运营 -- 明天发帖准备"
    NOTIFICATION_SENT=1
fi

# Personal account gap check (any day): warn if last personal post > 7 days ago
LAST_PERSONAL=$(grep "^personal_post_count_this_month:" "$STATE_FILE" 2>/dev/null | head -1 | awk '{print $2}')
if [ "$LAST_PERSONAL" = "0" ]; then
    send_notification \
        "警告: 个人号本月0发帖，断更超7天会降权！今天有TD/AI作品就发" \
        "XHS运营 -- 个人号断更风险"
    NOTIFICATION_SENT=1
fi

# Saturday: data entry reminder (building/stable phases)
if [ "$DOW" = "6" ] && { [ "$PHASE" = "building" ] || [ "$PHASE" = "stable" ]; }; then
    send_notification \
        "周末检查 -- 本周帖子数据录入了吗？去Notion发布表现记录填写赞/藏/评/私信" \
        "XHS运营 -- 数据检查"
    NOTIFICATION_SENT=1
fi

# Monday: approval reminder (plan_ready/content_ready/brief_ready phases)
if [ "$DOW" = "1" ] && { [ "$WORKFLOW_STEP" = "plan_ready" ] || [ "$WORKFLOW_STEP" = "content_ready" ] || [ "$WORKFLOW_STEP" = "brief_ready" ]; }; then
    send_notification \
        "去Notion审批本周草稿 -- 待审批改为已批准" \
        "XHS运营 -- 周一审批"
    NOTIFICATION_SENT=1
fi

# ---------------------------------------------------------------------------
# Priority 3: awaiting_data — check if last_publish_date was >72h ago
# ---------------------------------------------------------------------------
if [ "$WORKFLOW_STEP" = "awaiting_data" ]; then
    NOTIFY_DATA=0
    if [ -z "$LAST_PUBLISH_DATE" ]; then
        # No publish date recorded — prompt anyway
        NOTIFY_DATA=1
    else
        # Parse last_publish_date as seconds since epoch
        # Expected format: YYYY-MM-DD
        PUBLISH_EPOCH="$(date -j -f '%Y-%m-%d' "$LAST_PUBLISH_DATE" '+%s' 2>/dev/null || echo 0)"
        NOW_EPOCH="$(date +%s)"
        if [ "$PUBLISH_EPOCH" -gt 0 ]; then
            DIFF_HOURS=$(( (NOW_EPOCH - PUBLISH_EPOCH) / 3600 ))
            if [ "$DIFF_HOURS" -ge 72 ]; then
                NOTIFY_DATA=1
            fi
        fi
    fi

    if [ "$NOTIFY_DATA" -eq 1 ]; then
        send_notification \
            "该录入发帖数据了，打开Notion发布表现记录" \
            "XHS运营 — 数据录入"
        NOTIFICATION_SENT=1
    fi
fi

# Pending todos live in Apple Notes "XHS待完成" — managed manually by user on iPhone

# ---------------------------------------------------------------------------
# No notification needed
# ---------------------------------------------------------------------------
if [ "$NOTIFICATION_SENT" -eq 0 ]; then
    log "no notification needed (phase=${PHASE}, dow=${DOW})"
fi
