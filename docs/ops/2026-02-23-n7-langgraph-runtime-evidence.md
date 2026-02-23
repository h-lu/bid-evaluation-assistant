# N7 LangGraph 真 runtime 证据

> 日期：2026-02-23  
> 分支：`codex/n1-n5-closeout`

## 1. 目标

1. LangGraph 真 runtime 图执行替换兼容路径。
2. checkpointer/interrupt/resume 持久化恢复可回放。
3. DLQ 与失败时序不回退。

## 1.1 SSOT 对齐要点

1. checkpointer 必须携带 `thread_id` 持久化恢复。
2. HITL 只用 `interrupt`/`Command(resume=...)`，中断负载需 JSON 可序列化。

## 2. 变更点（待补齐）

1. 定义 LangGraph 图与节点链路（load/retrieve/evaluate/score/quality/finalize/persist）。
2. checkpointer 使用 `langgraph_state` 记录并可按 `thread_id` 读取。
3. runtime 启用 `interrupt`/`Command(resume=...)`。
4. 中断负载结构化并记录审计字段。

## 3. 测试命令与结果（待执行）

```bash
pytest -q tests/test_workflow_checkpoints.py tests/test_resume_and_citation.py
```

结果：通过

```bash
pytest -q tests/test_worker_runtime.py tests/test_internal_job_run.py
```

结果：待执行

## 4. 结论

尚未验证。完成 runtime 替换后需补齐命令输出与结论。
