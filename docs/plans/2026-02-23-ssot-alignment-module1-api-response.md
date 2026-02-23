# SSOT 对齐 - 模块 1：API 响应结构

> 版本：v1.0
> 状态：Draft
> 日期：2026-02-23
> 分支：`codex/ssot-alignment`
> 对齐：`docs/design/2026-02-21-retrieval-and-scoring-spec.md` §11

## 1. 目标

将 API 响应中的 `citations` 字段从 ID 列表改为完整对象，严格对齐 SSOT 规范。

## 2. SSOT 要求

### 2.1 报告级 citations（retrieval-and-scoring-spec §11）

```json
{
  "citations": [
    {
      "chunk_id": "ck_xxx",
      "page": 8,
      "bbox": [120.2, 310.0, 520.8, 365.4],
      "quote": "原文片段..."
    }
  ]
}
```

### 2.2 criteria_results.citations（rest-api-specification §5.12）

```json
{
  "criteria_results": [
    {
      "criteria_id": "delivery",
      "citations": [
        {
          "chunk_id": "ck_xxx",
          "page": 8,
          "bbox": [120.2, 310.0, 520.8, 365.4]
        }
      ]
    }
  ]
}
```

### 2.3 移除多余字段

| 字段 | 位置 | 原因 |
|------|------|------|
| `weight` | `criteria_results[]` | SSOT 无此字段，weight 应只在规则包中 |
| `citations_count` | `criteria_results[]` | SSOT 无此字段，可从 citations.length 获取 |

## 3. 当前实现（需修复）

### 3.1 报告级 citations

```python
# store.py:1367
"citations": report["citations"],  # 返回 ["ck_xxx", "ck_yyy"]
```

### 3.2 criteria_results.citations

```python
# store.py:795-796
"citations": citations,           # 返回 ["ck_xxx"]
"citations_count": len(citations), # 多余字段
```

```python
# store.py:788
"weight": weight,  # 多余字段
```

## 4. 修改方案

### 4.1 新增 `_resolve_citation()` 方法

```python
def _resolve_citation(self, chunk_id: str) -> dict[str, Any]:
    """
    将 chunk_id 解析为完整 citation 对象。

    Returns:
        {
            "chunk_id": str,
            "page": int | None,
            "bbox": list[float] | None,
            "quote": str | None
        }
    """
    source = self.citation_sources.get(chunk_id)
    if source is None:
        return {
            "chunk_id": chunk_id,
            "page": None,
            "bbox": None,
            "quote": None,
        }
    return {
        "chunk_id": chunk_id,
        "page": source.get("page"),
        "bbox": source.get("bbox"),
        "quote": source.get("text"),
    }
```

### 4.2 新增 `_resolve_citations_batch()` 方法

```python
def _resolve_citations_batch(self, chunk_ids: list[str]) -> list[dict[str, Any]]:
    """
    批量解析 chunk_id 列表为 citation 对象列表。
    """
    return [self._resolve_citation(cid) for cid in chunk_ids]
```

### 4.3 修改 `get_evaluation_report_for_tenant()`

**位置**：`store.py:1359-1372` (InMemoryStore) 和 `store.py:4552-4564` (PostgresBackedStore)

```python
# 修改前
"citations": report["citations"],

# 修改后
"citations": self._resolve_citations_batch(report.get("citations", [])),
```

### 4.4 修改 `criteria_results` 生成

**位置**：`store.py:780-798`

```python
# 修改前
criteria_results.append({
    ...
    "citations": citations,
    "citations_count": len(citations),
    "weight": weight,
})

# 修改后
criteria_results.append({
    "criteria_id": criteria_id,
    "criteria_name": str(criteria_name),
    "requirement_text": str(requirement_text) if requirement_text is not None else None,
    "response_text": str(response_text) if response_text is not None else None,
    "score": score,
    "max_score": max_score,
    "hard_pass": hard_constraint_pass,
    "reason": ...,
    "citations": self._resolve_citations_batch(citations),
    "confidence": 0.81 if hard_constraint_pass else 1.0,
})
```

### 4.5 修改报告级 citations 生成

**位置**：`store.py:894` 附近

```python
# 修改前
"citations": citations_all,

# 修改后
"citations": self._resolve_citations_batch(citations_all),
```

## 5. 影响范围

### 5.1 修改文件

| 文件 | 修改行数（估） |
|------|---------------|
| `app/store.py` | ~50 行 |

### 5.2 测试更新

| 测试文件 | 修改内容 |
|---------|---------|
| `tests/test_evaluation_report.py` | 断言改为检查 citation 对象结构 |
| `tests/test_resume_and_citation.py` | 同上 |
| 其他引用 `citations` 的测试 | 同上 |

### 5.3 API 兼容性

| 影响 | 说明 |
|------|------|
| **Breaking Change** | `citations` 从 `list[str]` 改为 `list[dict]` |
| 前端影响 | 需要更新 citation 渲染逻辑 |
| 集成测试 | 需要更新断言 |

## 6. 验收标准

1. `GET /evaluations/{evaluation_id}/report` 返回的 `citations` 为对象数组
2. `criteria_results[].citations` 为对象数组
3. `criteria_results[]` 不包含 `weight` 和 `citations_count` 字段
4. 所有测试通过
5. citation 对象包含 `chunk_id`, `page`, `bbox`, `quote` 四个字段

## 7. 回滚方案

如需回滚：
1. `git revert <commit>`
2. 恢复 `citations` 为 ID 列表格式

## 8. 后续步骤

完成模块 1 后，继续：
- 模块 2：计算逻辑（`retrieval_agreement`, `score_deviation_pct`）
- 模块 3：工作流状态（`query_bundle`, `retrieved_chunks`, `errors[]`）
