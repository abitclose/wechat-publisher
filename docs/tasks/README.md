# 微信公众号文章发布器 - 研发任务大盘与索引导航 (Tasks Navigation Hub)

> 本目录收敛 `wechat-publisher` 项目的所有功能迭代、卡片生成、主题排版、流水线编排与微信生态发布治理任务（Task）。
> 遵循统一的 **三级任务法定标准** 与 **任务全生命周期规约** 进行闭环管理。

---

## 一、 进行中活跃任务 (Active Tasks)

| 任务编号 | 任务主题 / 方案路径 | 核心涉及模块 | 核心目标 | 当前状态 |
| :--- | :--- | :--- | :--- | :--- |
| **Task 001** | [`001-typeset-cards-three-archetypes-and-rendering-pipeline.md`](001-typeset-cards-three-archetypes-and-rendering-pipeline.md) | `scripts/` / `tech/` / `themes/` / `gen.py` | 落地排版卡片“三剑客”（金句卡、对比卡、清单卡）生成与渲染引擎并接入主流水线 | 已交付待验收 (Ready for User Acceptance) |
| **Task 002** | [`002-contrast-card-vertical-stack-redesign.md`](002-contrast-card-vertical-stack-redesign.md) | `assets/` / `scripts/` / `tests/` | 移动端友好型对比卡重构：由左右分栏升级为上下流式堆叠，实现非对称光影、骨架词胶囊与自适应高度 | 已完成 (Completed) |

---

## 二、 需求草案与待立项方案 (Draft Proposals)

| 草案文件 / 主题 | 业务领域 | 说明与目标 |
| :--- | :--- | :--- |
| [排版卡片三剑客设计体系提案](../typeset-cards-design-system-proposal.md) | 排版与视觉设计 | 金句卡、对比卡、清单卡的视觉规范、HTML/CSS 结构与生成参数规范草案 |
| [首篇发布实战复盘与成本核算](../case-study-first-published-post.md) | 业务案例与成本 | 首次端到端发布实测数据、API 消耗核算与流水线优化建议 |

---

## 三、 历史已完成任务归档库 (Archived Tasks)

> 所有已验收、实测通过并交付的历史任务方案均归档至 [`docs/tasks/archive/`](archive/) 目录，完整保留所有技术设计决策与代码变更依据。

- 详见归档目录：[`docs/tasks/archive/`](archive/)
- 暂无已归档任务（项目处于快速演进初期）。

---

## 四、 任务编写规范与模板

编写新任务时，请严格参考规范模板：
- 标准任务模板：[`TEMPLATE-TASK.md`](TEMPLATE-TASK.md)
- 智能体任务技能：[`.agents/skills/task-lifecycle-management/SKILL.md`](../../.agents/skills/task-lifecycle-management/SKILL.md)
