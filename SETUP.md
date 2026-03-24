# 小红书运营中心 — 一次性配置清单

执行顺序按优先级排列。每项完成后打勾。
预计总时间：约30分钟（分两次完成：账号操作10分钟，技术配置20分钟）

---

## Part 1：账号操作（手机完成，今天）

### 公司号「No Turn on Red → 改名为 蕉蕉椒椒（作品集版）」

- [ ] **隐藏违规帖** — 逐条进入，改为「仅自己可见」：
  - 商科转数媒零基础超低GPA录取SAIC
  - 服务设计5天5offer免面试秒录
  - OMG！我拿到DAE的offer了！
  - 纽约今天谁在用无人机求婚啊！
  - 🔸纽约啥都做工作室🔸
  - 📢📢📢 30岁的第一天干了件大事！！！
  - 陈老师终于把我的毕设剪好了！

- [ ] **置顶**「数媒邪修指南」（388赞藏，合规）

- [ ] **改名**：昵称改为 `蕉蕉椒椒（作品集版）`

- [ ] **更新简介**：
  ```
  数媒/交互/平面/纯艺 作品集｜NYU IDM毕业｜Shaw
  英美为主｜帮你找到真正属于你的作品集方向
  评论区或私信聊
  ```

- [ ] **配置私信自动回复**（创作者中心 → 私信设置）：
  - 欢迎语：`你好！你是哪个专业方向，本科还是研究生申请？`
  - 触发词 `作品集` → `你好！你是哪个专业方向？数媒/交互/平面/纯艺？我来帮你分析一下方向。`
  - 触发词 `辅导` → `你好！请问你目前的申请阶段是？作品集做到哪一步了？`

- [ ] **开通专业号认证**（2026年强制要求，教育类内容必须）：
  - 创作者中心 → 专业号 → 认证类型选「教育培训-留学」
  - 需要营业执照或个人资质证明
  - 未认证账号发布教育类内容会被限流

---

## Part 2：技术配置（Mac完成，今天）

### Step 1 — Notion集成 Token

1. 访问 `notion.so/profile/integrations` → 「New integration」
2. 类型：Internal，名称：xhs-ops
3. 复制 Token（`secret_xxx`）
4. 打开小红书Notion页面 → 右上角「...」→「Connections」→ 添加刚建的Integration
5. 添加到 shell：
   ```bash
   echo 'export NOTION_TOKEN="secret_xxx"' >> ~/.zshrc
   source ~/.zshrc
   ```

### Step 2 — Anthropic API Key（内容自动生成）

1. 访问 `console.anthropic.com` → 注册 → 充值 $10-20
2. 「API Keys」→「Create Key」→ 复制
3. 添加到 shell：
   ```bash
   echo 'export ANTHROPIC_API_KEY="sk-ant-xxx"' >> ~/.zshrc
   source ~/.zshrc
   ```
   每次生成约 $0.04，$20 够用半年。

### Step 3 — 初始化 Notion 页面结构

```bash
source ~/claude/xiaohongshu-ops/.venv/bin/activate
python3 ~/claude/xiaohongshu-ops/automation/setup_notion.py
```

这一步自动创建所有 database（草稿库、发布记录、竞品周报、花钱日志）和「本周状态」callout。
Database ID 保存到 `~/claude/xiaohongshu-ops/notion-ids.json`。

### Step 4 — 注册 launchd 任务

```bash
cd ~/Library/LaunchAgents

launchctl load com.xhs.scrape.daily.plist
launchctl load com.xhs.brief.weekly.plist
launchctl load com.xhs.check.hourly.plist
launchctl load com.xhs.notify.daily.plist
launchctl load com.xhs.notify.wed.plist
launchctl load com.xhs.notify.sun.plist
```

验证：
```bash
launchctl list | grep xhs
```
应出现6行。

### Step 5 — 安装 MediaCrawler

```bash
# 安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 克隆 MediaCrawler（NanmiCoder/MediaCrawler）
cd ~/claude/xiaohongshu-ops
git clone https://github.com/NanmiCoder/MediaCrawler.git

# 安装依赖
cd MediaCrawler
uv sync
uv run playwright install chromium
```

### Step 6 — 首次登录（扫码获取Cookie）

```bash
cd ~/claude/xiaohongshu-ops/MediaCrawler
export PATH="$HOME/.local/bin:$PATH"
uv run python main.py --platform xhs --lt qrcode --type search --keywords "测试"
```

用小红书APP扫描终端中的二维码登录。登录态会自动缓存，后续脚本使用 `--lt cookie` 复用。

### Step 7 — 测试抓取

```bash
bash ~/claude/xiaohongshu-ops/automation/daily_scrape.sh
```

成功后查看 `~/claude/xiaohongshu-ops/data/` 是否有 CSV 输出。

---

## Part 3：开通聚光广告账户

- [ ] 小红书创作者中心 → 推广 → 聚光平台
- [ ] 首次开通，最低充值 1000 元（按需消耗）
- [ ] 第 2 周起开搜索推广：关键词 `作品集辅导` / `数媒作品集` / `交互设计留学`，日预算 50 元

---

## 完成后验证

- [ ] `launchctl list | grep xhs` 显示 6 行
- [ ] `~/claude/xiaohongshu-ops/notion-ids.json` 文件存在
- [ ] `~/claude/xiaohongshu-ops/MediaCrawler/` 目录存在，`uv run python main.py --help` 正常输出
- [ ] 小红书搜索「作品集辅导」，确认公司号出现
- [ ] 用另一个账号私信「作品集」，确认自动回复触发

---

完成时间目标：2026-03-23
