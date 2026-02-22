# True Stack 强约束证据（P6+）

> 日期：2026-02-23  
> 分支：`codex/p6-release-admission`

## 1. 目标

1. `staging/prod` 禁止静默回退到 `memory/sqlite`。
2. store/queue 初始化必须使用 `postgres + redis` 真栈。

## 2. 变更点

1. 新增 `BEA_REQUIRE_TRUESTACK` 运行时开关（默认 `false`）。
2. `create_store_from_env`：当该开关为 `true` 时，仅允许 `BEA_STORE_BACKEND=postgres`。
3. `create_queue_from_env`：当该开关为 `true` 时，仅允许 `BEA_QUEUE_BACKEND=redis`。
4. API queue 初始化：当该开关为 `true` 时，queue 初始化失败直接报错，不再回退到 `InMemoryQueueBackend`。

## 3. 测试命令与结果

```bash
pytest -q tests/test_store_persistence_backend.py::test_store_factory_rejects_non_postgres_when_true_stack_required tests/test_queue_backend.py::test_queue_factory_rejects_non_redis_when_true_stack_required tests/test_runtime_queue_fallback.py
```

结果：通过

```bash
pytest -q tests/test_store_persistence_backend.py tests/test_queue_backend.py tests/test_health.py tests/test_runtime_queue_fallback.py
```

结果：通过

## 4. 结论

1. 真栈强约束已具备可回归测试证据。
2. `staging/prod` 可通过配置禁止回退路径，降低误配置导致的伪生产运行风险。
