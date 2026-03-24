# Findings & Decisions

## Requirements
- 2 XHS accounts: company (作品集辅导老师Shaw) + personal (纯创作者, TD/AI/exhibition)
- 3 manual actions per week: Sunday competitor browsing, Monday draft approval, Tuesday publish setup
- Everything else automated via launchd + Python scripts + Claude API + Notion
- TD videos auto-processed with AI music when dropped in export folder
- Plan progression gated by Notion todo checkbox completion

## Research Findings
- XHS uses per-post "horse racing" algorithm — initial 200 impressions determine distribution
- Content quality (visual output + hook title) matters more than account status
- Personal account TD videos are top-performing content type (avg 2867 interactions)
- 3/4 post (13 likes, had visual output + hook) performed better than 3/5 post (2 likes, just code patches)
- Must wait 48h for natural traffic data before drawing conclusions about suppression

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| ffmpeg scene detection `gte(scene,0.03)` | Detects visual change points for rhythm-aware music prompts |
| Claude Vision for video mood analysis | Sends keyframes + rhythm analysis context for music prompt generation |
| Suno API with callBackUrl | Required field; using httpbin.org/post as dummy callback |
| curl for audio downloads | urllib blocked by Cloudflare; curl with -sL works |
| JPEG frames at max 1280px, q:v 5 | Keeps under Claude Vision's 5MB limit |
| Static ffmpeg binaries in ~/bin/ | Homebrew not available on this machine |
| Notion REST API + MCP hybrid | MCP for initial DB setup; REST API in scripts for runtime |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| XHS scraping warning | Removed all MediaCrawler scraping; manual competitor observation via Notion |
| Python 3.9 compatibility | `from __future__ import annotations` for union type syntax |
| Notion integration access | Must share databases with integration in Notion UI |
| Personal account low views on 3/5 post | Content quality issue (code patches vs visual output), not suppression — wait 48h |

## Resources
- Suno API: POST `/api/v1/generate`, GET `/api/v1/generate/record-info?taskId=`
- Notion IDs: `automation/notion-ids.json`
- Workflow state: `WORKFLOW-STATE.md`
- Workflow docs: `WORKFLOW.md` (v5.1)
- Plan file: `.claude/plans/curried-whistling-matsumoto.md`

## Key File Map
| File | Purpose |
|------|---------|
| `automation/add_music.py` | TD video -> AI music -> merge -> Notion draft |
| `automation/gen_content.py` | Claude API content generation (company/personal prompts) |
| `automation/weekly_planner.py` | Brief + analysis -> Notion drafts (待审批) |
| `automation/weekly_brief.py` | Notion competitor observations -> weekly brief |
| `automation/analyze_performance.py` | Performance data -> latest-summary.json |
| `automation/check_approved.py` | Poll Notion for approved drafts -> generate content |
| `automation/notion_daily_todo.py` | Update Notion daily todo callout |
| `automation/nightly_review.py` | Check todo completion status |
| `automation/notify.sh` | macOS + Slack notifications by day of week |
| `~/Desktop/td/export/` | TD video input folder (watched by launchd) |
| `~/Desktop/td/export/ready/` | Processed video output folder |

---
*Update this file after every 2 view/browser/search operations*
