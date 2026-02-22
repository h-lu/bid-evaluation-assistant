# 安全与多租户生产化规范

> 版本：v2026.02.23-r4  
> 状态：Active  
> 对齐：`docs/plans/2026-02-22-production-capability-plan.md`

## 1. 文档目标

1. 将当前测试级隔离升级为生产级“默认拒绝”安全模型。
2. 建立 API/DB/Vector/Cache/Queue/Object Storage 六层一致租户隔离。
3. 固化高风险动作审批、审计与安全阻断流程。

## 2. 范围与非目标

### 2.1 纳入范围

1. JWT 可信来源与租户注入链。
2. 租户越权阻断（接口层 + 数据层 + 检索层）。
3. 审批动作（DLQ discard、策略变更、终审）治理。
4. 日志脱敏与密钥扫描 CI 阻断。

### 2.2 非目标

1. 完整 IAM 平台改造。
2. 跨组织统一身份目录。

## 3. 当前基线（已完成）

1. 部分接口已有 `TENANT_SCOPE_VIOLATION` 阻断。
2. queue `ack/nack` 已加租户归属校验。
3. 回归用例已覆盖跨租户 queue 操作阻断。

## 4. 目标安全模型

```text
Request -> AuthN(JWT verify) -> Context inject(tenant_id,trace_id)
        -> AuthZ(scope + action) -> API handler
        -> Repository(RLS session) + Vector filter + Queue tenant-prefix
```

原则：

1. 未鉴权即拒绝。
2. 无 tenant 上下文即拒绝。
3. 无授权即拒绝。

## 5. 实施任务（执行顺序）

### 5.1 P4-S1：JWT 可信链路

输入：当前 header 注入模型。  
产出：JWT 验签 + claims 校验 + tenant 抽取。  
验收：伪造 token、缺 claim、过期 token 全阻断。

### 5.2 P4-S2：API 层授权与审计

输入：S1。  
产出：统一授权拦截器与审计中间件。  
验收：越权请求全部返回标准错误码并落审计。

### 5.3 P4-S3：DB RLS 全覆盖

输入：S2。  
产出：核心表 RLS 策略和会话 tenant 注入。  
验收：绕过 API 的 SQL 访问也无法跨租户读取。

### 5.4 P4-S4：Vector/Cache/Queue 隔离

输入：S3。  
产出：检索 metadata 强制过滤、缓存与队列 tenant 前缀。  
验收：跨租户召回、缓存污染、队列串读均为 0。

### 5.5 P4-S5：高风险动作审批

输入：S4。  
产出：双人审批策略与必填审计字段。  
验收：缺 `reviewer_id/reason/trace_id` 的高风险动作全部拒绝。

### 5.6 P4-S6：日志与密钥治理

输入：S1-S5。  
产出：日志脱敏规则与 CI 密钥扫描阻断。  
验收：扫描命中即阻断合并。

## 6. 契约与错误码约束

1. 越权统一：`TENANT_SCOPE_VIOLATION`。
2. 鉴权失败统一：`AUTH_FORBIDDEN` 或 `AUTH_UNAUTHORIZED`。
3. 高风险审批缺失统一：`APPROVAL_REQUIRED`。

## 7. 配置清单

1. `JWT_ISSUER`
2. `JWT_AUDIENCE`
3. `JWT_SHARED_SECRET`（当前实现：HS256）
4. `JWT_REQUIRED_CLAIMS`
5. `SECURITY_APPROVAL_REQUIRED_ACTIONS`
6. `SECURITY_LOG_REDACTION_ENABLED`
7. `SECURITY_SECRET_SCAN_ENABLED`

## 8. 测试与验证命令

1. 鉴权：过期、伪造、缺 claim。
2. 越权：API/DB/Vector 穿透测试。
3. 审批：高风险动作缺字段阻断。
4. 日志：脱敏检查与密钥扫描。

建议命令：

```bash
pytest -q tests/test_tenant_isolation.py tests/test_internal_outbox_queue_api.py
pytest -q tests/test_gate_d_other_gates.py
pytest -q
```

## 9. 验收证据模板

1. 越权阻断报告（按层统计）。
2. 审批覆盖率报告（目标 100%）。
3. 日志脱敏抽检报告。
4. 密钥扫描 CI 结果。

## 10. 退出条件（P4 完成定义）

1. 六层隔离策略均可验证。
2. 越权阻断项为 0。
3. 高风险动作审批覆盖率 100%。
4. 安全回归在压测并发下稳定。

## 11. 风险与回退

1. 风险：授权规则误配导致误封。
2. 风险：RLS 策略遗漏导致数据泄漏。
3. 回退：临时只读模式 + 高风险动作全冻结 + 强制人工审批。

## 12. 实施检查清单

1. [x] JWT 验签与 claim 校验生效。
2. [x] API 授权与审计生效。
3. [x] DB RLS 全量启用。
4. [x] Vector/Cache/Queue 隔离通过。
5. [x] 高风险审批与 CI 安全阻断通过。

## 13. 实施更新（2026-02-23）

1. 新增 `app/security.py`：
   - Bearer JWT（HS256）验签、`iss/aud/exp` 与必填 claim 校验。
   - JWT claim 注入 `tenant_id`，并阻断 `x-tenant-id` 伪造覆盖。
   - 安全审计日志写入（阻断类事件）与可选脱敏。
2. `app/main.py` 中间件接入 JWT 安全上下文：
   - 对 `/api/v1/*`（非 internal）启用鉴权。
   - 失败统一返回 `AUTH_UNAUTHORIZED`。
   - 租户冲突统一返回 `TENANT_SCOPE_VIOLATION`。
3. 高风险审批统一错误码 `APPROVAL_REQUIRED`：
   - `dlq_discard` 必须 `reason + reviewer_id + trace_id`。
   - `strategy_tuning_apply` 可通过 `SECURITY_APPROVAL_REQUIRED_ACTIONS` 配置为强制审批。
4. 新增密钥扫描能力：
   - `app/security_scan.py`
   - `scripts/security_secret_scan.py`
   - 可直接接入 CI 阶段阻断合并。
