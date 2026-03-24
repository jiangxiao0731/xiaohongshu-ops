---
name: idea-scanner
description: Scans Apple Notes for new content ideas and routes them into the pipeline
---

## rules
- Don't modify or delete notes, only read
- Always Slack notify when finding new ideas
- Never duplicate an idea that's already in Notion
- Output in Chinese

## prompt
Read Apple Notes "No Turn on Red - 啥都做工作室" via osascript. Compare with last scan (stored in this file's ## state section). New ideas → trigger content-writer to write full draft → push to Notion drafts (状态=待审批) → Slack notify. Store last scan timestamp in ## state section.

Execution steps:
1. Use osascript to read notes from the "No Turn on Red - 啥都做工作室" folder
2. Compare note titles and modification dates against ## state section below
3. For each new or modified note:
   a. Extract the idea content
   b. Check Notion drafts to avoid duplicates
   c. Trigger content-writer agent to expand into full draft
   d. Push completed draft to Notion with 状态=待审批
   e. Slack notify: "发现新想法: [标题]，已生成草稿推入Notion"
4. Update ## state section with current scan timestamp and processed note IDs

## state
last_scan: null
processed_notes: []
