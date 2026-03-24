# 小红书双号运营系统

核心目标：公司号月询单量 0 → 5 → 15 → 20+（12周）

---

## 文件结构

```
xiaohongshu-ops/
├── README.md            ← 你在这里
├── SETUP.md             ← 账号基础设置清单（本周完成）
├── CALENDAR.md          ← 8周内容日历
├── WORKFLOW.md          ← 每周操作流程（<1小时/周）
├── TAGS.md              ← 标签数据库（v0.1，待数据更新）
├── TRACKER.md           ← 数据追踪表
├── templates/
│   ├── TEMPLATE-company.md   ← 公司号4种内容类型模板
│   └── TEMPLATE-personal.md  ← 个人号3种内容类型模板
├── analysis/
│   └── ANALYSIS-PROMPT.md    ← MediaCrawler数据分析提示词
├── content/             ← 存放草稿和发布版本
├── data/                ← 存放MediaCrawler输出的CSV
└── .venv/               ← MediaCrawler Python虚拟环境
```

---

## 当前状态（2026-03-16）

- [x] MediaCrawler 已安装（~/Downloads/MediaCrawler/）
- [x] 虚拟环境已配置（~/xiaohongshu-ops/.venv/）
- [ ] MediaCrawler 登录授权（需要扫QR码）
- [ ] 5组关键词数据抓取
- [ ] 账号基础设置（见SETUP.md）
- [ ] 聚光账户开通

---

## 立即执行（今天）

### 1. MediaCrawler 登录授权

```bash
cd ~/Downloads/MediaCrawler
source ~/xiaohongshu-ops/.venv/bin/activate
python main.py --platform xhs --lt qrcode
# 扫码授权小红书账号
```

### 2. 抓取5组竞品数据

```bash
# 在同一个终端（已激活venv）
python main.py --platform xhs --lt qrcode --crawler-type search --keywords "作品集辅导" --save-data-option csv
python main.py --platform xhs --lt qrcode --crawler-type search --keywords "艺术留学作品集" --save-data-option csv
python main.py --platform xhs --lt qrcode --crawler-type search --keywords "数媒作品集" --save-data-option csv
python main.py --platform xhs --lt qrcode --crawler-type search --keywords "Touchdesigner教程" --save-data-option csv
python main.py --platform xhs --lt qrcode --crawler-type search --keywords "offer录取 艺术留学" --save-data-option csv
```

数据输出到：`~/Downloads/MediaCrawler/data/`

### 3. 分析数据

将CSV内容 + `analysis/ANALYSIS-PROMPT.md` 中的提示词 → 发给Claude

### 4. 完成账号设置

按 SETUP.md 完成7项账号操作

---

## 每周循环（从下周开始）

1. 周一：按WORKFLOW.md提交上周数据 → 获取本周草稿
2. 周三 晚7:30北京（纽约7:30AM）：发布第1篇（高峰前30分钟）
3. 周日 晚7:30北京（纽约7:30AM）：发布第2篇（高峰前30分钟）
4. 发布72小时后：更新TRACKER.md

---

## 关键决策参考

| 决策 | 标准 | 数据来源 |
|------|------|---------|
| 这篇帖子要不要投流？ | 曝光>500 且 点赞率>3% | TRACKER.md |
| 这类内容要不要继续做？ | 发布后有私信询单 | TRACKER.md |
| 聚光要不要继续？ | CPC<2元 且 CTR>3% | 聚光后台 |
| 账号名要不要改？ | 竞品数据分析结论 | ANALYSIS-PROMPT.md |
