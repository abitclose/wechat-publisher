# 📌 [任务编号]-[任务名称] 实施方案与交付计划

> **任务编号**：`docs/tasks/<NNN>-<name>.md`（**铁律**：三位数字编号开头，如 `001-typeset-cards-pipeline.md`；严禁带 `-plan` 后缀，严禁在文件名带 `phase-X`）  
> **所属专题**：[`docs/tasks/README.md`](README.md)（必须在任务大盘登记目录清单）  
> **任务状态**：`草稿中 (Drafting) / 待评审 (Ready for Review) / 实施中 (In Progress) / 已交付 (Completed)`  
> **涉及端与模块**：`gen.py` (主编排入口)、`scripts/` (处理脚本与工具)、`themes/` (排版主题)、`tech/` (技术文档/卡片体系)、`tests/` (自动化测试)  
> **创建时间**：YYYY-MM-DD  
> **负责人 / Agent**：[Name / Subagent]  

---

> ### 🌟 全系统任务层级与命名法定铁律 (The 3-Tier Task Standard)
> 1. **L1 专题目录（Topic Folder - 可选）**：`docs/tasks/<NNN>-<topic-name>/`
>    - 内部**必须且仅包含一个标准的 `README.md`**：仅记录简短业务背景 + 任务目录导航清单 (Task Manifest)，**严禁书写冗长设计伪代码，绝不占用数字编号位**！
> 2. **L2 任务方案文件（Task Plan）**：`<NNN>-<task-name>.md`
>    - 必须以纯数字编号开头（如 `001-typeset-cards.md`），1:1 对应 Task 1、Task 2...；
>    - **严禁带 `-plan` 后缀，严禁在文件名中使用 `phase-X` 或 `stage-X`**；
> 3. **L3 任务内执行阶段（Phases）**：
>    - 单个任务内部的最小执行、验证与代码提交颗粒度（`阶段 1 / 阶段 2 / 阶段 3`）。

---

## 🏛️ 一、 任务背景、业务目标与基线锁定 (Context, Objectives & Baseline)

