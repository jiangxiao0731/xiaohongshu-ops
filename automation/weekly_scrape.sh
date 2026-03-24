#!/bin/bash
# weekly_scrape.sh — Batch scrape all XHS keywords + top creator profiles.
# Idempotent per keyword: skips if CSV already exists for today.
# Runs weekly (Sunday 22:00 NYC via launchd).

set -e

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR="$HOME/xiaohongshu-ops"
MEDIACRAWLER_DIR="$PROJECT_DIR/MediaCrawler"
DATA_DIR="$PROJECT_DIR/data"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/scrape.log"
STATE_FILE="$PROJECT_DIR/WORKFLOW-STATE.md"
AUTOMATION_DIR="$PROJECT_DIR/automation"

mkdir -p "$DATA_DIR" "$LOG_DIR"

# Ensure uv is on PATH
export PATH="$HOME/.local/bin:$PATH"

# Bypass proxy for localhost (ShadowsocksX-NG Privoxy conflicts with CDP/Playwright)
export no_proxy="localhost,127.0.0.1"
export NO_PROXY="localhost,127.0.0.1"

# Route browser traffic through local SOCKS5 proxy (ShadowsocksX-NG)
export XHS_SOCKS_PROXY="socks5://127.0.0.1:1086"
# HTTP proxy (Privoxy) for httpx API calls
export XHS_HTTP_PROXY="http://127.0.0.1:1087"

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

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
# Load .env for Slack webhook
# ---------------------------------------------------------------------------
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

# ---------------------------------------------------------------------------
# Date and keyword list
# ---------------------------------------------------------------------------
TODAY="$(date '+%Y-%m-%d')"

KEYWORDS=(
    "作品集辅导"
    "作品集机构"
    "留学作品集"
    # "艺术留学作品集"    # ALREADY DONE today (2026-03-19)
    "留学作品集辅导"
    "艺术生留学"
    "交互设计留学"
    "数媒作品集"
    "作品集排版"
    "设计留学"
)

# ---------------------------------------------------------------------------
# Phase 1: Keyword search scrape
# ---------------------------------------------------------------------------
log "=== Weekly scrape starting: ${#KEYWORDS[@]} keywords, date=${TODAY} ==="

SUCCESS_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0
TOTAL_ROWS=0
COMPLETED_KEYWORDS=()

for KW in "${KEYWORDS[@]}"; do
    SAFE_KW="${KW// /_}"
    DEST_CSV="$DATA_DIR/${TODAY}-${SAFE_KW}.csv"

    # Idempotency: skip if already scraped
    if [ -f "$DEST_CSV" ]; then
        log "SKIP: $DEST_CSV already exists"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        COMPLETED_KEYWORDS+=("$KW")
        continue
    fi

    log "Scraping keyword: $KW"
    SCRAPE_ERROR=0
    (
        set -e
        cd "$MEDIACRAWLER_DIR"
        uv run python main.py \
            --platform xhs \
            --type search \
            --lt cookie \
            --keywords "$KW" \
            --save_data_option csv \
            --headless true \
            --get_comment false
    ) >> "$LOG_FILE" 2>&1 || SCRAPE_ERROR=1

    if [ "$SCRAPE_ERROR" -eq 1 ]; then
        log "ERROR: Scrape failed for keyword=$KW"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # Find and copy the output CSV
    CRAWL_CSV="$MEDIACRAWLER_DIR/data/xhs/csv/search_contents_${TODAY}.csv"
    if [ ! -f "$CRAWL_CSV" ]; then
        CRAWL_CSV="$(ls -t "$MEDIACRAWLER_DIR/data/xhs/csv/search_contents_"*.csv 2>/dev/null | head -1 || true)"
    fi

    if [ -z "$CRAWL_CSV" ] || [ ! -f "$CRAWL_CSV" ]; then
        log "ERROR: No output CSV found for keyword=$KW"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    # Verify CSV date matches today
    CSV_BASENAME="$(basename "$CRAWL_CSV")"
    CSV_DATE="$(echo "$CSV_BASENAME" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)"
    if [ -n "$CSV_DATE" ] && [ "$CSV_DATE" != "$TODAY" ]; then
        log "ERROR: Stale CSV for keyword=$KW (date=${CSV_DATE}, expected=${TODAY})"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    cp "$CRAWL_CSV" "$DEST_CSV"
    ROW_COUNT=$(wc -l < "$DEST_CSV" | tr -d ' ')
    ROW_COUNT=$((ROW_COUNT - 1))  # subtract header
    TOTAL_ROWS=$((TOTAL_ROWS + ROW_COUNT))
    log "OK: $KW -> $DEST_CSV ($ROW_COUNT rows)"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    COMPLETED_KEYWORDS+=("$KW")

    # Sleep between keywords to avoid rate limiting
    log "Sleeping 60s before next keyword..."
    sleep 60
