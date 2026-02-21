# AGENTS.md

本文件定义在本仓库中运行的通用 Agent 执行规范（Codex/兼容代理）。

## 1. 目标

1. 让 Agent 执行流程可预测、可审计、可回滚。
2. 让文档驱动开发（docs-first）在本项目稳定落地。
3. 降低提示注入、越权工具调用、误改文档结构等风险。

## 2. 范围与优先级

1. 适用于本仓库所有目录。
2. 若子目录存在更具体的 Agent 规范，子目录优先。
3. 系统/平台级安全限制始终高于本文件。

## 3. 执行流程（必须）

```text
读取任务 -> 定位相关文档与约束 -> 形成最小实现计划
-> 执行改动 -> 运行验证 -> 输出证据 -> 再声明完成
```

硬要求：

1. 未验证不得宣称“完成/通过”。
2. 先改文档契约，再改实现（本仓库当前以文档为主）。
3. 破坏性操作必须显式确认并记录理由。

## 4. 文档驱动规则

1. SSOT：`docs/plans/2026-02-21-end-to-end-unified-design.md`。
2. 实施顺序：`docs/design/2026-02-21-implementation-plan.md` 的 Gate A-F。
3. 任何新增设计必须同步更新对应专项文档。
4. 图示统一使用 ASCII，不使用 mermaid。

## 5. 官方最佳实践（对齐结论）

以下条款来自官方文档与 Context7 核验后的统一结论：

1. LangGraph：
   - 使用 checkpointer 时必须携带 `thread_id`。
   - HITL 使用 `interrupt`/`Command(resume=...)`。
   - 中断负载需 JSON 可序列化。
2. LangChain：
   - Agent 输出优先结构化（`ToolStrategy`/`ProviderStrategy`）。
   - 工具调用需显式 schema 约束。
3. FastAPI：
   - 长任务接口返回 `202 + job_id`。
   - 复杂长任务由外部 worker 执行，API 仅受理与状态查询。
4. OpenAI Agent Builder/AgentKit：
   - 先定义工作流与 typed edges，再发布版本。
   - 发布前执行 eval/trace grading 与安全检查。
5. OpenAI Agent Safety：
   - 不把不可信输入注入高优先级系统指令。
   - 用结构化输出限制数据流，并保留人工审批节点。

## 6. 工具与安全

1. 默认最小权限。
2. 外网检索优先官方来源与主文档（official docs/repo）。
3. 高风险动作（删除、终审、丢弃）必须二次确认策略。
4. 禁止把密钥、token、敏感配置写入仓库。

## 7. 提交前检查（最小）

1. 文档引用存在性检查通过。
2. 无 `TODO/TBD/recovered/mermaid` 残留。
3. 术语一致：状态机、错误码、租户字段、HITL 字段。
4. 变更与目标一致，且有可读变更摘要。

## 8. 推荐知识源

1. OpenAI Docs MCP：`https://developers.openai.com/mcp`
2. OpenAI Agent Builder/AgentKit 文档。
3. LangGraph/LangChain/FastAPI 官方文档。
4. Anthropic Claude Code 官方文档（若任务涉及 Claude 协作）。
