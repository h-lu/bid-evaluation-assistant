# Gate F 运行优化验收清单

> 版本：v2026.02.22-r1  
> 状态：Active  
> 对齐：`docs/design/2026-02-21-implementation-plan.md`

## 1. 目标

1. 将 Gate F 的数据回流与策略优化落为可执行、可回归接口。
2. 形成“数据集版本演进 + 策略版本演进”的双轨证据。
3. 为后续连续迭代提供最小运维优化基线。

## 2. F-1 数据回流

接口：`POST /api/v1/internal/ops/data-feedback/run`

必做项：

1. DLQ 样本回流到反例集。
2. 人审改判样本回流到黄金集候选。
3. 每次执行都更新评估数据集版本号。

验收断言：

1. `counterexample_added >= 0`
2. `gold_candidates_added >= 0`
3. `dataset_version_after != dataset_version_before`

证据测试：`tests/test_gate_f_ops_optimization.py`（data feedback 场景）

## 3. F-2 策略优化

接口：`POST /api/v1/internal/ops/strategy-tuning/apply`

必做项：

1. selector 阈值与规则可调整。
2. 评分校准参数可调整。
3. 工具权限与审批策略可调整。

验收断言：

1. 返回 `strategy_version` 且版本递增。
2. 返回体中的 selector/calibration/tool_policy 与输入一致。

证据测试：`tests/test_gate_f_ops_optimization.py`（strategy tuning 场景）

## 4. 内部接口约束

1. Gate F 两个接口都必须携带 `x-internal-debug: true`。
2. 未携带内部标识统一返回 `403 + AUTH_FORBIDDEN`。
3. 非法入参统一返回 `400 + REQ_VALIDATION_FAILED`。

## 5. 契约同步范围

1. `docs/design/2026-02-21-rest-api-specification.md`
2. `docs/design/2026-02-21-openapi-v1.yaml`
3. `docs/design/2026-02-21-api-contract-test-samples.md`

## 6. 运行验证证据

1. 运行命令：`pytest -v`
2. OpenAPI 解析：`openapi=3.1.0`
3. 文档禁词检查：占位词与非约定图示关键字不得出现
4. 文档引用检查：显式引用路径全部存在

当前分支验证结果（2026-02-22）：

1. `pytest -q` 退出码 `0`
2. Gate F 新增用例 `tests/test_gate_f_ops_optimization.py` 通过
3. OpenAPI 新增 Gate F 两个内部路径存在并可解析

## 7. 结论判定

同时满足以下条件可判定 Gate F 通过：

1. 数据回流可执行且每轮都能产出新数据集版本号。
2. 策略优化可执行且每轮都能产出新策略版本号。
3. Gate F 接口具备稳定的鉴权与回归用例覆盖。
