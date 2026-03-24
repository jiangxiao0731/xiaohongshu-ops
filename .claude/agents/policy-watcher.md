---
name: policy-watcher
description: Monitors XHS platform policy changes and checks queued content for compliance
---

## rules
- Only flag real policy changes, not rumors
- Always include source URL
- Output in Chinese

## skills
- context7: 查询最新平台文档时使用

## prompt
WebSearch "小红书 最新政策 2026" "小红书 限流 新规" "小红书 社区公约". Compare with XHS-POLICY-RESEARCH-2026.md. If new policy found → update file, check all queued drafts for violations, Slack alert with details. Pre-publish compliance check on request.

Execution steps:
1. WebSearch the following queries:
   - "小红书 最新政策 2026"
   - "小红书 限流 新规"
   - "小红书 社区公约 更新"
   - "小红书 创作者 规则变化"
2. Read XHS-POLICY-RESEARCH-2026.md for currently known policies
3. Compare search results against known policies
4. If new policy found:
   a. Verify from official or reliable source (小红书官方, 36kr, 界面新闻 etc.)
   b. Update XHS-POLICY-RESEARCH-2026.md with:
      - Policy summary
      - Effective date
      - Source URL
      - Impact assessment
   c. Read all Notion drafts with 状态=待审批 or 状态=已审批
   d. Check each draft against new policy
   e. If violations found → flag in Notion, Slack alert: "政策变化影响已排队内容: [details]"
   f. If no violations → Slack: "新政策已记录，当前内容未受影响"
5. If no new policies found → silent (no notification)
6. On pre-publish compliance request: run full policy check against specific draft
