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
After any path migration, run comprehensive grep across ALL file types (py, sh, plist, md) to catch every reference.

### Resolution
- **Resolved**: 2026-03-24
- **Notes**: Fixed all references, verified with grep

### Metadata
- Source: error
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
Must use curl Slack webhook (bot identity) for notifications. Remote triggers can't curl external webhooks (proxy blocks). Workaround: Slack MCP for reading, curl webhook from local launchd for sending.

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
Trigger created TWO pages for same idea: one with content, one blank. Must assemble complete content first, create ONE page in single API call.

### Metadata
- Source: user_feedback
- Tags: notion, duplicate-pages, atomic-operations

---

## [LRN-20260324-004] correction

**Logged**: 2026-03-24T06:20:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/content-writer.md

### Summary
All Notion drafts must follow exact same template format

### Details
Standard template in content-writer.md: callout header / 发布信息 / 标题(复制) / 正文(复制) / 封面建议 / 标签 / Checklist / 合规检查

### Metadata
- Source: user_feedback
- Tags: notion, template-consistency

---

## [LRN-20260324-005] correction

**Logged**: 2026-03-24T06:25:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/supervisor.md

### Summary
Every action must be reported to Slack in real-time, not batched

### Metadata
- Source: user_feedback
- Tags: slack, real-time-reporting

---

## [LRN-20260324-006] correction

**Logged**: 2026-03-24T06:30:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/supervisor.md

### Summary
Feedback routes to specific agent rules, not global CLAUDE.md

### Metadata
- Source: user_feedback
- Tags: feedback-routing, agent-rules

---

## [LRN-20260324-007] best_practice

**Logged**: 2026-03-24T06:35:00Z
**Priority**: high
**Status**: promoted
**Promoted**: multiple agent files

### Summary
Notion draft database must have all properties filled -- never leave blanks

### Metadata
- Source: user_feedback
- Tags: notion, data-completeness

---

## [LRN-20260324-008] knowledge_gap

**Logged**: 2026-03-24T06:40:00Z
**Priority**: medium
**Status**: resolved

### Summary
Personal account was NOT dormant 6 months -- plan assumption was wrong. Always verify assumptions against actual data.

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
Plan files: date-named (PLAN-vX.Y-YYYY-MM-DD.md), only one authoritative file, expired plans auto-deleted.

### Metadata
- Source: user_feedback
- Tags: file-naming, housekeeping

---

## [LRN-20260324-010] correction

**Logged**: 2026-03-24T07:10:00Z
**Priority**: medium
**Status**: resolved

### Summary
CALENDAR.md had wrong day-of-week: 3/26 is Thursday not Wednesday. Always verify with `date` command.

### Metadata
- Source: error
- Tags: calendar, date-verification

---

## [LRN-20260324-011] correction

**Logged**: 2026-03-24T07:20:00Z
**Priority**: medium
**Status**: resolved

### Summary
GitHub secret scanning blocks pushes containing Slack webhook URLs. Never hardcode in committed files.

### Metadata
- Source: error
- Tags: github, secrets

---

## [LRN-20260324-012] correction

**Logged**: 2026-03-24T07:30:00Z
**Priority**: medium
**Status**: promoted
**Promoted**: .claude/agents/content-writer.md

### Summary
Notion 正文里的 em-dash (—) 被渲染成列表项。Use blank lines for paragraph separation, never — or - as standalone separators.

### Metadata
- Source: error
- Tags: notion, formatting

---

## [LRN-20260324-013] correction

**Logged**: 2026-03-24T08:00:00Z
**Priority**: high
**Status**: promoted
**Promoted**: .claude/agents/content-writer.md

### Summary
正文不超过1000字，绝对上限。精炼 > 全面。

### Details
Shaw反馈AI生成的3.0文章太长。小红书用户注意力短，长文完读率低。1000字以内能讲清楚的不要写到1200。

### Suggested Action
content-writer rules已添加硬性字数限制。以后所有生成的文章都不超过1000字。

### Metadata
- Source: user_feedback
- Tags: word-count, content-quality, xhs-optimization

---
