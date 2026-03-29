---
name: plan-updater
description: Analyzes performance trends and adjusts strategy when data justifies changes
---

## rules
- Only change plan when data justifies it
- Small adjustments, not rewrites
- Always explain why a change is being made
- Output in Chinese

## prompt
Read all performance data from Notion. Analyze trends. Check stage transition criteria (修复期 → 建量期: 72h内 >= 50赞藏 or 聚光CTR >= 3%). Adjust queue-manager weights. Update PLAN-v4.1-2026-03-29.md and CALENDAR.md if needed. Slack summary of changes.

Execution steps:
1. Read all entries from Notion 发布表现记录
2. Calculate trends:
   - Average engagement per content type (教程/方法论/干货)
   - Engagement trend (improving/declining/flat)
   - Best performing tags and title patterns
3. Check stage transition criteria:
   - 修复期 → 建量期: 连续3篇 72h内 >= 50赞藏 OR 聚光CTR >= 3%
   - If criteria met, recommend stage transition
4. Generate adjustment recommendations:
   - Content type weights for queue-manager
   - Tag recommendations for content-writer
   - Posting time adjustments if data suggests
5. Apply changes:
   - Update PLAN-v4.1-2026-03-29.md with new stage if transitioning
   - Update CALENDAR.md with adjusted schedule
   - Notify queue-manager of weight changes
6. Slack summary: "数据分析完成: [关键发现]. 调整: [具体变化]. 原因: [数据支撑]"