### 1.1 全局工程上下文与规范引用 (SSOT 指针，严禁大段复制)
- 📖 [智能体开发规范与核心规约 (`AGENTS.md`)](file:///home/white/github/wechat-publisher/AGENTS.md)
- 📖 [任务大盘与索引导航 (`docs/tasks/README.md`)](file:///home/white/github/wechat-publisher/docs/tasks/README.md)
- 📖 [排版卡片三剑客设计体系 (`docs/typeset-cards-design-system-proposal.md`)](file:///home/white/github/wechat-publisher/docs/typeset-cards-design-system-proposal.md)

### 1.2 本次任务微观背景与痛点 (Local Context & Pain Points)
- 简述本次任务触发的具体业务场景、排版/生成痛点或工具链演进诉求（控制在 2~3 句话以内，保持高信噪比）。

### 1.3 核心交付目标 (Deliverables)
1. **交付目标 1**：[如：新增类型B对比卡与类型C清单卡渲染支持]
2. **交付目标 2**：[如：将新卡片集成进 gen.py 主流水线编排]
3. **交付目标 3**：[如：添加 --dry-run 离线模拟与全链路自动化测试，保证 100% PASS]

### 1.4 实施前 Baseline Commit ID 与分支锁定 (Baseline Locking)
- **当前仓库 (`wechat-publisher`)**：当前分支 `main` (或 `feature/<NNN>-<slug>`) | 起点 Commit ID `[Commit ID]`（用于快速 reset / diff 对账）

---

## 🔍 二、 【法定门禁】存量代码资产摸底事实表 (Codebase Grounding)

> ⚠️ **法定门禁（Iron Law）**：起草本方案前，**必须先执行代码与资产摸底**，并在下方如实贴出真实执行命令与扫描事实！严禁凭空假设“项目中没有此功能”而盲目新建重复轮子！

### 2.1 存量资产摸底日志 (Search Evidence & Audit Log)

> 💡 起草真实任务方案时，必须将以下命令中的 `<Keyword>` 替换为本次真实业务关键词，并贴出实际扫描输出结果：

1. 🐍 **Python 脚本与流水线摸底 (Python Scripts & Pipeline)**：
   ```bash
   # 检索 scripts/ 与 gen.py 中是否存在相关方法或参数
   grep -rn "<Keyword>" gen.py scripts/
   ```
2. 🚀 **Bun / TypeScript 渲染引擎摸底 (Rendering Engine)**：
   ```bash
   # 检索 TS/JS 脚本中是否存在相关渲染函数或样式生成逻辑
   find scripts/ tech/ -name "*<Keyword>*"
   grep -rn "<Keyword>" scripts/ tech/
   ```
3. 🎨 **排版主题、HTML 模板与内联样式摸底 (Themes & Styles)**：
   ```bash
   # 检索 themes/ 与 references/ 下现有排版预设
   find themes/ references/ docs/ -name "*<Keyword>*"
   ```
4. ⚙️ **配置项与环境密钥契约摸底 (Configs & Credentials)**：
   ```bash
   # 检索配置解析与相关环境变量
   grep -rn "<Keyword>" wechat-publisher.yaml.example scripts/config.py
   ```

- **实际扫描到的核心文件路径**：
  - `[文件路径 1]`：现有实现功能与定位说明
  - `[文件路径 2]`：现有实现功能与定位说明

### 2.2 现有资产能力与差距评估 (Capability Gap Analysis)
- **现有已具备能力**：列出已支持的功能、入参契约、支持的交互形态。
- **本次缺失能力**：精准列出本次需求真正需要增量补充的能力点。

### 2.3 资产复用与重构决策矩阵 (Reusability Matrix)

| 目标功能点 / 模块 | 现有资产路径 | 决策（`[ENHANCE]` 复用增强 / `[REFACTOR]` 平移重构 / `[CREATE]` 全新新建） | 决策理由（严格遵守单一可信源 SSOT，严禁重复造轮子） |
| :--- | :--- | :--- | :--- |
| 功能点 A | `scripts/...` | **`[ENHANCE]` 复用增强** | 现有脚本已具备基础结构，在其上增量扩展能力 |
| 功能点 B | `tech/...` | **`[REFACTOR]` 平移重构** | 原型文档提炼沉淀为正式脚本或模板 |
| 功能点 C | 无 | **`[CREATE]` 全新新建** | 系统此前完全不存在该资产，经摸底确认后新建 |

---

## 🏗️ 三、 单一可信源 (SSOT) 与全局架构设计 (Architecture & SSOT)

### 3.1 本次任务在发布流水线中的定位 (Pipeline Position)
- **流水线环节（单选或多选）**：
  - [ ] **A. 选题与大纲阶段 (Topic & Outline)**
  - [ ] **B. 正文撰写与 AI 生文 (Article Writing)**
  - [ ] **C. 排版卡片与视觉生成 (Typeset Cards & Visuals)**
  - [ ] **D. 主题排版渲染与内联注入 (Theme Typesetting & Inlining)**
  - [ ] **E. 微信草稿箱发布与同步 (WeChat Draft Publishing)**
  - [ ] **F. 主编排器与 CLI 工具链 (Pipeline Orchestration & CLI)**

### 3.2 物理目录落点与单一导出收敛 (Physical Scope & Exports)
- **新增/修改的核心文件**：`[填写本次改动的具体路径，如 scripts/typeset_card_gen.py 或 gen.py]`
- **单一可信出口 (SSOT)**：`[明确核心模块的统一调用入口，杜绝多处平行实现]`

### 3.3 核心数据流转、交互时序与契约设计 (Dataflow & Contracts)
- **数据流转架构图**：
  ```mermaid
  flowchart TD
      Input["用户输入 / 选题参数"] --> Orchestrator["主编排器 gen.py"]
      Orchestrator --> Writer["文章撰写模块"]
      Writer --> CardGen["排版卡片生成器"]
      CardGen --> Renderer["主题排版引擎"]
      Renderer --> Publisher["微信草稿箱发布器"]
  ```
- **契约与参数设计 (CLI & Data Contracts)**：
  - 输入参数规范（CLI 选项、环境变量、配置文件映射）；
  - 输出产物规范（产物落盘路径、中间数据格式、Markdown 标签协议）。

---

## 📋 四、 分步实施清单 (带显式操作意图标记)

> 💡 **操作意图标记说明（AI 行为锁）**：
> - **`[ENHANCE]`（增强已有）**：**文件已存在！严禁新建平行文件！** 强制用 `view_file` 查阅后使用 `replace_file_content` 做增量加固；
> - **`[REFACTOR]`（平移重构）**：保持已有功能 100% 完整的前提下，进行架构优化、模块解耦与目录归正；
> - **`[CREATE]`（全新新建）**：工程此前完全不存在的新文件，必须经过第二章摸底确认；
> - **`[COMPAT]`（兼容保护）**：检查 CLI 参数与配置项是否完全向后兼容已有脚本调用；
> - **`[CLEANUP]`（清理废弃）**：安全删除开发过程中的临时废弃文件。
> 
> ⚡ **即时验证要求（Fail-Fast）**：每完成一个关键步骤，必须立即执行对应的测试或验证命令，严禁累积错误！

### 阶段 1：底层核心脚本与数据契约扩展
- [ ] 步骤 1.1: `[CREATE]` / `[ENHANCE]` 实现底层核心功能模块
  - 🔍 即时验证: `[输入对应验证命令，如 python3 scripts/xxx.py --help]`
- [ ] 步骤 1.2: `[COMPAT]` 校验参数兼容性与异常降级分支

### 阶段 2：流水线编排接入与 CLI 参数联动
- [ ] 步骤 2.1: `[ENHANCE]` 将新能力挂载至 `gen.py` 主编排链路
- [ ] 步骤 2.2: `[COMPAT]` 支持 `--dry-run` 离线演练模式（不消耗正式 API 与生图额度）
  - 🔍 即时验证: `python3 gen.py --account test --idea "测试选题" --dry-run`

### 阶段 3：自动化测试与端到端验证
- [ ] 步骤 3.1: `[CREATE]` 编写单元测试用例
  - 🔍 即时验证: `pytest tests/test_xxx.py`
- [ ] 步骤 3.2: `[CLEANUP]` 清理临时测试产物，确保工作区干净

---

## 🔒 五、 公众号生态与安全运行门禁 (WeChat Ecosystem & Security Gates)

### 5.1 微信凭据与敏感信息防泄露门禁 (Credentials Security)
- **严禁明文硬编码**：`app_id`、`app_secret`、API Tokens 绝对禁止硬编码在任何脚本或任务文档中；
- **配置隔离**：所有密钥统一由 `wechat-publisher.yaml`（已纳入 `.gitignore`）管理，样例统一维护在 `wechat-publisher.yaml.example`；
- **Git 提交防泄露扫描**：提交前必须核对 `git status` 与 `git diff`，严禁提交任何包含真实秘钥的文件。

### 5.2 本地临时文件全封闭生命周期 (Temp File Sandboxing)
- **禁止污染系统 `/tmp`**：所有生图产物、中间 HTML、Base64 临时解码文件，**必须强制统一收敛在 `<repo>/generated/tmp/` 目录下**；
- **自愈清理机制**：流水线执行完毕（无论是成功还是异常退出），必须主动触发临时缓存的清理或安全归档，杜绝磁盘暴涨。

### 5.3 微信富文本与排版防失真门禁 (Rich Text & Mobile Viewport)
- **纯行内样式 (Inline CSS)**：输出给微信公众平台的最终 HTML 必须转换为纯 `style="..."` 行内样式，禁止依赖外部 CSS 选择器；
- **移动端 375px 断点防御**：排版卡片与容器必须在 375px 真机屏幕下表现正常，禁止横向溢出，自适应 `box-sizing: border-box`；
- **合规排版规范**：遵守微信公众平台排版限制，禁止输出非法 `<script>` 标签或外部不可信外链。

### 5.4 API 容错与配额防御 (Quotas & Error Handling)
- **接口频控与额度感知**：生图接口、草稿箱上传接口须具备超时重试与清晰的错误日志上报；
- **图片规格核验**：上传微信素材前核验图片尺寸与格式（JPG/PNG < 10MB），避免草稿箱同步失败。

---

## 🛡️ 六、 影响面分析、向下兼容与双向回滚预案 (Compatibility & Rollback)

### 6.1 现有业务影响面评估
- 是否影响已有 `gen.py` 的默认执行行为？
- 是否影响已发布的文章历史归档？

### 6.2 向下兼容策略
- CLI 参数是否提供默认值？已有调用是否可以无缝运行无需修改入参？

### 6.3 双向回滚预案 (Disaster Recovery & Rollback)
- 一旦新功能引入严重回归，执行 Git 快速止血：
  ```bash
  # 回滚到实施前的 Baseline Commit
  git reset --hard [BASELINE_COMMIT_ID]
  ```

---

## ✅ 七、 验收标准与测试回归清单 (Acceptance Criteria & Test Suite)

### 7.1 静态检查与单元测试
- [ ] 代码符合 PEP 8 / TypeScript 规范，无语法报错；
- [ ] 自动化测试全部通过：
  ```bash
  pytest tests/
  ```

### 7.2 流水线端到端 Dry-Run 离线回归
- [ ] 执行离线演练成功，完整打印各阶段日志且不调用真实消费型 API：
  ```bash
  python3 gen.py --account main --idea "回归测试选题" --dry-run
  ```

### 7.3 真机视觉排版效果验收 (Visual Regression)
- [ ] 产出的 HTML 样式在桌面浏览器与微信手机端预览均排版良好，色彩对比度合规，卡片不溢出。

---

## 📦 八、 交付物归档、架构文档与知识沉淀闭环 (Deliverables & Knowledge Sync)

### 8.1 交付物核对表 (Deliverables Checklist)
- [ ] 核心源码已落盘并就地测试通过；
- [ ] `wechat-publisher.yaml.example`（若涉及配置变更）已同步更新；
- [ ] `README.md` 或 CLI 文档（若涉及新参数）已同步说明。

### 8.2 任务大盘状态更新 (Tasks Hub Status Sync)
- [ ] 同步在 [`docs/tasks/README.md`](file:///home/white/github/wechat-publisher/docs/tasks/README.md) 中将当前任务状态刷新为 `已完成 (Completed)`。

### 8.3 经验与复盘沉淀
- [ ] 若在开发过程中遇到关键踩坑（如微信富文本解析器过滤规则、接口限制等），将排错经验与总结记录于任务文档末尾或相关技术文档中。
