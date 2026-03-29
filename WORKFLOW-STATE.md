# XHS Workflow State
# This file is auto-updated by automation scripts. Do not edit manually except where noted.

phase: repair
# Values: repair | building | stable
workflow_step: content_ready
# Values: awaiting_data | brief_ready | plan_ready | content_ready
# repair = 修复期 (weeks 1-4)
# building = 建量期 (weeks 5-8) — enter when new post gets ≥50 organic likes/saves in 72h OR 聚光 CTR ≥3% with inquiries
# stable = 稳定期 (week 9+)

cookie_status: ok
# Values: ok | expired | unknown

# Scraping disabled (2026-03-24). Competitor data via manual Notion observation.

last_brief_date: 2026-03-22
last_content_gen_date: 2026-03-28
last_publish_date: 2026-03-24
last_data_entry_date: 2026-03-29
last_analysis_date: 2026-03-28

current_phase: 修复期
# Auto-updated by analyze_performance.py
# Values: 修复期 | 建量期 | 稳定期

current_phase_week: 1
# Manually update this each Monday

company_post_count_this_month: 1
personal_post_count_this_month: 1
# 邪修3.0 (2026-03-24) 72h data: 861眼睛, 152赞, 66藏, 4评论 (薯条加持后)
offer_post_count_this_month: 0

warmup_complete: yes
# Set to "yes" after personal account warmup posts are published
# Only relevant during Week 1 of repair phase

# MANUAL SECTION — update these yourself:
# has_new_td_work: no
# has_new_case: no
# notes:
last_missed_tasks: 数据录入逾期 — 公司号「蕉蕉椒椒（作品集版）」 帖子 2026-03-24 已超72h，去 Notion 发布表现记录填写赞/藏/评/私信数 | 公司号「蕉蕉椒椒（作品集版）」 + 个人号「蕉蕉椒椒」 → 回复评论和私信
last_missed_date: 2026-03-28
