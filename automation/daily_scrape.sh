#!/bin/bash
# daily_scrape.sh — Runs daily XHS MediaCrawler scrape with keyword rotation.
# Idempotent: exits 0 if today's scrape already completed successfully.
# Uses: https://github.com/NanmiCoder/MediaCrawler

set -e

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR="$HOME/claude/xiaohongshu-ops"
MEDIACRAWLER_DIR="$PROJECT_DIR/MediaCrawler"
DATA_DIR="$PROJECT_DIR/data"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/scrape.log"
STATE_FILE="$PROJECT_DIR/WORKFLOW-STATE.md"

mkdir -p "$DATA_DIR" "$LOG_DIR"

# Ensure uv is on PATH
export PATH="$HOME/.local/bin:$PATH"

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ---------------------------------------------------------------------------
# Date / keyword selection
# ---------------------------------------------------------------------------
TODAY="$(date '+%Y-%m-%d')"
DOW="$(date '+%u')"  # 1=Mon … 7=Sun

case "$DOW" in
    1) KEYWORD="数媒作品集" ;;
    2) KEYWORD="交互设计留学" ;;
    3) KEYWORD="作品集辅导" ;;
    4) KEYWORD="艺术留学作品集" ;;
    5) KEYWORD="数字媒体艺术" ;;
    6) KEYWORD="交互设计作品集" ;;
    7) KEYWORD="艺术生留学" ;;
    *) KEYWORD="数媒作品集" ;;
esac

SAFE_KEYWORD="${KEYWORD// /_}"
DEST_CSV="$DATA_DIR/${TODAY}-${SAFE_KEYWORD}.csv"

# ---------------------------------------------------------------------------
# Idempotency check
# ---------------------------------------------------------------------------
if [ -f "$DEST_CSV" ]; then
    log "already_ran — $DEST_CSV exists, exiting."
    exit 0
fi

log "Starting scrape: keyword=${KEYWORD}, date=${TODAY}"

# ---------------------------------------------------------------------------
# State file helper
# ---------------------------------------------------------------------------
update_state_field() {
    local field="$1"
    local value="$2"
    if [ -f "$STATE_FILE" ]; then
        if grep -q "^${field}:" "$STATE_FILE"; then
            perl -i -pe "s|^${field}:.*|${field}: ${value}|" "$STATE_FILE"
        else
            echo "${field}: ${value}" >> "$STATE_FILE"
        fi
    else
        echo "${field}: ${value}" > "$STATE_FILE"
    fi
}

# ---------------------------------------------------------------------------
# Run MediaCrawler (NanmiCoder/MediaCrawler)
# ---------------------------------------------------------------------------
log "Running MediaCrawler with uv..."

SCRAPE_ERROR=0
(
    set -e
    cd "$MEDIACRAWLER_DIR"
    uv run python main.py \
        --platform xhs \
        --type search \
        --lt cookie \
        --keywords "$KEYWORD" \
        --save_data_option csv \
        --headless true \
        --get_comment false
) >> "$LOG_FILE" 2>&1 || SCRAPE_ERROR=1

if [ "$SCRAPE_ERROR" -eq 1 ]; then
    log "ERROR: MediaCrawler exited with non-zero status"
    update_state_field "last_scrape_date" "$TODAY"
    update_state_field "last_scrape_keyword" "$KEYWORD"
    update_state_field "last_scrape_status" "error"

    # Send failure notification
    ENV_FILE="$PROJECT_DIR/.env"
    if [ -f "$ENV_FILE" ]; then
        # shellcheck disable=SC1090
        source "$ENV_FILE"
    fi
    osascript -e "display notification \"每日抓取失败（${KEYWORD}），检查Cookie或MediaCrawler\" with title \"XHS运营 - 抓取错误\" sound name \"Basso\"" 2>/dev/null || true
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"*XHS运营 - 抓取错误*\n每日抓取失败（${KEYWORD}），检查Cookie或MediaCrawler\"}" \
            "$SLACK_WEBHOOK_URL" >> "$LOG_FILE" 2>&1 || true
    fi

    exit 1
fi

# ---------------------------------------------------------------------------
# Find and copy the output CSV
# ---------------------------------------------------------------------------
# MediaCrawler writes to MediaCrawler/data/xhs/csv/
CRAWL_CSV="$MEDIACRAWLER_DIR/data/xhs/csv/search_contents_${TODAY}.csv"

if [ ! -f "$CRAWL_CSV" ]; then
    # Fallback: find the most recently modified search_contents CSV
    CRAWL_CSV="$(ls -t "$MEDIACRAWLER_DIR/data/xhs/csv/search_contents_"*.csv 2>/dev/null | head -1 || true)"
fi

if [ -z "$CRAWL_CSV" ] || [ ! -f "$CRAWL_CSV" ]; then
    log "ERROR: Could not locate output CSV in $MEDIACRAWLER_DIR/data/xhs/csv/"
    update_state_field "last_scrape_date" "$TODAY"
    update_state_field "last_scrape_keyword" "$KEYWORD"
    update_state_field "last_scrape_status" "error"
    exit 1
fi

# Check that the fallback CSV date matches today (reject stale data)
CSV_BASENAME="$(basename "$CRAWL_CSV")"
CSV_DATE="$(echo "$CSV_BASENAME" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)"
if [ -n "$CSV_DATE" ] && [ "$CSV_DATE" != "$TODAY" ]; then
    log "ERROR: Found CSV is stale (date=${CSV_DATE}, expected=${TODAY}) — refusing to use old data"
    update_state_field "last_scrape_date" "$TODAY"
    update_state_field "last_scrape_keyword" "$KEYWORD"
    update_state_field "last_scrape_status" "error"
    exit 1
fi

cp "$CRAWL_CSV" "$DEST_CSV"
log "Copied $CRAWL_CSV -> $DEST_CSV"

# ---------------------------------------------------------------------------
# Update WORKFLOW-STATE.md
# ---------------------------------------------------------------------------
update_state_field "last_scrape_date" "$TODAY"
update_state_field "last_scrape_keyword" "$KEYWORD"
update_state_field "last_scrape_status" "ok"

log "Scrape complete: keyword=${KEYWORD}, output=${DEST_CSV}"
