# SSOT 对齐 - 模块 3：工作流状态

> 版本：v1.0
> 状态：Implemented
> 日期：2026-02-23
> 分支：`codex/ssot-alignment`
> 对齐：`docs/design/2026-02-21-langgraph-agent-workflow-spec.md` §2

## 1. 目标

补齐工作流状态对象字段，对齐 SSOT 规范。

## 2. SSOT 要求

### 2.1 状态对象结构（langgraph-agent-workflow-spec §2）

```yaml
identity:
  tenant_id, project_id, evaluation_id, supplier_id
trace:
  trace_id, thread_id, checkpoint_id
inputs:
  query_bundle        # ❌ 缺失
  rule_pack_version   # ⚠️ 在 payload 中，需提升
retrieval:
  retrieved_chunks[]  # ❌ 缺失
  evidence_bundle     # ❌ 缺失
scoring:
  criteria_scores, total_score, confidence, citation_coverage
review:
  requires_human_review, human_review_payload, human_decision, resume_token
output:
  report_payload, status
runtime:
  retry_count
  errors[]            # ❌ 只有 last_error
```

## 3. 当前实现（需修复）

### 3.1 workflow_checkpoints 结构

```python
# store.py:1580-1589
checkpoint = {
    "checkpoint_id": str,
    "thread_id": str,
    "job_id": str,
    "seq": int,
    "node": str,
    "status": str,
    "payload": dict,
    "tenant_id": str,
    "created_at": str,
}
```

### 3.2 job 结构

```python
# 当前 job 结构
{
    "job_id": str,
    "job_type": str,
    "status": str,
    "retry_count": int,
    "thread_id": str,
    "trace_id": str,
    "resource": dict,
    "payload": dict,
    "last_error": dict | None,  # ⚠️ 单个 error，应为数组
}
```

## 4. 修改方案

### 4.1 新增 `get_workflow_state()` 方法

返回符合 SSOT 的完整工作流状态对象：

```python
def get_workflow_state(self, *, evaluation_id: str, tenant_id: str) -> dict[str, Any] | None:
    """
    获取工作流状态对象（对齐 SSOT langgraph-agent-workflow-spec §2）。
    """
    report = self.get_evaluation_report_for_tenant(evaluation_id=evaluation_id, tenant_id=tenant_id)
    if report is None:
        return None

    job = self._find_job_by_evaluation_id(evaluation_id=evaluation_id, tenant_id=tenant_id)
    checkpoints = self.list_workflow_checkpoints(thread_id=report.get("thread_id", ""), tenant_id=tenant_id)

    # 从 checkpoints 提取 retrieval 信息
    retrieved_chunks = self._extract_retrieved_chunks(checkpoints)
    evidence_bundle = self._extract_evidence_bundle(checkpoints)

    return {
        "identity": {
            "tenant_id": tenant_id,
            "project_id": report.get("project_id"),
            "evaluation_id": evaluation_id,
            "supplier_id": report.get("supplier_id"),
        },
        "trace": {
            "trace_id": report.get("trace_id"),
            "thread_id": report.get("thread_id"),
            "checkpoint_id": checkpoints[-1].get("checkpoint_id") if checkpoints else None,
        },
        "inputs": {
            "query_bundle": self._extract_query_bundle(checkpoints),
            "rule_pack_version": report.get("rule_pack_version"),
        },
        "retrieval": {
            "retrieved_chunks": retrieved_chunks,
            "evidence_bundle": evidence_bundle,
        },
        "scoring": {
            "criteria_scores": report.get("criteria_results", []),
            "total_score": report.get("total_score"),
            "confidence": report.get("confidence"),
            "citation_coverage": report.get("citation_coverage"),
        },
        "review": {
            "requires_human_review": report.get("needs_human_review"),
            "human_review_payload": report.get("interrupt"),
            "human_decision": None,  # 恢复后填充
            "resume_token": report.get("interrupt", {}).get("resume_token"),
        },
        "output": {
            "report_payload": report,
            "status": job.get("status") if job else None,
        },
        "runtime": {
            "retry_count": job.get("retry_count", 0) if job else 0,
            "errors": self._collect_errors(job, checkpoints),
        },
    }
```

### 4.2 新增辅助方法

```python
def _extract_query_bundle(self, checkpoints: list[dict]) -> dict[str, Any] | None:
    """从 checkpoints 提取查询包"""
    for cp in checkpoints:
        if cp.get("node") == "load_context":
            return cp.get("payload", {}).get("query_bundle")
    return None

def _extract_retrieved_chunks(self, checkpoints: list[dict]) -> list[dict[str, Any]]:
    """从 checkpoints 提取召回的 chunks"""
    for cp in checkpoints:
        if cp.get("node") == "retrieve_evidence":
            return cp.get("payload", {}).get("retrieved_chunks", [])
    return []

def _extract_evidence_bundle(self, checkpoints: list[dict]) -> dict[str, Any] | None:
    """从 checkpoints 提取证据包"""
    for cp in checkpoints:
        if cp.get("node") == "retrieve_evidence":
            return cp.get("payload", {}).get("evidence_bundle")
    return None

def _collect_errors(self, job: dict | None, checkpoints: list[dict]) -> list[dict[str, Any]]:
    """收集所有错误信息"""
    errors = []
    if job and job.get("last_error"):
        errors.append(job["last_error"])
    for cp in checkpoints:
        if cp.get("status") == "error" and cp.get("payload", {}).get("error"):
            errors.append(cp["payload"]["error"])
    return errors
```

### 4.3 修改 job 结构（向后兼容）

```python
# 新增 errors 数组，保留 last_error 向后兼容
{
    ...
    "last_error": dict | None,  # 保留，最新错误
    "errors": list[dict],       # 新增，所有错误历史
}
```

### 4.4 修改 `create_evaluation_job()`

在创建 job 时初始化 `errors` 数组：

```python
job = {
    ...
    "last_error": None,
    "errors": [],  # 新增
}
```

### 4.5 修改错误处理逻辑

当发生错误时，同时更新 `last_error` 和 `errors`：

```python
job["last_error"] = error_info
job.setdefault("errors", []).append(error_info)
```

## 5. 影响范围

### 5.1 修改文件

| 文件 | 修改行数（估） |
|------|---------------|
| `app/store.py` | ~100 行 |
| `app/main.py` | 新增 API 端点（可选） |

### 5.2 API 兼容性

| 影响 | 说明 |
|------|------|
| **非 Breaking** | 新增方法和字段，不改变现有结构 |
| 新增 `errors` 字段 | job 结构扩展 |

## 6. 验收标准

1. `get_workflow_state()` 返回完整 SSOT 结构
2. `errors` 数组记录所有错误历史
3. `inputs.query_bundle` 可从 checkpoints 提取
4. `retrieval.retrieved_chunks` 可从 checkpoints 提取
5. 所有测试通过
