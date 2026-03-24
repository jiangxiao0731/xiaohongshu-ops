# Learnings Log

## [LRN-20260324-001] correction

**Logged**: 2026-03-24T06:00:00Z
**Priority**: critical
**Status**: resolved
**Area**: infra

### Summary
Project path migration breaks ALL automation if references aren't updated everywhere

### Details
Project moved from ~/xiaohongshu-ops to ~/claude/xiaohongshu-ops. 12 launchd plists, 10 Python scripts, 5 shell scripts, and WORKFLOW.md all had old paths. System silently failed for a week with no notifications reaching Shaw.

### Suggested Action
After any path migration, run comprehensive grep across ALL file types (py, sh, plist, md) to catch every reference. Never assume "I fixed the main ones."

### Resolution
- **Resolved**: 2026-03-24
- **Notes**: Fixed all references, verified with grep

### Metadata
- Source: error
- Related Files: all automation/*.py, automation/*.sh, ~/Library/LaunchAgents/com.xhs.*.plist
- Tags: path-migration, silent-failure, launchd

---

## [LRN-20260324-002] correction

**Logged**: 2026-03-24T06:10:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/supervisor.md

### Summary
Slack MCP sends as user's own identity -- no push notification received

### Details
Slack MCP connector authenticates as Shaw. Messages sent via Slack MCP appear as Shaw's own messages, so Shaw gets no notification. Must use curl Slack webhook (bot identity) for notifications. But remote triggers can't curl external webhooks (proxy blocks it). Workaround: use Slack MCP for reading messages, use curl webhook from local launchd for sending.

### Suggested Action
All notification code: prefer curl webhook (bot). Fallback to Slack MCP if curl fails. Document this in supervisor rules.

### Metadata
- Source: user_feedback
- Tags: slack, notifications, mcp-limitations

---

## [LRN-20260324-003] correction

**Logged**: 2026-03-24T06:15:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/content-writer.md, daily-briefing.md

### Summary
Notion page creation must be atomic -- never create empty pages

### Details
When processing Slack content, the trigger created TWO Notion pages for the same idea: one with content, one blank. This happened because the agent called create-pages before content was ready, then updated separately.

### Suggested Action
Always assemble complete content locally first, then create ONE page with all content + properties in a single API call. Validate title/body/properties non-empty before creation.

### Metadata
- Source: user_feedback
- Related Files: .claude/agents/content-writer.md, .claude/agents/daily-briefing.md
- Tags: notion, duplicate-pages, atomic-operations

---

## [LRN-20260324-004] correction

**Logged**: 2026-03-24T06:20:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/content-writer.md

### Summary
All Notion drafts must follow the exact same template format

### Details
Trigger-generated draft had different structure (## 发布标题 / ## 正文 / ## 标签) than existing drafts (callout header / ## 发布信息 / ## 标题（复制）/ ## 正文（复制）/ ## 封面建议 / ## 标签 / ## 发布后 Checklist / callout 合规检查). Shaw expects consistent format across all drafts.

### Suggested Action
Standard template is now in content-writer.md ## Notion 草稿标准格式. Every generated draft must match.

### Metadata
- Source: user_feedback
- Related Files: .claude/agents/content-writer.md
- Tags: notion, template-consistency, formatting

---

## [LRN-20260324-005] correction

**Logged**: 2026-03-24T06:25:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/supervisor.md

### Summary
Every action must be reported to Slack in real-time, not batched

### Details
Shaw wants to see what the system is doing AS it happens. "读到了什么、怎么分类的、正在做什么、做完了什么、结果是什么" -- all must be communicated via Slack immediately, not summarized at the end.

### Suggested Action
Each agent step should send a Slack update. Not just the final result.

### Metadata
- Source: user_feedback
- Tags: slack, real-time-reporting, transparency

---

## [LRN-20260324-006] correction

**Logged**: 2026-03-24T06:30:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/supervisor.md

### Summary
Feedback routes to specific agent rules, not global CLAUDE.md

### Details
Shaw said: "每次的反馈都精准对应到相关的subagent，不要全部写进全局占带宽". Example: "文字要有活人感" goes to content-writer.md rules, not global CLAUDE.md.

### Suggested Action
Supervisor must classify feedback and route to correct agent .md file. Only truly universal rules go to global.

### Metadata
- Source: user_feedback
- Tags: feedback-routing, agent-rules

---

## [LRN-20260324-007] best_practice

**Logged**: 2026-03-24T06:35:00Z
**Priority**: high
**Status**: promoted
**Promoted**: CLAUDE.md

### Summary
Notion draft database must have all properties filled -- never leave blanks

### Details
22 out of 25 drafts were missing 状态 property. Multiple drafts missing 账号, 阶段. Shaw expects every property filled on every draft.

### Suggested Action
Added rules to queue-manager, content-writer, supervisor, daily-briefing: check for empty properties and fill them.

### Metadata
- Source: user_feedback
- Tags: notion, data-completeness

---

## [LRN-20260324-008] knowledge_gap

**Logged**: 2026-03-24T06:40:00Z
**Priority**: medium
**Status**: resolved

### Summary
Personal account was NOT dormant for 6 months -- plan assumption was wrong

### Details
PLAN-V2 assumed personal account was dormant 6 months, requiring warmup. Actual data: posts on 2/23 (227 views), 3/4 (324 views), 3/5 (69 views). Account was active. Warmup was unnecessary.

### Suggested Action
Always verify assumptions against actual data before building plans on them. Updated PLAN-v3.0.

### Metadata
- Source: user_feedback
- Tags: data-verification, wrong-assumptions

---

## [LRN-20260324-009] best_practice

**Logged**: 2026-03-24T07:00:00Z
**Priority**: medium
**Status**: promoted
**Promoted**: memory/feedback_plan_cleanup.md

### Summary
Plan files should be date-named, expired plans auto-deleted

### Details
Shaw doesn't want to be reminded about file maintenance. Plan files use format PLAN-vX.Y-YYYY-MM-DD.md. Old plans deleted automatically. Only one authoritative plan file exists at any time.

### Suggested Action
On plan update: create new versioned file, delete old one, update all references.

### Metadata
- Source: user_feedback
- Tags: file-naming, housekeeping

---

## [LRN-20260324-010] correction

**Logged**: 2026-03-24T07:10:00Z
**Priority**: medium
**Status**: resolved

### Summary
CALENDAR.md had wrong day-of-week: 3/26 is Thursday not Wednesday

### Details
Calendar said "周三 3/26" but 3/26 is actually Thursday. 3/25 is Wednesday. The remote trigger caught this error during its first run.

### Suggested Action
Always verify day-of-week with `date` command before writing dates. Don't assume.

### Metadata
- Source: error
- Tags: calendar, date-verification

---

## [LRN-20260324-011] correction

**Logged**: 2026-03-24T07:20:00Z
**Priority**: medium
**Status**: resolved

### Summary
GitHub secret scanning blocks pushes containing Slack webhook URLs

### Details
Attempted to commit supervisor.md with Slack webhook URL hardcoded. GitHub rejected the push with "push declined due to repository rule violations". Webhook URLs are detected as secrets.

### Suggested Action
Never hardcode webhook URLs in committed files. Reference .env or describe as "read from .env".

### Metadata
- Source: error
- Tags: github, secrets, webhook

---

## [LRN-20260324-012] correction

**Logged**: 2026-03-24T07:30:00Z
**Priority**: medium
**Status**: resolved

### Summary
Notion正文里的 em-dash (—) 被渲染成列表项

### Details
Content-writer used — (em-dash) as section separator in post body. Notion interpreted single `-` at line start as a bullet list item, creating empty "List" blocks.

### Suggested Action
Use blank lines for paragraph separation in Notion content, never use — or - as standalone separators.

### Metadata
- Source: error
- Related Files: .claude/agents/content-writer.md
- Tags: notion, formatting, em-dash

---
