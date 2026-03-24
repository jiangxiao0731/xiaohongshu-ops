# Task Plan: XHS Weekly Operations Automation v5.1

## Goal
Fully automate XHS (Xiaohongshu) content operations for Shaw's company + personal accounts: competitor research, content generation, approval workflow, performance analysis, and TD video processing with AI music — requiring only 3 manual actions per week.

## Current Phase
Phase 6 (Operational — awaiting 48h post data)

## Phases

### Phase 1: Fix Broken Scripts
- [x] Task 1: Fix `notion_daily_todo.py` — replaced `data_sources` API with `databases.query()`
- [x] Task 2: Fix `check_approved.py` — use fixed DB IDs from `notion-ids.json`
- **Status:** complete

### Phase 2: Enhance Existing Scripts
- [x] Task 3: Enhance `gen_content.py` — split company/personal prompts
- [x] Task 4: Enhance `notify.sh` — add 4 new notification triggers, update Sunday msg
- [x] Task 5: Fix + Enhance `analyze_performance.py` — fixed DB IDs + summary JSON output
- **Status:** complete

### Phase 3: New Scripts & Data Sources
- [x] Task 6: Rewrite `weekly_brief.py` — read Notion competitor observations instead of CSVs
- [x] Task 7: Create `weekly_planner.py` — brief + analysis -> Notion drafts
- **Status:** complete

### Phase 4: Scheduling & Cleanup
- [x] Task 8: Create launchd plists + cleanup scrape plists
- [x] Task 9: Update WORKFLOW.md to v5.1
- **Status:** complete

### Phase 5: TD Video Auto-Music Pipeline
- [x] Task 10: Create `add_music.py` — scene detection, Claude Vision, Suno API, ffmpeg merge, XHS copy generation, Notion sync
- [x] Task 11: Create launchd WatchPaths daemon (`com.xhs.td-music.plist`)
- **Status:** complete

### Phase 6: Operational — Week 1 Warmup
- [ ] Wait for 48h post data (due 2026-03-23 afternoon)
- [ ] Decision based on view count: >300 continue / 100-300 review content / <100 silent recovery
- [ ] Publish warmup posts (personal account) — NOT YET DONE
- [ ] Publish company account first post — NOT YET DONE
- [ ] Start shudiao (薯条) ads — NOT YET DONE
- **Status:** in_progress
- **Gate:** Notion daily todo checkboxes must be checked before advancing steps

### Phase 7: Week 2+ Execution
- [ ] Enter regular weekly cycle per WORKFLOW.md
- [ ] Monitor phase transition criteria (>=50 organic likes/saves in 72h OR jiguang CTR >=3%)
- **Status:** pending

## Key Questions
1. Is personal account suppressed? — Waiting for 48h data (posted 2026-03-21)
2. Does company account also need warmup? — Yes, both accounts should be evaluated
3. When to start shudiao ads? — After warmup posts establish baseline

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| No scraping — manual competitor observation | XHS warning received for scraping |
| Suno API for music generation | AI-generated ambient tracks matching video mood |
| Scene detection threshold 0.03 | Default 0.08 missed too many transitions |
| Unified drafts DB for personal posts | Simpler than separate DB, use `账号=个人号` tag |
| launchd WatchPaths over polling | More efficient, native macOS, instant trigger |
| Plan gated by Notion todo checkboxes | Shaw wants control — no auto-advancing unfinished steps |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Python 3.9 `Path \| None` TypeError | 1 | Added `from __future__ import annotations` |
| Homebrew not found for ffmpeg | 1 | Downloaded static binaries to ~/bin/ |
| Cloudflare 403 on Suno API | 1 | Added User-Agent and Accept headers |
| Suno API 400 missing callBackUrl | 1 | Added `callBackUrl: httpbin.org/post` |
| Audio download 403 | 1 | Switched to curl subprocess |
| Claude Vision 5MB limit | 1 | JPEG + scale to max 1280px + quality 5 |
| Scene detection 0 results | 1 | Lowered threshold from 0.08 to 0.03 |
| Notion 404 missing integration access | 1 | Used Notion MCP for initial setup |
| Notion property name mismatch | 1 | Fetched schema — was "Name" not "名称" |

## Notes
- WORKFLOW-STATE.md is the runtime state file (auto-updated by scripts)
- This task_plan.md tracks the broader project plan and operational phases
- Phase 6+ are operational, not code tasks — progress depends on real-world actions
- All code implementation (Tasks 1-11) is complete and tested
