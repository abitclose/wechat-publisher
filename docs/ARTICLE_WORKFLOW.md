# 微信公众号推文创作与发布工作流规约 (Article Creation & Publishing Workflow)

> 本文档为 `wechat-publisher` 的核心业务规范，系统化定义了从选题策划、Hook/结构选型、正文撰写、人味化改写、双轨配图、富文本排版到草稿箱发布的完整生命周期与操作标准。
> 所有人类开发者与 AI Agent 在执行推文生产任务时必须严格遵从本规约。

---

## 1. 总体架构与双模流速 (Overview & Operating Modes)

推文生产系统支持两种互补的作业模式：

1. **总控一键流水线 (Master Pipeline · `gen.py`)**：
   - 面向端到端自动化生产，按标准时序依次调度封面生图、本地卡片离线渲染、反 AI 门禁自检与草稿箱推送；
   - 支持 `--dry-run` 离线预演模式（不消耗 API 额度、不向微信推送，脱机打印执行计划与真实命令）。
2. **Agent 交互式创作流 (Skill Interactive Mode · `SKILL.md`)**：
   - 面向与用户/编辑深度结对的人机协同创作，分为 6+1 个精细化阶段，步步确认。

### 全流程生命周期拓扑图

```mermaid
flowchart TD
    subgraph S1["1. 需求与规划 (Brief)"]
        A[输入选题/参考素材] --> B[账号与人格 Voice 绑定<br/>main/飞哥 vs tech/葱哥]
        B --> C[选定 8 种推进结构 × 7 种 Hook 钩子<br/>生成 brief.md 蓝图]
    end

    subgraph S2["2. 双层素材调研 (Research)"]
        C --> D1[权威层: 官方资讯/Release Notes/评测]
        C --> D2[真人层: V2EX/Reddit/即刻 一线吐槽语料]
        D1 & D2 --> E[交叉验证生成 research.md]
    end

    subgraph S3["3. 骨架撰写与人味化改写 (Drafting)"]
        E --> F[阶段 3: Markdown 初稿骨架<br/>混用 8 种行内标色标记]
        F --> G[阶段 3.5: 人味化改写 Pass<br/>9 项强制清单 + 句长抖动 Burstiness]
    end

    subgraph S4["4. 双轨配图生成 (Visuals)"]
        G --> H1[轨道 A: 云端模型生图 (Gemini/OpenAI)<br/>仅 1 次调用生成 16:9 头条封面]
        G --> H2[轨道 B: 本地无头 Chrome 排版卡 (typeset-card)<br/>离线渲染 0 成本高保真插图]
    end

    subgraph S5["5. 微信富文本排版 (Typesetting)"]
        H1 & H2 --> I[html_converter.py<br/>注入 15 套内置主题 JSON]
        I --> J[编译为纯行内 CSS Inline Styles<br/>适配 375px 移动端视口]
    end

    subgraph S6["6. 质量门禁与发布 (Quality Gate & Publish)"]
        J --> K{ai_score.py<br/>6 维反 AI 检测门禁}
        K -- "≥ 45分 (拦截)" --> G
        K -- "< 45分 (放行)" --> L[publish.py 上传微信素材库]
        L --> M[保存为微信后台草稿箱 Draft<br/>严格不自动群发]
    end
```

---

## 2. 阶段一：需求规划与结构蓝图 (Brief & Structure Planning)

在动笔写正文之前，必须先明确**发哪个号、用什么人格语气、几千字怎么展开、前 3 秒怎么留人**，并写入 `brief.md`。

### 2.1 账号与人格 Voice 规范

| 标识 (`account`) | 公众号名称 | 作者名 | 默认排版主题 | 写作人格特征 (Voice) | 适用领域 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`main`**（默认）| 刷屏AI | **飞哥** | `refined-blue` | 热情、爱打比方、生活化踩坑、情绪有起伏、禁用“我跟你讲/我跟你说”等对读者说教喊话的口语。 | AI 产品评测、个人生产力、提示工程、Agent 应用 |
| **`tech`** | 蒜是哪根葱 | **葱哥** | `minimal-mono` | 技术极客风、冷幽默、**禁用感叹号**、爱贴命令行输出、版本号与 commit hash。 | 源码剖析、CLI/SDK 开发、底层协议与工程实践 |

### 2.2 8 种正文推进结构 (`article_structure`)

长文正文必须选择以下结构之一推进，严禁写成千篇一律的流水账或教科书式结构：

