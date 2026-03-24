#!/usr/bin/env python3
"""Rebuild the plans page with full side-by-side 12-week calendar."""

import os, sys
sys.path.insert(0, os.path.expanduser("~/claude/xiaohongshu-ops"))

env_file = os.path.expanduser("~/claude/xiaohongshu-ops/.env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"')

from notion_client import Client
notion = Client(auth=os.environ["NOTION_TOKEN"])

PLANS_PAGE_ID = "32693fe4326481e39af0f61b15f8f174"

def h2(text, color="default"):
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}], "color": color}
    }

def h3(text, color="default"):
    return {
        "object": "block", "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}], "color": color}
    }

def para(text, bold=False, color="default"):
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}, "annotations": {"bold": bold}}],
            "color": color
        }
    }

def bullet(text, bold_prefix=None):
    if bold_prefix:
        return {
            "object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {"type": "text", "text": {"content": bold_prefix}, "annotations": {"bold": True}},
                    {"type": "text", "text": {"content": text}}
                ]
            }
        }
    return {
        "object": "block", "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }

def callout(text, icon="📌", color="blue_background"):
    return {
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": icon},
            "color": color
        }
    }

def divider():
    return {"object": "block", "type": "divider", "divider": {}}

def columns(left_blocks, right_blocks):
    return {
        "object": "block", "type": "column_list",
        "column_list": {
            "children": [
                {"object": "block", "type": "column", "column": {"children": left_blocks}},
                {"object": "block", "type": "column", "column": {"children": right_blocks}},
            ]
        }
    }

def append(blocks):
    notion.blocks.children.append(PLANS_PAGE_ID, children=blocks)

# ---------------------------------------------------------------------------
# PAGE TITLE CALLOUT
# ---------------------------------------------------------------------------
append([
    callout(
        "12周运营计划 | 公司号 vs 个人号对照 | 修复期→建量期→稳定期",
        icon="📅", color="gray_background"
    ),
    divider(),
])

# ---------------------------------------------------------------------------
# PHASE 1 HEADER
# ---------------------------------------------------------------------------
append([
    h2("🔧 修复期 Phase 1（第1–4周）"),
    callout(
        "目标：恢复公司号权重，建立Shaw个人老师人设，为询单做铺垫。\n"
        "核心动作：隐藏违规帖 → 改名改简介 → 每周1篇合规教育型内容 + 薯条+聚光冷启动\n"
        "进入建量期条件（满足其一）：新帖72h有机≥50赞藏 / 聚光CTR≥3%且有询单",
        icon="📌", color="yellow_background"
    ),
])

# ---------------------------------------------------------------------------
# WEEK 1
# ---------------------------------------------------------------------------
append([h3("第1周（本周）")])
append([columns(
    [
        para("🏢 公司号「蕉蕉椒椒（作品集版）」", bold=True),
        bullet("标题：数媒邪修指南2.0 | 这些「非典型」方向凭什么能申上顶校"),
        bullet("钩子：「上周有个学生给我看他的作品集，全是装置艺术。我第一反应是：这很难申。然后我改口了。」"),
        bullet("正文：延续388赞藏爆款格式，3-4个具体「邪修」方向，每个配一句「为什么能申」的反直觉逻辑，Shaw第一人称视角"),
        bullet("结尾CTA：「你现在做的方向算不算邪修？评论区聊聊，我来判断值不值得做。」"),
        bullet("标签：#作品集辅导 #数媒作品集 #艺术留学作品集 #交互设计留学 #数字媒体艺术"),
        bullet("发布：周三北京时间20:00，发后立即开薯条100元×3天"),
        bullet("付费：薯条目标「涨粉/互动」，测试能否穿透限流"),
    ],
    [
        para("👤 个人号「蕉蕉椒椒」", bold=True),
        bullet("标题：用TouchDesigner做了一个会呼吸的粒子墙 | 10行代码"),
        bullet("钩子：前3秒展示最终效果视频（粒子随音频起伏），不说话不解释"),
        bullet("正文：选现有作品中视觉冲击力最强的一个，配简短教程：GLSL noise + audio reactive基础"),
        bullet("发布时间：周二/周四任意时间（不绑定周三档）"),
        bullet("配图：屏幕录制GIF + 代码截图（iPad Notes手写注释版）"),
        bullet("标签：#TouchDesigner #TouchDesigner教程 #创意编程 #生成艺术 #粒子 #generativeart"),
        bullet("为什么：个人号引流核心——TD视效帖历史均值约75赞藏，是最稳定的获客内容"),
    ]
)])

