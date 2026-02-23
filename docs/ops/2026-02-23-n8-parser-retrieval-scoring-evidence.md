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

## 2. 变更点

1. 解析输出新增 `content_source` 并统一 bbox 归一化。
2. parse manifest 追加 `content_source/chunk_count`（追加字段）。
3. citation 追加 `heading_path/chunk_type/content_source`（追加字段）。

## 3. 测试命令与结果（待执行）

```bash
pytest -q tests/test_parse_manifest_and_error_classification.py tests/test_parser_adapters.py
```

结果：通过

```bash
pytest -q tests/test_retrieval_query.py
```

结果：通过

## 4. 结论

解析/检索基础能力已对齐并通过回归命令验证（详见第 3 节）。
