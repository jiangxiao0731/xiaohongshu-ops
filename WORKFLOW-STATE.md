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

last_brief_date: 2026-04-26
last_content_gen_date: 2026-04-12
last_publish_date: 2026-03-30
last_data_entry_date: 2026-03-29
last_analysis_date: 2026-04-12

current_phase: 修复期
# Auto-updated by analyze_performance.py
# Values: 修复期 | 建量期 | 稳定期

current_phase_week: 5
# Manually update this each Monday

company_post_count_this_month: 2
personal_post_count_this_month: 1
# 邪修3.0 (2026-03-24) 72h data: 861眼睛, 152赞, 66藏, 4评论 (薯条加持后)
# 工具清单1/4调研篇 (3/30) 已发布，72h数据待录入
# Gemini复刻TD效果 (3/30) 个人号已发布，72h数据待录入
offer_post_count_this_month: 0

warmup_complete: yes
# Set to "yes" after personal account warmup posts are published
# Only relevant during Week 1 of repair phase

# MANUAL SECTION — update these yourself:
# has_new_td_work: no
# has_new_case: no
# notes:
# 2026-04-05 weekly analysis: W3草稿就绪(公司号2篇) 个人号W3草稿已新建
# 竞品数据库无新条目，沿用历史分析
# 政策无新变化，2026 Q1规则稳定
last_missed_tasks: ⚠️ 个人号「vibe coding三个月后」4/30前必发（今天4/25最晚） | ⚠️ 工具清单1-3/6历史数据待补录(逾期) | ❓ 4/24「工具清单5/6排版篇」发布状态待XHS后台确认 | 📊 4/21工具清单4/6的72h数据今日可录
last_missed_date: 2026-04-25
# 2026-04-12 周日复盘: W4草稿新建完成(4/16五页排版模板+4/19 Figma快捷操作) | 开题三大坑扩写至800字 | 政策无新变化 | 竞品库无新条目 | 阶段继续修复期
