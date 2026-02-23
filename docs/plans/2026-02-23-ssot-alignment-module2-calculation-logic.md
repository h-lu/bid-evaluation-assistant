# SSOT 对齐 - 模块 2：计算逻辑

> 版本：v1.0
> 状态：Implemented
> 日期：2026-02-23
> 分支：`codex/ssot-alignment`
> 对齐：`docs/design/2026-02-21-retrieval-and-scoring-spec.md` §8.3, §9

## 1. 目标

1. 实现真实 `retrieval_agreement` 计算（当前用 `citation_coverage` 替代）
2. ~~实现 `score_deviation_pct` HITL 触发条件~~ ✅ 已存在

## 2. 发现

经代码审查发现：
- `score_deviation_pct` 已在 `store.py:863` 实现
- HITL 触发条件 `score_deviation_pct > 20.0` 已在 `store.py:868` 实现
- **只需修复 `retrieval_agreement` 计算**

## 3. 实现内容

### 3.1 新增 `_calculate_retrieval_agreement()` 方法

```python
def _calculate_retrieval_agreement(self, chunk_ids: list[str]) -> float:
    """
    计算检索一致性 (retrieval_agreement)。

    基于引用来源的 score_raw 分布计算：
    - 如果所有 citation 的 score_raw 都较高且接近，认为一致性好
    - 如果 score_raw 分散，认为一致性差

    Returns:
        float: 0.0 ~ 1.0
    """
    # 计算变异系数 (CV = std / mean)
    # CV 越小，一致性越高
    # CV=0 → agreement=1.0, CV>=1 → agreement=0.0
```

### 3.2 修改置信度计算

```python
# 修改前
retrieval_agreement = citation_coverage

# 修改后
retrieval_agreement = self._calculate_retrieval_agreement(citations_all)
```

## 4. 验收标准

1. ✅ `retrieval_agreement` 不再等于 `citation_coverage`
2. ✅ 所有测试通过 (240 passed)