# ---------------------------------------------------------------------------
# WEEK 2
# ---------------------------------------------------------------------------
append([h3("第2周")])
append([columns(
    [
        para("🏢 公司号", bold=True),
        bullet("标题：UAL交互录取案例 | 把「失眠」做成了一个生成装置"),
        bullet("钩子：「有个学生来找我时，做的是平面设计方向。我们谈了一小时后，他把整套作品集推倒重来——以失眠为研究起点。」"),
        bullet("正文（合规版）：第一人称叙述，只写作品集策略逻辑，不写录取结果/GPA/时间承诺"),
        bullet("项目1：失眠数据可视化装置 — 研究问题「城市噪声如何影响睡眠节律」"),
        bullet("项目2：生成音景 — 让用户「听到」自己的失眠数据"),
        bullet("项目3：公共装置概念 — 失眠患者匿名数据共享展"),
        bullet("结尾：「有类似方向的评论区说说，我来看看。」"),
        bullet("付费：聚光冷启动50元/天，关键词：作品集辅导/数媒作品集/交互设计留学"),
        bullet("注意：封面用作品截图，不用offer邮件"),
    ],
    [
        para("👤 个人号", bold=True),
        bullet("标题：测了一周最火的AI视频工具，说说哪个真的能用"),
        bullet("钩子：选当周最热门的AI视频/图像生成工具（Sora/Kling/Runway等），48小时内跟进"),
        bullet("正文：真实测试3-5个案例，每个配原始输入prompt和输出结果，不美化"),
        bullet("重点：「我作为一个装置艺术从业者，这个工具对我有没有用」——垂直视角，不做泛科技测评"),
        bullet("发布：AI热点时效性强，工具发布后48h内必须发"),
        bullet("标签：#AI工具 #AI视频 #创意编程 #数字媒体艺术 #生成艺术"),
        bullet("为什么：AI工具帖历史均值161赞藏，是个人号最高类目"),
    ]
)])

# ---------------------------------------------------------------------------
# WEEK 3
# ---------------------------------------------------------------------------
append([h3("第3周")])
append([columns(
    [
        para("🏢 公司号", bold=True),
        bullet("标题：交互设计留学3个方向的真实区别 | 申请前必读"),
        bullet("钩子：「每周都有人问我：IDM和IXD和Service Design有什么区别，申哪个更好？我每次都想说：问错问题了。」"),
        bullet("正文：IDM（NYU）vs IXD（RCA/UAL）vs Service Design三个方向，从作品集类型/导师研究方向/毕业去向三个维度对比"),
        bullet("Shaw视角：「我自己申的IDM，当时有一个关键判断是...」——植入个人经历作为信任背书"),
        bullet("结尾：「你倾向哪个方向，评论区告诉我，我帮你看合不合适你的背景。」"),
        bullet("付费：聚光持续，观察CTR是否≥2%"),
        bullet("碎片帖（同周）：「今天改了5份研究计划，发现大家卡的是同一个地方」（100字，不需要CTA）"),
    ],
    [
        para("👤 个人号", bold=True),
        bullet("标题：TouchDesigner + Mediapipe 升级版 | 现在可以控制10个关节点了"),
        bullet("钩子：接上期手势控制帖（131赞藏），展示新版本支持全身骨骼追踪"),
        bullet("正文：对比上期：原来只能追踪手指，现在加了肩/肘/腰，展示在装置表演中的实际应用"),
        bullet("发布形式：竖版视频，前5秒展示效果，后15秒快速演示节点连接"),
        bullet("标签：#TouchDesigner #Mediapipe #创意编程 #互动装置 #交互艺术 #新媒体艺术"),
        bullet("为什么：系列内容留存率高，老粉会回来看升级版，算法倾向推荐有互动历史的账号"),
    ]
)])

# ---------------------------------------------------------------------------
# WEEK 4
# ---------------------------------------------------------------------------
append([h3("第4周")])
append([columns(
    [
        para("🏢 公司号", bold=True),
        bullet("标题：作品集研究部分怎么写 | 大部分人卡在这里"),
        bullet("钩子：「『研究』两个字把很多人吓到了。我帮学生改稿时，80%的问题都出在这一部分——不是不会做研究，是不知道研究要证明什么。」"),
        bullet("正文：研究部分的3个功能（证明问题存在/建立你的方法论/为3个项目铺垫），每个功能配1个具体示例"),
        bullet("示例用真实改稿片段（脱敏），展示改前/改后对比"),
        bullet("结尾：「把你的研究问题发评论区，我来看看逻辑通不通。」"),
        bullet("付费：根据第3周数据决定聚光是否加量"),
        bullet("数据复盘：4周后评估——有机赞藏趋势 / 聚光CTR / 询单数 → 决定是否进入建量期"),
    ],
    [
        para("👤 个人号", bold=True),
        bullet("标题：NYU ITP 2025毕业展 | 这几个装置我想聊聊"),
        bullet("钩子：「上周专门去看了ITP的毕设展，走了两个小时，想跟你们说说让我停下来的几件作品。」"),
        bullet("正文：选3-4件装置，每件写：1) 用一句话说清楚研究问题，2) 我作为从业者的技术判断，3) 如果是我会怎么改"),
        bullet("配图：现场照片（申请拍摄许可或网络公开图），不用精修"),
        bullet("发布时间：毕业展季（4-5月）前后，时机对准"),
        bullet("标签：#新媒体艺术 #互动装置 #数字艺术 #NYU #数字媒体艺术 #生成艺术"),
        bullet("为什么：展览类帖均值约60，但评论互动质量高（精准用户），适合在修复期末积累真实粉丝"),
    ]
)])

