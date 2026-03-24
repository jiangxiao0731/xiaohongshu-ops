# 每周运营工作流 v5.1 (No-Scrape + Auto-Music Edition)

每次开session先看：`~/claude/xiaohongshu-ops/WORKFLOW-STATE.md`

---

## Shaw的3个手动动作/周

1. **周日晚** (~15分钟): 打开小红书，浏览同赛道竞品内容，记录到Notion「竞品观察」表
2. **周一晚** (~5分钟): 去Notion审批草稿（待审批 -> 已批准）
3. **周二晚** (~10分钟): 去XHS创作者中心，复制文案，设定时发布（北京19:30）

---

## 自动任务（launchd驱动）

| 时间 | 脚本 | 说明 |
|------|------|------|
| 每晚 21:00 | `notify.sh` | 根据星期几+当前阶段发macOS+Slack提醒 |
| 每晚 21:00 | `notion_daily_todo.py` | 更新Notion「今晚待办」callout |
| 每晚 23:45 | `nightly_review.py` | 检查待办完成情况 |
| 每小时 | `check_approved.py` | 检测Notion「已批准」→ 调Claude API生成草稿 |
| 周六 10:00 | `analyze_performance.py` | 分析发布数据 → latest-summary.json |
| 周日 10:00 | `weekly_brief.py` | 读Notion竞品观察表 → 生成竞品周报 |
| 周日 22:30 | `weekly_planner.py` | brief + analysis → 生成Notion草稿（待审批） |
| 文件夹变动 | `add_music.py --scan` | TD视频自动加配乐 + 生成个人号文案 → Notion草稿 |

---

## 每周流程

### 周日 20:00 — 收到通知「浏览竞品时间」

1. 打开小红书，搜索同赛道关键词（作品集/数媒/交互设计等）
2. 浏览15分钟，把看到的高互动帖子记录到Notion「竞品观察」表：
   - 标题、赞藏数、标签、来源关键词、账号名、观察日期
3. 完成后不用做其他事 — 自动脚本会在22:00+22:30接手

### 周日 22:00 — 自动

`weekly_brief.py` 读取Notion竞品观察 → 生成竞品周报 → 推送到Notion

### 周日 22:30 — 自动

`weekly_planner.py` 读取周报 + analysis → 调Claude API → 在Notion草稿库创建本周草稿（状态=待审批）

### 周一 09:00 — 收到通知「去Notion审批草稿」

1. 打开Notion草稿库，查看自动生成的本周草稿
2. 审核/修改内容
3. 状态改为「已批准」

### 周一 — 自动

`check_approved.py` 每小时检测 → 发现「已批准」→ 调Claude API生成完整正文 → 状态改「草稿就绪」→ macOS通知

### 周二 21:00 — 收到通知「明天发帖准备」

1. 打开Notion草稿库，复制本周草稿
2. XHS创作者中心 → 发布 → 设定时发布：北京时间 19:30（纽约7:30AM）
3. 勾选「AI辅助生成」标注
4. Notion发布表现记录新建一行

### 周三 07:30 — 帖子定时发出

发布后：开薯条（修复期50-150元/建量期100元），回复早期评论

### TD视频发布 — 自动（随时触发）

当新 `.mov` 文件被放入 `~/Desktop/td/export/` 时，launchd 自动触发 `add_music.py`：

1. ffmpeg 场景检测 → 分析视觉变化节点
2. Claude Vision → 生成贴合画面节奏的音乐提示词
3. Suno API → 生成匹配节奏的 AI 配乐
4. ffmpeg → 合并视频+音频（H.264 .mp4，2s fade in/out）
5. Claude → 生成个人号 XHS 文案（标题/正文/标签）
6. Notion → 在个人号草稿库创建「待审批」页面
7. macOS 通知「视频处理完成」
8. 输出文件：`~/Desktop/td/export/ready/*.mp4`

**Shaw 只需：导出 TD 视频 → 放入 export 文件夹 → 等通知 → 去 Notion 审批文案 → 上传视频到 XHS**

### 周六 10:00 — 自动

`analyze_performance.py` 分析数据 → 写入 analysis/latest-summary.json → 更新花钱决策日志

---

## 发布后数据录入（发帖72小时后）

在Notion发布表现记录填入：赞/藏/评论/私信条数、薯条金额、聚光CTR

---

## 快速状态查看

```bash
cat ~/claude/xiaohongshu-ops/WORKFLOW-STATE.md
```

---

*工作流版本：v5.1 | 2026-03-21 | No-Scrape + Auto-Music Edition — TD视频自动配乐+文案+Notion*
