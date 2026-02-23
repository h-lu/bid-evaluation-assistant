# N8 解析/检索/评分深度实现证据

> 日期：2026-02-23  
> 分支：`codex/n1-n5-closeout`

## 1. 目标

1. 解析链路字段对齐 SSOT（page/bbox/heading_path/chunk_type）。
2. 检索与评分策略可配置并可回放。
3. 引用覆盖与置信度触发 HITL 一致。

## 1.1 SSOT 对齐要点

1. `content_list.json` 为定位真值，`full.md` 为结构真值。
2. bbox 归一化为 `[x0,y0,x1,y1]`，引用对象含 `page,bbox,heading_path,chunk_type`。
3. HITL 触发条件需满足 `score_confidence/citation_coverage/score_deviation_pct` 规则。

## 2. 变更点（待补齐）

1. 解析器输出字段校验与入库一致化。
2. 检索与评分策略参数化与审计化。
3. 评分项引用覆盖验证与回放脚本。
4. 引用对象结构化输出与前端回跳字段一致化。

## 3. 测试命令与结果（待执行）

```bash
pytest -q tests/test_parse_router_selection.py tests/test_parse_manifest_and_error_classification.py
```

结果：待执行

```bash
pytest -q tests/test_retrieval_query.py tests/test_quality_gate_evaluation.py
```

结果：待执行

## 4. 结论

尚未验证。完成深度实现后需补齐命令输出与结论。