1. **`playbook`（行动清单）**：适合技巧/生产力指南。适合人群 $\rightarrow$ 最短路径 $\rightarrow$ 3~5 个核心动作 $\rightarrow$ 避坑指南 $\rightarrow$ 何时不该用。
2. **`field-notes`（实测笔记）**：适合本机实验与踩坑。从报错/日志切入 $\rightarrow$ 我跑了什么 $\rightarrow$ 哪里顺 $\rightarrow$ 哪里坑 $\rightarrow$ 实战建议。
3. **`contrarian`（反常识）**：适合认知纠偏。大家普遍怎么看 $\rightarrow$ 为什么不对 $\rightarrow$ 核心反常证据 $\rightarrow$ 新的认知框架。
4. **`teardown`（拆解剖析）**：适合架构/SDK剖析。先给三层总览图 $\rightarrow$ 模块逐层拆解 $\rightarrow$ 关键设计取舍 $\rightarrow$ 与旧方案对比。
5. **`data-first`（数据砸脸）**：适合榜单/评测/财报。甩出一个反常数字或排名 $\rightarrow$ 是什么 $\rightarrow$ 为什么可信 $\rightarrow$ 行业影响。
6. **`question-led`（问题追踪）**：适合行业争议与疑难杂症。抛出具体问题 $\rightarrow$ 证据链 A/B $\rightarrow$ 哪些已确认 $\rightarrow$ 结论边界。
7. **`timeline-news`（时间线新闻）**：适合热点大事件复盘。发生什么 $\rightarrow$ 时间线推进 $\rightarrow$ 关键角色反应 $\rightarrow$ 后续观察重点。
8. **`case-file`（案卷复盘）**：适合商业翻车/安全事故复盘。案情摘要 $\rightarrow$ 证据链复盘 $\rightarrow$ 错在哪里 $\rightarrow$ 普通人启示。

### 2.3 7 种开篇 Hook 钩子 (`opening_hook`)

开篇前 3~5 行文字决定完读率与跳出率，**严格禁止使用“随着……的飞速发展”等宏观空泛废话**：

1. **`hard-number`**：直接扔出刺眼的具体数字、金额、比例或耗时；
2. **`scene-first`**：直接把读者拉入具体对话、事故翻车现场或深夜加班场景；
3. **`artifact-first`**：直接贴一段真实的终端报错输出、Git Commit 日志或截图描述；
4. **`sharp-question`**：抛出一个直击灵魂的大白话尖锐问题；
5. **`contradiction`**：将两个强烈冲突的事实并排放置引发好奇；
6. **`quote-first`**：直接引用一线工程师或当事人的吐槽原话；
7. **`timeline-first`**：精确到具体日期的事件链推进。

### 2.4 `brief.md` 蓝图规范

归档于 `mp-articles/<account>/<YYYY-MM-DD>-<slug>/brief.md`，标准结构：

```markdown
---
topic: "普通人/程序员如何用 AI 提升效率、避免踩坑"
account: main
author: "飞哥"
theme: refined-blue
article_structure: playbook
opening_hook: scene-first
cover_style: hand-drawn-blue
---

# 选题摘要
面向程序员与数字化工作者，破除“AI 必须一键全自动化”的幻想，结合真实调试踩坑经历，梳理小步快跑与确定性验收的工作流。

# 核心细节与踩坑清单 (真人真事原料，反 AI 味核心)
1. 真实踩坑案例：数据库迁移脚本漏了 1 个字段，排查耗时 3 小时；
2. 误区一：把大任务一揽子丢给 AI，结果自己成了全职纠错员；
3. 实操三板斧：小步验收、样例示范 (Few-shot)、轻量敏捷回滚。
```

---

## 3. 阶段二：素材调研与双层语料 (Research)

- **权威层**：抓取 6 个月内官方权威数据、发布会日志、架构文档；
- **真人语料层（反 AI 核心原料）**：重点抓取 V2EX、Reddit、知乎、X、即刻上的一线真实讨论与吐槽原话，记录于 `research.md`。

---

## 4. 阶段三 & 3.5：骨架撰写与人味化改写 (Drafting & Anti-AI)

### 4.1 骨架初撰与行内标色系统
一篇文章内**必须主动混用多种行内标色标记**，打破 AI 均质文本指纹：
- `**加粗结论**`：最重要的核心结论（一段最多 1 次）；
- `==黄色背景高亮==`：关键数据 / 核心论点；
- `++蓝色背景高亮++`：概念定义 / 工具名 / 平台名；
- `%%粉色背景高亮%%`：警示 / 陷阱 / 反面案例；
- `&&绿色背景高亮&&`：正面结果 / 推荐做法；
- `!!红色强调!!`：严重警告 / 负面数字；
- `@@蓝色强调@@`：术语 / 专有名词；
- `^^橙色强调^^`：温暖点缀 / 亮点；
- `===`：章节分节符。

### 4.2 阶段 3.5 人味化独立审校 Pass（9 项强制清单）
1. **句长抖动 (Burstiness)**：长句、短句与单字断句交替出现；
2. **句式多样性**：禁止连续三句主谓宾相同；
3. **AI 高频词黑名单清洗**：彻底剔除“赋能、闭环、矩阵、维度、抓手、综上所述、值得一提的是、毋庸置疑、不可否认、由此可见”；
4. **开头破冰**：严格按选定的 `opening_hook` 切入；
5. **人称与立场**：统一使用“我们”或“我”，严禁站在上帝视角说教；
6. **事实密度**：必须带有具体时间、版本号、报错细节；
7. **标点多样性**：自然使用破折号、括号注解；
8. **结构的不完美**：小节长短错落，严禁机械对称；
9. **账号 Voice 再校准**：检查是否符合当前账号人格。

