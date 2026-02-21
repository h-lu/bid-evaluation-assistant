# AI Agent 全流程开发生命周期（Agent-first, 2026）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标与边界

本文件定义“用 Codex/Claude Code 开发本项目”的标准流程，替代传统人工周计划流程。

边界：

1. 关注流程与证据，不展开函数级代码实现。
2. 约束多 Agent 协作方式与发布门禁。
3. 与 SSOT 和专项设计文档保持一致。

## 2. 2026 实践结论（核验后）

1. 从简单可控工作流开始，避免一上来全自治多 Agent。
2. Agent 必须是可观测状态机，而非纯 Prompt 黑箱。
3. 工具契约必须标准化（输入/输出/副作用/权限）。
4. 高风险动作必须人类介入（interrupt/approval）。
5. 发布依赖 eval + trace + 回滚能力，不依赖时间节点。
6. 先建立高性能基线，再做成本优化（模型降配）。

## 3. 生命周期 Gate（0-6）

### Gate 0：任务契约定义

输入：业务目标与约束。  
输出：输入输出契约、失败定义、门禁指标。  
退出条件：任务边界和成功标准可量化。

### Gate 1：工作流设计

输入：任务契约。  
输出：状态机草图、节点职责、副作用边界、HITL 触发点。  
退出条件：可解释且可恢复。

### Gate 2：最小闭环可运行

输入：工作流设计。  
输出：`upload -> parse -> retrieve -> evaluate -> hitl -> report` 最小链路。  
退出条件：E2E 冒烟通过，trace 可串联。

### Gate 3：评估体系固化

输入：可运行闭环。  
输出：离线数据集、质量指标、预发回放脚本。  
退出条件：质量门禁可自动执行。

### Gate 4：安全与治理固化

输入：评估体系。  
输出：工具权限模型、审批流、审计与事故流程。  
退出条件：安全回归通过。

### Gate 5：灰度发布

输入：门禁通过版本。  
输出：灰度策略、告警策略、回滚剧本。  
退出条件：灰度指标稳定。

### Gate 6：运营优化

输入：线上观测数据。  
输出：漂移修复、数据回流、策略调优。  
退出条件：连续版本迭代稳定提升。

## 4. Agent 开发执行形态（Codex/Claude Code）

### 4.1 标准回路

```text
定义任务
 -> 拆分可验证子任务
 -> 并行执行
 -> 自动化评估
 -> 人工评审
 -> 合并与发布
```

### 4.2 子任务粒度

1. 每个子任务必须可在单次会话内验证。
2. 子任务必须明确输入文件与输出文件。
3. 子任务必须附验收命令或检查项。

### 4.3 并行规则

可并行：互不共享写状态的任务。  
必须串行：修改同一契约、同一状态机、同一错误码字典的任务。

## 5. Agent 与人工分工

### 5.1 Agent 负责

1. 文档/代码变更执行。
2. 测试、回归、指标对比。
3. 变更影响分析与草案。

### 5.2 人工负责

1. 需求优先级与风险裁量。
2. 高风险动作审批。
3. 发布/回滚决策。

## 6. 质量控制点

1. 变更前：契约检查。
2. 变更中：局部验证 + 回归。
3. 变更后：门禁评估 + 安全检查。
4. 发布前：灰度准入审查。

## 7. 与 superpowers 技能体系的映射

1. `brainstorming`：需求澄清与方案分解。
2. `writing-plans`：生成可执行任务计划。
3. `subagent-driven-development`：并行执行独立任务。
4. `verification-before-completion`：交付前证据验证。
5. `requesting-code-review`：合并前问题收敛。

## 8. 本项目执行清单（最小）

1. 先冻结 SSOT 与专项规范。
2. 再执行 Gate B-C 骨架与主链路打通。
3. 然后执行 Gate D 四门禁强化。
4. 最后做灰度发布与回滚演练。

## 9. 失败模式与纠偏

1. 任务粒度过大：拆分为可验证小任务。
2. 只改实现不改契约：阻断合并。
3. 指标回归但未发现：补 trace 观测与门禁用例。
4. 频繁回滚：缩小灰度范围并提高 HITL 比例。

## 10. 验收标准

1. 生命周期流程可复述且可执行。
2. 每个 Gate 都有对应证据产物。
3. 变更流程与门禁流程联动可运行。

## 11. 参考来源（核验：2026-02-21）

1. Anthropic: Building effective agents  
   https://www.anthropic.com/research/building-effective-agents/
2. OpenAI: A practical guide to building agents  
   https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
3. OpenAI Agent Builder & safety docs  
   https://platform.openai.com/docs/guides/agent-builder
4. superpowers  
   https://github.com/obra/superpowers
