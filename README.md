# 小红书双号运营系统

核心目标：个人号为主引擎带流量，公司号为辅助做转化（12周计划）

---

## 文件结构

```
xiaohongshu-ops/
├── README.md                       ← 你在这里
├── CLAUDE.md                       ← 项目配置 + 规则 + subagent文档
├── PLAN-v3.0-2026-03-24.md         ← 总体运营计划（策略/定位/投流/目标）
├── CALENDAR.md                     ← 12周内容日历
├── WORKFLOW.md                     ← 每周操作流程 + 自动化说明
├── WORKFLOW-STATE.md               ← 运行状态（phase/cookie/发布记录）
├── TAGS.md                         ← 标签策略
├── XHS-POLICY-RESEARCH-2026.md     ← 平台政策研究
├── SETUP.md                        ← 一次性配置清单
├── templates/
│   ├── TEMPLATE-company.md         ← 公司号5种内容类型模板
│   └── TEMPLATE-personal.md        ← 个人号3种内容类型模板
├── automation/                     ← 自动化脚本（launchd驱动）
│   ├── utils.py                    ← 共享工具函数
│   ├── weekly_brief.py             ← 竞品周报生成
│   ├── weekly_planner.py           ← 周草稿规划 + Notion创建
│   ├── gen_content.py              ← Claude API内容生成
│   ├── check_approved.py           ← 检测Notion已批准 → 触发生成
│   ├── analyze_performance.py      ← 发布数据分析
│   ├── notion_daily_todo.py        ← Notion每晚待办更新
│   ├── add_music.py                ← TD视频自动配乐 + 文案
│   ├── notify.sh                   ← macOS + Slack通知
│   ├── slack_daily.sh              ← 每日Slack提醒
│   └── slack_post_reminder.sh      ← 发帖日30分钟提醒
├── .claude/agents/                 ← 10个subagent定义
├── .env.example                    ← 环境变量模板
├── requirements.txt                ← Python依赖
└── notion-ids.json                 ← Notion database IDs（自动生成）
```

---

## 当前状态

详见 `WORKFLOW-STATE.md`（机器可读）和 `PLAN-v3.0-2026-03-24.md`（策略全貌）。

---

## 每周循环

1. **周日晚** — 浏览竞品，记录到Notion竞品观察表
2. **周日 22:00+** — 自动生成竞品周报 + 本周草稿
3. **周一晚** — 审批Notion草稿（待审批 → 已批准）
4. **周二晚** — 复制文案到XHS，设定时发布（北京19:00）
5. **周三** — 帖子发出，开薯条，回复评论
6. **发布72h后** — Notion录入赞/藏/评/私信数据

详细流程见 `WORKFLOW.md`。

---

## 关键决策参考

| 决策 | 标准 | 数据来源 |
|------|------|---------|
| 这篇帖子要不要投流？ | 曝光>500 且 点赞率>3% | Notion发布表现记录 |
| 这类内容要不要继续做？ | 发布后有私信询单 | Notion发布表现记录 |
| 聚光要不要继续？ | CPC<2元 且 CTR>3% | 聚光后台 |
| 阶段是否升级？ | 新帖72h有机赞藏≥50 | analyze_performance.py |