append([divider()])

# ---------------------------------------------------------------------------
# PHASE 2 HEADER
# ---------------------------------------------------------------------------
append([
    h2("📈 建量期 Phase 2（第5–8周）"),
    callout(
        "进入条件（满足其一）：新帖72h有机≥50赞藏 OR 聚光CTR≥3%且有询单\n"
        "公司号升至每周2篇（周三+周日）。聚光预算升至100元/天。\n"
        "个人号维持1-2篇/周，逐步引入系列内容。",
        icon="📌", color="green_background"
    ),
])

# WEEK 5
append([h3("第5周")])
append([columns(
    [
        para("🏢 公司号（周三+周日）", bold=True),
        bullet("周三：如何用「研究型」思维做作品集 | 不是做项目，是回答问题"),
        bullet("钩子：「大部分作品集看起来是3个项目。好的作品集是一个研究，用3个项目来回答同一个问题。」"),
        bullet("正文：用Shaw自己申IDM时的思路为例，展示什么是「研究驱动」vs「项目堆砌」"),
        bullet("周日：平面设计背景转交互 | 这条路我见过走通的人是怎么做的"),
        bullet("钩子：「每学期都有平面设计背景的人来找我，说想申交互设计。我通常第一个问题是：你对什么问题感兴趣？」"),
        bullet("付费：聚光100元/天，若有帖子有机≥30赞藏，用它做聚光「最优内容推广」"),
    ],
    [
        para("👤 个人号（每周1-2篇）", bold=True),
        bullet("TD系列开篇：「创意编程入门 Week 1 | 从0开始做一个会动的圆」"),
        bullet("逻辑：把知识点拆成系列，增加粉丝留存和追更动力"),
        bullet("Week1内容：基础shape操作 + noise函数让圆「呼吸」，视频时长5分钟以内"),
        bullet("系列设计：每周一篇，共4周，从基础到audio reactive，最后做一个完整作品"),
        bullet("为什么做系列：系列内容账号粉丝粘性提升约30%，算法偏好有追更行为的账号"),
    ]
)])

# WEEK 6
append([h3("第6周")])
append([columns(
    [
        para("🏢 公司号", bold=True),
        bullet("周三：RCA录取案例 | 用城市垃圾数据重新定义「废弃物美学」"),
        bullet("合规格式：第一人称叙述，聚焦作品集策略，3个项目，不写录取结果"),
        bullet("选题逻辑：RCA在竞品帖中频次高，用户对它关注度高，用案例植入关键词"),
        bullet("周日：数媒作品集最常见的3个「死穴」| 改稿时发现的"),
        bullet("钩子：「改了3年作品集，某些问题出现频率高得让我开始怀疑是不是有人在传模板。」"),
        bullet("3个死穴：1)研究问题太宽泛，2)项目之间没有逻辑关系，3)设计决策没有依据"),
        bullet("付费：重点观察哪篇CTR更高——案例类 vs 方法论类，调整后续内容比例"),
    ],
    [
        para("👤 个人号", bold=True),
        bullet("TD系列Week2：「创意编程 Week 2 | 让声音控制画面——audio reactive基础」"),
        bullet("内容：FFT分析 + 音频输入，让音乐的bass控制圆的大小，treble控制颜色"),
        bullet("加入互动：「上周的作业截图来了！@xxxx 做的版本比我好看」——展示粉丝作业"),
        bullet("额外：若有热门AI工具发布，可插入一篇AI测评（系列可以暂停一期）"),
        bullet("运营动作：主动@上期评论区问「做完了吗」的粉丝，增加召回"),
    ]
)])