---

## 5. 阶段四：双轨配图体系 (Dual-Track Visuals)

系统并行运行两套视觉生成轨道，兼顾“艺术美感”与“文字高保真”：

```text
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ 轨道 A: 云端生图 (Gemini/OpenAI)     │ 轨道 B: 本地无头 Chrome 排版海报卡   │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • 仅用于：16:9 头条封面图 (1 次调用) │ • 用于：文内金句、对比、实操小抄插图 │
│ • 优势：手绘蓝调艺术水彩感           │ • 优势：本地 0 API 消耗、离线运行    │
│ • 劣势：中文文字易模糊变形           │ • 优势：中文与符号绝对精确、Retina2x │
│ • 脚本：scripts/generate_image.py    │ • 脚本：scripts/typeset_card_gen.py  │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### 5.1 本地无头 Chrome 排版卡三大原型

卡片数据收敛于 `cards_data.json`，由本地 Chrome 2x 离线渲染为高清 PNG：
1. **金句卡 (`quote`)**：大字观点输出，高度自适应；
2. **对比卡 (`contrast`)**：上下堆叠误区与正解对撞，三列严格对齐，高度自适应；
3. **实操清单卡 (`checklist`)**：结构化避坑小抄，带序号与高亮标签。

> **临时文件沙箱铁律**：所有渲染过程中的中间 HTML 片段强制存放在 `<repo>/generated/tmp/` 目录中，任务结束必须 100% 清理，严禁写入系统全局临时目录。

---

## 6. 阶段五：富文本编译与微信排版 (Typesetting)

- 核心脚本：[`scripts/html_converter.py`](file:///home/white/github/wechat-publisher/scripts/html_converter.py)
- **100% 纯行内 CSS（Inline Styles）**：微信后台会过滤外部样式表与 class 选择器，所有文字大小、行高、颜色、边距均编译为行内 `style="..."`；
- **15 套内置主题**：色值收敛在 `assets/themes/*.json`；
- **移动端 375px 视口防护**：图片宽度 100%、代码块自动换行、内边距弹性适配，严防手机端横向滚动条。

---

## 7. 阶段六：质量门禁与安全发布 (Quality Gate & Publish)

### 7.1 反 AI 味 6 维门禁量化检测
- 核心脚本：[`scripts/ai_score.py`](file:///home/white/github/wechat-publisher/scripts/ai_score.py)
- 权重分配：句长离散方差 (30%) + AI 套话词密度 (30%) + 词汇多样性 (20%) + 标点分布 (10%) + 结构对称度 (10%)；
- **熔断阈值**：
  - **< 35 分**：🟢 PASS，真人味十足，允许发布；
  - **35~45 分**：🟡 WARN，建议对命中的词句微调；
  - **$\ge$ 45 分**：🔴 FAIL，`publish.py` 强制熔断拦截，禁止推送到微信！

### 7.2 草稿箱安全发布与红线
- 核心脚本：[`scripts/publish.py`](file:///home/white/github/wechat-publisher/scripts/publish.py)
- 上传正文插图至微信 CDN，上传封面获取 `thumb_media_id`，调用微信公众平台 API 创建草稿；
- **防暗箱推送红线**：**发布接口永远仅调用微信“草稿箱（Draft）”**，绝不调用“群发（Publish）”接口。最终发布必须由人类作者在微信公众号后台扫码确认。

---

## 8. 常用执行命令速查表 (CLI Cheatsheet)

### 8.1 一键总控流水线 (`gen.py`)
```bash
# 1. 预演模式 (Dry-Run: 打印执行计划与真实命令，不调用云端生图，不推送微信，0 费用)
python3 gen.py --account main --idea "普通人如何用 AI 提升效率且避坑" --dry-run

# 2. 正式执行 (完成选题规划、封面生图、本地卡片渲染、反 AI 门禁并直推草稿箱)
python3 gen.py --account main --idea "普通人如何用 AI 提升效率且避坑" --publish

# 3. 对已有推文目录执行检查与发布
python3 gen.py --post-dir mp-articles/main/2026-10-03-ai-productivity-pitfalls --publish
```

### 8.2 单模块独立调试命令
```bash
# 重新渲染正文排版卡 (0 费用)
python3 scripts/typeset_card_gen.py \
  --data-file mp-articles/main/<slug>/cards_data.json \
  --output-dir mp-articles/main/<slug>/images

# 独立运行反 AI 味 6 维检测门禁
python3 scripts/ai_score.py mp-articles/main/<slug>/article.md --threshold 45

# 转换生成微信 HTML 本地预览文件
python3 scripts/html_converter.py mp-articles/main/<slug>/article.md \
  --theme refined-blue -o preview.html

# 手动推送到微信公众号草稿箱
python3 scripts/publish.py \
  --account main \
  --input mp-articles/main/<slug>/article.md \
  --cover mp-articles/main/<slug>/cover.jpg \
  --title "文章标题" --digest "120字以内摘要"
```
