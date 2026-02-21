# 安全设计规范

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 安全目标

1. 零跨租户越权。
2. 关键动作全审计可追溯。
3. Agent 工具调用可控且最小权限。
4. 证据与报告满足留存与法律保全要求。

## 2. 威胁模型

1. API 越权与令牌滥用。
2. Worker 丢失租户上下文造成误处理。
3. 检索缺少过滤导致跨租户召回。
4. 高风险动作绕过审批。
5. Prompt 注入诱导工具越权调用。

## 3. 认证与授权

### 3.1 认证

1. JWT access token（短时）+ refresh token（HttpOnly Cookie）。
2. refresh 接口启用 CSRF 防护。
3. 支持 token 撤销与黑名单。

### 3.2 授权

1. RBAC：`admin/agent/evaluator/viewer`。
2. ABAC：高风险动作附加资源与审批条件。
3. 默认拒绝：未显式允许即拒绝。

## 4. 多租户隔离控制

### 4.1 API 层

1. `tenant_id` 只从 JWT 注入。
2. 拒绝客户端提交 `tenant_id`。
3. 所有资源访问二次校验资源租户归属。

### 4.2 数据层

1. 核心表全量 `tenant_id` + RLS。
2. 会话设置 `app.current_tenant`。
3. 无租户上下文查询一律拒绝。

### 4.3 检索层

1. 向量查询必须附 `tenant_id + project_id` 过滤。
2. 无过滤查询直接拒绝并告警。

### 4.4 缓存与队列层

1. Redis key 强制 tenant 前缀。
2. job payload 强制包含 tenant 上下文。
3. Worker 执行前二次验证 tenant 一致性。

## 5. Agent 工具安全

1. 工具分级：`read_only/state_write/external_commit`。
2. 高风险工具调用必须有人审或双人复核。
3. 工具输入做 schema 校验与 allowlist 校验。
4. 工具调用结果写审计日志。

## 6. Prompt 注入防护

1. 上下文分层：系统指令 > 业务规则 > 用户输入。
2. 对外部文档内容启用“非可信指令”标记。
3. 禁止模型根据文档文本直接提升权限。
4. 高风险动作必须通过显式工具调用，不接受纯文本隐式提交。

## 7. 数据保护

1. 传输：TLS 1.2+。
2. 存储：数据库、备份、对象存储均加密。
3. 密钥：集中管理，定期轮换（90 天）。
4. 日志脱敏：证件号、手机号、token、密钥字段脱敏。

## 8. 审计与保全

1. 高风险动作审计覆盖率 100%。
2. 审计字段至少含：`actor/action/resource/trace_id/reason`。
3. legal hold 对象禁止自动删除。
4. 报告归档进入 WORM 存储。

## 9. 安全测试要求

1. 租户越权测试（API + DB + retrieval）。
2. 权限绕过测试（角色与审批链）。
3. token 重放与失效测试。
4. Prompt 注入回归测试。

## 10. 应急与回滚

1. 发现越权风险立即触发 P0：关闭相关写接口。
2. 开启只读降级保障可查询能力。
3. 恢复前必须完成根因分析与补丁验证。

## 11. 验收标准

1. 跨租户访问事件为 0。
2. 高风险动作无审计缺口。
3. legal hold 对象无违规删除。
4. 安全回归全通过。

## 12. 参考来源（核验：2026-02-21）

1. FastAPI security docs: https://fastapi.tiangolo.com/
2. OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
