# XHS (Xiaohongshu) Dual-Account Operations Project

## Project Overview

Shaw runs a portfolio consulting business (作品集辅导) targeting art/design study-abroad students. This repo manages content creation, publishing, analytics, and automation for two XHS accounts.

## Two Accounts

| Account | Name | Role | Content Focus |
|---------|------|------|---------------|
| **Company** | 蕉蕉椒椒（作品集版） | Brand credibility + case studies | Portfolio methodology, tech tutorials, program comparisons |
| **Personal** | 蕉蕉椒椒 | Creator persona + trust building | TD tutorials, AI tool reviews, exhibition content |

**Critical rule:** The two accounts NEVER cross-reference each other in posts. No mutual @mentions, no "check my other account" CTAs. XHS aggressively bans matrix operations (矩阵运营). The personal account does NOT mention portfolio consulting at all -- it's a creative technologist persona.

**Scraping account:** MediaCrawler 登录态使用小号（burner account），NOT the business or personal account. 封号风险太高，绝不能用运营账号爬取。登录态缓存在 `MediaCrawler/browser_data/`。如需重新登录小号：删除 `browser_data/xhs_user_data_dir` 和 `browser_data/cdp_xhs_user_data_dir`，然后 `--lt qrcode` 扫码。

## Current Phase

- **Phase:** 修复期 (Repair) -- Week 1 of 12-week plan
- **State file:** `WORKFLOW-STATE.md` (source of truth for current phase, warmup status, etc.)
- **Full plan:** `PLAN-V2.md` (v2.2, data-driven rewrite based on 120 competitor posts + XHS policy research)

## Plan Review Discipline

`PLAN-V2.md` is the operational backbone. Follow these rules:

1. **Every session start:** Read `PLAN-V2.md` and `WORKFLOW-STATE.md` to understand current state.
2. **Daily review:** At the end of each working day, review what actions were taken (posts published, designs created, data collected, decisions made). If any posts were published or performance data was read, refine `PLAN-V2.md` accordingly -- adjust timelines, update learnings, shift priorities based on real results.
3. **Skip if idle:** If no posts were published and no performance data was read/collected that day, do NOT update the plan. No busywork updates.
4. **Slack notification:** After each plan update, send a Slack message to Shaw summarizing what changed and why. Keep it concise -- bullet points of what was updated, not a full diff.
5. **Plan evolution:** The plan is a living document. Real data always overrides assumptions. If a post performs unexpectedly well or poorly, the plan should reflect that learning immediately.

## Color System (zumi供稿 Design Only)

This palette is specifically for zumi供稿 carousel designs, not a global rule:

| Color | Hex | Usage |
|-------|-----|-------|
| 米色 (Beige) | `#f4f2eb` | Background / card fills |
| 冷绿 (Cool Green) | `#a0cfa8` | Primary accent |
| 暖绿 (Warm Green) | `#a4c699` | Secondary accent |
| 浅绿 (Light Green) | `#d1e1d4` | Subtle backgrounds |
| 红 (Red) | `#FF0043` | Accent ONLY -- salary numbers, admission rates, key emphasis. Never structural. |

Green is the primary identity. Red is strictly 点缀 (decorative accent), never used for backgrounds, dividers, underlines, or section labels.

## Carousel Design Specs

- **Dimensions:** 1080 x 1440 px (3:4 ratio, XHS standard)
- **Font:** Inter + Noto Sans SC (loaded via Google Fonts for Figma capture compatibility)
- **Font stack:** `"Inter", "Noto Sans SC", -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif`
- **Figma file:** `jOnxH8FLGP2lPVBV7Cf8RO`
- **Capture workflow:** HTML files served via local HTTP server (port 7800) → `mcp__figma__generate_figma_design` with `figmadelay=8000` for font loading
- **Design files location:** `designs/zumi/`
  - `capture-*.html` = Figma-ready single-option files (full size, stacked vertically)
  - `*-v2.html` = Multi-option source files (Options D/E/F)

