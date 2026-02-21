# AI Agent 工具治理与互操作规范（2026）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 工具调用可控：权限、审批、限流、回滚明确。
2. 工具调用可追溯：输入、输出、副作用全记录。
3. 工具接入可扩展：支持 MCP 与 A2A 协作。

## 2. 工具契约模型（必须）

每个工具必须文档化以下字段：

1. `name`
2. `description`
3. `input_schema`（JSON Schema）
4. `output_schema`
5. `side_effect_level`（`read_only/state_write/external_commit`）
6. `idempotency_policy`
7. `timeout/retry_policy`
8. `owner`
9. `risk_level`

无契约工具不得进入生产工作流。

## 3. 权限分级

1. `L0`：只读查询（默认可用）
2. `L1`：租户内写操作（角色授权）
3. `L2`：高风险写操作（二次确认）
4. `L3`：外部提交/删除（双人复核）

## 4. 高风险动作清单（本项目）

1. 终审发布。
2. DLQ discard。
3. legal hold 解除。
4. 外部系统正式提交。

要求：

1. 必填 `reason`。
2. 操作人与复核人分离。
3. 全量审计可追溯。

## 5. 运行时安全控制

1. 工具输入做 schema + allowlist 校验。
2. 工具调用超时、重试、断路器策略统一。
3. 高风险工具可被 feature flag 一键关闭。
4. 工具异常统一映射错误码。

## 6. Prompt 注入与越权防护

1. 文档内容视为非可信输入。
2. 禁止模型通过自然语言直接触发高风险副作用。
3. 高风险副作用必须走受控工具调用路径。
4. 工具调用前执行“权限 + 上下文 + 审批”三重校验。

## 7. MCP / A2A 互操作策略

### 7.1 MCP 使用边界

用于接入企业系统能力（知识库、审批、日志等）：

1. 每个 MCP 服务声明最小权限。
2. 会话隔离，禁止跨租户上下文复用。
3. 工具响应必须可审计。

### 7.2 A2A 使用边界

用于跨 Agent/跨组织任务协同：

1. 明确任务状态与责任边界。
2. 异步交付必须有回执与超时策略。
3. 不可信外部 Agent 输出需二次校验。

## 8. 审计要求

每次工具调用记录：

1. `trace_id`
2. `tenant_id`
3. `agent_id`
4. `tool_name`
5. `risk_level`
6. `input_hash`
7. `result_summary`
8. `status`
9. `latency_ms`

## 9. 发布门禁（工具变更）

1. 工具 schema 变更需契约回归。
2. 高风险工具变更需安全评审。
3. 互操作变更需灰度验证。
4. 所有变更必须有回滚策略。

## 10. 本项目最小落地清单

1. 工具注册表与风险分级表。
2. 高风险动作审批拦截器。
3. 工具调用审计中间件。
4. MCP 接入安全基线。
5. A2A 外部结果校验器。

## 11. 验收标准

1. 所有生产工具均有完整契约。
2. 高风险动作无审批不可执行。
3. 工具调用链路可完整追溯。

## 12. 参考来源（核验：2026-02-21）

1. Model Context Protocol: https://modelcontextprotocol.io/
2. Google A2A protocol: https://google.github.io/A2A/
3. LangChain/LangGraph docs: https://docs.langchain.com/
