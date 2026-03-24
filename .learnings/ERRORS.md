# Errors Log

## [ERR-20260324-001] launchd_path_failure

**Logged**: 2026-03-24T05:00:00Z
**Priority**: critical
**Status**: resolved

### Summary
All 12 launchd jobs failing with exit code 127 (command not found)

### Error
```
launchctl list | grep com.xhs
-  127  com.xhs.notify.wed
-  127  com.xhs.slack.daily
...
```

### Context
- Project moved from ~/xiaohongshu-ops to ~/claude/xiaohongshu-ops
- All plist files still pointed to old path
- Silent failure -- no notifications, no errors visible to user

### Suggested Fix
Update all plist paths, unload/reload. Verify with exit code 0.

### Resolution
- **Resolved**: 2026-03-24
- **Notes**: All 12 plists updated, 10 reloaded (2 scrape plists deleted)

### Metadata
- Reproducible: yes
- Related Files: ~/Library/LaunchAgents/com.xhs.*.plist

---

## [ERR-20260324-002] gen_content_nameerror

**Logged**: 2026-03-24T06:45:00Z
**Priority**: high
**Status**: resolved

### Summary
gen_content.py NameError: SYSTEM_PROMPT undefined in placeholder function

### Error
```
NameError: name 'SYSTEM_PROMPT' is not defined
```

### Context
- Line 163 of gen_content.py referenced `SYSTEM_PROMPT` variable
- Should be `COMPANY_SYSTEM_PROMPT` (account-specific prompts)
- Only affects placeholder generation (no API key scenario)

### Resolution
- **Resolved**: 2026-03-24
- **Notes**: Changed to COMPANY_SYSTEM_PROMPT

### Metadata
- Reproducible: yes
- Related Files: automation/gen_content.py

---

## [ERR-20260324-003] github_secret_scanning

**Logged**: 2026-03-24T06:20:00Z
**Priority**: medium
**Status**: resolved

### Summary
Git push rejected -- Slack webhook URL detected as secret

### Error
```
! [remote rejected] main -> main (push declined due to repository rule violations)
```

### Context
- Committed supervisor.md with hardcoded Slack webhook URL
- GitHub secret scanning blocked the push

### Resolution
- **Resolved**: 2026-03-24
- **Notes**: Reset commit, removed URL from file, changed rule to "read from .env"

### Metadata
- Reproducible: yes
- Related Files: .claude/agents/supervisor.md

---

## [ERR-20260324-004] remote_trigger_curl_blocked

**Logged**: 2026-03-24T06:30:00Z
**Priority**: high
**Status**: resolved

### Summary
Remote trigger can't curl external Slack webhook -- proxy blocks it

### Error
```
403 host_not_allowed
```

### Context
- Remote trigger runs in Anthropic cloud sandbox
- External HTTP requests to hooks.slack.com blocked by proxy
- Trigger prompt instructed to use curl for Slack webhook

### Resolution
- **Resolved**: 2026-03-24
- **Notes**: Trigger falls back to Slack MCP for sending. Local launchd uses curl webhook.

### Metadata
- Reproducible: yes
- Related Files: remote trigger prompts

---