## Notion Structure

**Main page:** `32693fe4326480e386e3fc6a049fff07` (小红书)

**Databases (IDs in `notion-ids.json`):**

| Database | Purpose |
|----------|---------|
| 内容草稿库 | Content drafts with approval workflow |
| 公司号发布表现记录 | Company account post performance tracking |
| 个人号发布表现记录 | Personal account post performance tracking |
| 竞品周报 | Auto-generated weekly competitor reports |
| 花钱决策日志 | Ad spend decisions and ROI tracking |

**Key sub-pages:**
- 运营计划 全周期: `32693fe4326481e39af0f61b15f8f174`

**Notion is the single source of truth.** After any work session that produces new content, changes plans, updates bios, adds design options, or makes any decision -- update the relevant Notion page immediately. This includes:
- New carousel designs or design decisions → update main page or relevant draft
- Plan changes, schedule shifts → update 运营计划 or main page callouts
- New drafts or content edits → update 内容草稿库 entries
- Performance data, ad spend decisions → update respective databases
- Bio changes → update 账号简介建议 section on main page

## Content Quality Rules

- **活人感优先：** All generated copy must sound natural, like a real person talking. No corporate tone, no ad-speak. Write like you're explaining to a friend, not pitching to a customer.
- **准确性：** All factual claims (school programs, admission requirements, salary ranges, deadlines, etc.) must be verified online before writing. Use WebSearch to confirm.
- **不确定就问：** If you're unsure about any information, ask Shaw. Never fabricate or guess facts.
- **不要太绝对：** Avoid absolute statements ("一定", "必须", "绝对", "基本过不了"). Use softer phrasing ("比较", "通常", "一般来说", "可能").

## XHS Compliance Red Lines

Every post must follow these rules (from `PLAN-V2.md` Section 5):

- Max 10 tags per post
- AI-generated content must be labeled (勾选「AI辅助生成」)
- **NEVER** write: time-to-offer promises, GPA+admission claims, "私信我辅导", cross-account promotion, external links/QR codes
- **SAFE:** Pure tech tutorials, program introductions, personal experience narratives, methodology content
- Offer case posts: write about portfolio concepts only, never about tutoring results

## Key Files

| File | Purpose |
|------|---------|
| `PLAN-V2.md` | Full 12-week operation plan (v2.2) |
| `WORKFLOW-STATE.md` | Machine-readable current state (phase, cookie, warmup status) |
| `WORKFLOW.md` | Automation scripts and launchd setup |
| `CALENDAR.md` | Week-by-week publishing calendar |
| `TAGS.md` | Tag strategy per content type |
| `notion-ids.json` | All Notion database IDs |
| `XHS-POLICY-RESEARCH-2026.md` | Platform policy research |

## Integrations

### Slack

- **Webhook:** `SLACK_WEBHOOK_URL` from `.env`
- **Pattern:** `curl -X POST -H 'Content-type: application/json' --data '{"blocks":[...]}' "$SLACK_WEBHOOK_URL"`
- **Reference scripts:** `automation/slack_daily.sh`, `automation/slack_post_reminder.sh`
- **Use for:** Plan update notifications, daily reminders, any alerts to Shaw
- **Format:** Slack Block Kit JSON (`blocks` array with `section`, `header`, `divider` types)

### Notion

- **MCP tools:** All `mcp__claude_ai_Notion__*` tools (search, fetch, create-pages, update-page, etc.)
- **Token:** `NOTION_TOKEN` from `.env`
- **Main page ID:** `32693fe4326480e386e3fc6a049fff07`
- **Database IDs:** stored in `notion-ids.json`
- **Rule:** Notion is always updated in-session, never deferred to later.

## HTTP Server

Design files are served from `designs/zumi/` on port 7800. Before starting a new server, always check `lsof -i :7800`. The server must run from the correct subdirectory, not from `~`.