done

log "Phase 1 complete: ${SUCCESS_COUNT} OK, ${SKIP_COUNT} skipped, ${FAIL_COUNT} failed, ${TOTAL_ROWS} total rows"

# ---------------------------------------------------------------------------
# Phase 2: Creator scrape
# ---------------------------------------------------------------------------
log "=== Phase 2: Extracting top creators ==="

CREATOR_CSV="$DATA_DIR/${TODAY}-creators.csv"

if [ -f "$CREATOR_CSV" ]; then
    log "SKIP: Creator CSV already exists"
else
    # Extract top 20 creator IDs from today's data
    TOP_CREATOR_IDS=$(python3 "$AUTOMATION_DIR/extract_top_creators.py" "$DATA_DIR" "$TODAY" 2>>"$LOG_FILE")

    if [ -z "$TOP_CREATOR_IDS" ]; then
        log "WARNING: No creator IDs extracted, skipping creator scrape"
    else
        CREATOR_COUNT=$(echo "$TOP_CREATOR_IDS" | tr ',' '\n' | wc -l | tr -d ' ')
        log "Scraping $CREATOR_COUNT creator profiles..."

        CREATOR_ERROR=0
        (
            set -e
            cd "$MEDIACRAWLER_DIR"
            uv run python main.py \
                --platform xhs \
                --type creator \
                --lt cookie \
                --creator_id "$TOP_CREATOR_IDS" \
                --save_data_option csv \
                --headless true
        ) >> "$LOG_FILE" 2>&1 || CREATOR_ERROR=1

        if [ "$CREATOR_ERROR" -eq 1 ]; then
            log "ERROR: Creator scrape failed"
        else
            # Find creator CSV output
            CREATOR_CRAWL_CSV="$(ls -t "$MEDIACRAWLER_DIR/data/xhs/csv/creator_"*.csv 2>/dev/null | head -1 || true)"
            if [ -n "$CREATOR_CRAWL_CSV" ] && [ -f "$CREATOR_CRAWL_CSV" ]; then
                cp "$CREATOR_CRAWL_CSV" "$CREATOR_CSV"
                log "OK: Creator profiles -> $CREATOR_CSV"
            else
                log "ERROR: No creator CSV output found"
            fi
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Update WORKFLOW-STATE.md
# ---------------------------------------------------------------------------
ALL_KEYWORDS_STR=$(IFS=','; echo "${COMPLETED_KEYWORDS[*]}")
update_state_field "last_scrape_date" "$TODAY"
update_state_field "last_scrape_keywords" "$ALL_KEYWORDS_STR"
if [ "$FAIL_COUNT" -eq 0 ]; then
    update_state_field "last_scrape_status" "ok"
else
    update_state_field "last_scrape_status" "partial (${FAIL_COUNT} failed)"
fi

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
SUMMARY="本周爬取完成: ${SUCCESS_COUNT}/${#KEYWORDS[@]}关键词OK, ${TOTAL_ROWS}条笔记"
if [ -f "$CREATOR_CSV" ]; then
    SUMMARY="$SUMMARY, 竞品账号资料已获取"
fi

osascript -e "display notification \"${SUMMARY}\" with title \"XHS运营 - 周爬取完成\" sound name \"Glass\"" 2>/dev/null || true

if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -s -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"*XHS运营 - 周爬取完成*\n${SUMMARY}\"}" \
        "$SLACK_WEBHOOK_URL" >> "$LOG_FILE" 2>&1 || true
fi

log "=== Weekly scrape finished: ${SUMMARY} ==="