# WEEK 7
append([h3("第7周")])
append([columns(
    [
        para("🏢 公司号", bold=True),
        bullet("周三：申请季倒计时 | 9月截止的学校现在到什么阶段了"),
        bullet("时机：配合申请季节点（9月截止→7月应完成初稿），踩热点增加搜索流量"),
        bullet("正文：时间线规划，用Shaw视角说「如果是我，现在应该在做什么」"),
        bullet("周日：作品集封面设计 | 为什么大部分封面都太无聊了"),
        bullet("正文：展示5个让人停下来的封面和5个让人划走的封面，分析视觉逻辑"),
        bullet("结尾：「你的封面现在是什么样的，发图到评论区」——互动率提升帖"),
        bullet("付费：若聚光有跑出CTR≥3%的关键词，加量至150元/天"),
    ],
    [
        para("👤 个人号", bold=True),
        bullet("TD系列Week3：「创意编程 Week 3 | 用摄像头控制粒子——Kinect/Mediapipe接入」"),
        bullet("内容：接入摄像头输入，让人体运动控制粒子系统，展示在现场表演中的效果"),
        bullet("视频：前5秒必须是「人站在粒子瀑布前，随手势流动」的视觉，无需解说"),
        bullet("展览帖备选：若本周有国内优质毕设展，插入展览观察帖"),
    ]
)])

# WEEK 8
append([h3("第8周")])
append([columns(
    [
        para("🏢 公司号", bold=True),
        bullet("周三：NYU IDM录取案例 | 用街区噪声重新定义城市边界"),
        bullet("这是Shaw最强的个人信任背书——自己毕业的项目，第一人称最自然"),
        bullet("正文：自述申请时的作品集思路，展示3个项目的研究逻辑，最后说「这套逻辑现在帮学生用」"),
        bullet("周日：建量期数据复盘 + 下一阶段预告"),
        bullet("内容：「8周下来，我发现小红书用户对作品集内容的关注点在这几个地方...」"),
        bullet("目的：建立账号的「分析师形象」，让粉丝觉得关注这个账号有认知价值"),
        bullet("付费：全面评估8周数据，决定稳定期预算配置"),
    ],
    [
        para("👤 个人号", bold=True),
        bullet("TD系列Week4（收官）：「创意编程 Week 4 | 把前3周学的全用上，做一个完整装置」"),
        bullet("内容：综合noise/audio/mediapipe，做一个5分钟能讲清楚的完整作品"),
        bullet("配套：发布完整项目文件到GitHub，帖子里提供链接（增加收藏动力）"),
        bullet("系列总结：「4周系列结束了，问问大家想学什么」——下个系列选题调研"),
        bullet("运营：若系列累计赞藏超过200，考虑用最佳一篇做加热（100元）"),
    ]
)])

append([divider()])

# ---------------------------------------------------------------------------
# PHASE 3 HEADER
# ---------------------------------------------------------------------------
append([
    h2("🎯 稳定期 Phase 3（第9周起）"),
    callout(
        "双轨成熟：内容自然流量 + 付费投流协同。\n"
        "公司号：维持周三+周日，聚光优化（保留CTR>3%关键词，月预算300元）。\n"
        "个人号：维持1-2篇，加热表现最好的TD帖（100元/月）。\n"
        "目标：10-20条询单/月。",
        icon="📌", color="purple_background"
    ),
])

append([columns(
    [
        para("🏢 公司号稳定期策略", bold=True),
        bullet("内容：维持「30%教程 / 30%方法论 / 20%方向干货 / 10%案例 / 10%碎片」比例"),
        bullet("案例类：≤2篇/月，全部走合规格式，封面用作品截图"),
        bullet("聚光：月预算300元，只保留CTR>3%的关键词，每2周审查一次"),
        bullet("薯条：只在有机≥30赞藏的帖子上加投（已验证内容再放量）"),
        bullet("系列内容：考虑「作品集方法论系列」4期，形成知识体系"),
        bullet("询单承接：评论区→私信→微信，保持「评论区先聊」的习惯"),
    ],
    [
        para("👤 个人号稳定期策略", bold=True),
        bullet("内容：维持「55%TD教程 / 25%AI测评 / 20%展览」节奏"),
        bullet("新系列：根据第5-8周粉丝反馈决定下一个系列主题"),
        bullet("加热：100元/月，用在赞藏最高的那篇TD帖上"),
        bullet("品牌连接：简介维持「蕉蕉椒椒（作品集版）」字样，不主动引导"),
        bullet("跨账号协同：两个号同周发布时，内容在认知层面形成互补（不互相提及）"),
        bullet("评估：若个人号粉丝超过5000，考虑是否开通个人号聚光"),
    ]
)])

# ---------------------------------------------------------------------------
# CLOSING
# ---------------------------------------------------------------------------
append([
    divider(),
    callout(
        "协同逻辑：个人号负责引流和信任建立（「这个人懂技术」），公司号负责转化（「这个老师能帮到我」）。"
        "两个号的内容在认知层面互补，简介里互相可见，帖子里绝不交叉引流。\n\n"
        "数据驱动决策：每周数据录入Notion发布表现记录 → analyze_performance.py自动生成建议 → 下周内容和付费决策基于上周数据。",
        icon="🔗", color="gray_background"
    ),
])

print("Plans page rebuilt successfully.")
