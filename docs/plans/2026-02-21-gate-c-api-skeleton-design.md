# Gate C API Skeleton Design

> 版本：v2026.02.21-r1  
> 状态：Active  
> 对齐：`docs/design/2026-02-21-implementation-plan.md`

## 1. 目标

在当前“文档仓库”内落一个可运行的最小 FastAPI 骨架，承接 Gate B 契约，提供：

1. `202 + job_id` 的异步受理接口。
2. `jobs` 状态查询接口（含状态机字段）。
3. HITL 恢复接口（`resume_token`）。
4. citation 回跳查询接口。

## 2. 约束

1. 先测试后实现（TDD）。
2. 仅做最小实现，不引入真实外部依赖（DB/队列/向量库）。
3. 保持字段与 `docs/design/2026-02-21-openapi-v1.yaml` 一致。
4. 不做“自动终审”行为，只实现契约层骨架。

## 3. 方案比较

### 方案 A：内存状态存储（推荐）

1. FastAPI + 进程内字典保存 jobs、idempotency、citations。
2. 用纯接口测试验证契约行为。
3. 优点：实现快、测试稳定、适合 Gate C 最小闭环。
4. 缺点：重启丢状态，不适用于生产。

### 方案 B：SQLite 本地持久化

1. 增加 SQLModel/SQLAlchemy 与迁移。
2. 优点：更贴近生产数据形态。
3. 缺点：超出当前“最小骨架”范围，增加复杂度。

### 方案 C：直接引入 PostgreSQL + Redis

1. 一步到位接近目标架构。
2. 优点：架构一致性高。
3. 缺点：搭建与运维成本高，不符合当前阶段速度目标。

## 4. 设计结论

采用方案 A：内存状态存储骨架。

1. 先保证契约正确和状态机字段完整。
2. 后续 Gate C/C+ 再把存储实现替换成 PostgreSQL/Redis。
3. 通过 TDD 锁定接口行为，避免后续替换时语义漂移。

## 5. 验收切面

1. 写接口都要求 `Idempotency-Key`。
2. 所有响应都有 `meta.trace_id`。
3. 异步接口返回 `202` 且含 `job_id`。
4. 关键错误码可触发：`IDEMPOTENCY_MISSING`、`IDEMPOTENCY_CONFLICT`、`WF_INTERRUPT_RESUME_INVALID`。
5. `GET /jobs/{job_id}` 返回状态机允许状态集合。
