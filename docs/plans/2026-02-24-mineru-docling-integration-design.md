# MinerU/Docling 解析器集成设计

> 版本：v2026.02.24-r2
> 状态：Draft
> 对齐：`docs/design/2026-02-21-mineru-ingestion-spec.md`、`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 实现 MinerU/Docling/OCR 三层解析器服务
2. MinerU 支持官方 API 和本地部署两种模式
3. 完全对齐 SSOT 规范
4. 复用现有 `parser_adapters.py` 架构

## 2. 现有代码分析

### 2.1 已实现 ✅

| 功能 | 文件位置 | SSOT 对齐 |
|------|----------|-----------|
| bbox 归一化 (xyxy/xywh) | `app/parse_utils.py:30-57` | §5.2 ✅ |
| 文本编码回退 (utf-8 → gb18030) | `app/parse_utils.py:65-78` | §5.3 ✅ |
| 文件发现规则 (5级优先级) | `app/parse_utils.py:17-27` | §2.3 ✅ |
| ParserAdapterRegistry | `app/parser_adapters.py:230-265` | §3 ✅ |
| HttpParserAdapter (mineru/docling/ocr) | `app/parser_adapters.py:70-85` | §3 ✅ |
| LocalParserAdapter | `app/parser_adapters.py:287-325` | - |
| PARSER_FALLBACK_EXHAUSTED 错误码 | `app/parser_adapters.py:257` | §10 ✅ |

### 2.2 需补充 ⚠️

| 功能 | 文件位置 | SSOT 要求 | 优先级 |
|------|----------|-----------|--------|
| Fallback 2跳限制 | `parser_adapters.py:241` | §3 约束2 | 高 |
| MinerU 双模式 (官方API) | 不存在 | §3.1 | 中 |
| trace_id 贯穿解析 | 不存在 | §2.2 | 中 |
| DoclingParserAdapter | 不存在 | §3 | 低 |
| OcrParserAdapter | 不存在 | §3 | 低 |

### 2.3 Fallback 当前实现问题

```python
# parser_adapters.py:241-255
candidates = [route.selected_parser, *route.fallback_chain]
for parser_name in candidates:  # ❌ 没有跳数限制
    ...
```

**SSOT §3 约束**: "fallback 链最多 2 跳，避免无限回退"

**需要修改为**:
```python
# SSOT 约束: fallback 链最多 2 跳
max_attempts = min(3, len(candidates))  # selected + 2 fallbacks
for parser_name in candidates[:max_attempts]:
    ...
```

## 3. 架构设计

### 3.1 服务拓扑

```
                      +------------------+
                      |  API Container   |
                      |  (port 8000)     |
                      +--------+---------+
                               |
        +------------------------+------------------------+
        |                         |                        |
        v                         v                        v
 +-------------+          +-------------+          +-------------+
 | MinerU      |          | Docling     |          | OCR Fallback|
 | :8100       |          | :8101       |          | :8102       |
 +------+------+          +------+------+          +-------------+
        |                         |
        v                         v
 +-------------+          +-------------+
 | /v1/parse   |          | /v1/parse   |
 | POST        |          | POST        |
 +-------------+          +-------------+
```

### 3.2 MinerU 双模式支持

```
+-------------------+     +------------------+
|   API Container   |     |  MinerU Options  |
|                   |     |                  |
| MineruParserAdapter |---->| A. Official API  | --> https://api.mineru.net/v1/parse
|                   |     |   (Bearer token) |
|                   |     |                  |
|                   |     | B. Local mineru-api | --> http://localhost:8100/v1/parse
|                   |     |   (Docker container)|
+-------------------+     +------------------+
```

**环境变量**:
```bash
MINERU_API_MODE=local          # local | official
MINERU_ENDPOINT=http://mineru:8100  # 本地模式端点
MINERU_API_KEY=                # 官方模式 API Key
```

### 3.3 解析器路由

```text
doc_type_detect
 -> mineru (default for complex PDF)
 -> docling (office/html/standard pdf)
 -> ocr_fallback (scanned pages only)

约束：
1. 主解析失败才允许 fallback
2. fallback 链最多 2 跳 (SSOT §3)
3. 每次路由决策写入 parse manifest
```

## 4. SSOT 对齐检查清单

### 4.1 mineru-ingestion-spec 对齐

| SSOT 要求 | 现有实现 | 需要修改 |
|-----------|----------|----------|
| §2.3 文件发现顺序 (5级) | ✅ `parse_utils.py:17-27` | 无 |
| §3 解析器路由 | ✅ `parser_adapters.py` | 无 |
| §3 fallback 最多 2 跳 | ❌ 当前无限制 | **需修改** |
| §3 路由决策写入 manifest | ✅ 已实现 | 无 |
| §4 parse manifest 字段 | ✅ 已实现 | 无 |
| §5.1 content item 字段 | ✅ 已实现 | 无 |
| §5.2 bbox 归一化 | ✅ `parse_utils.py:30-57` | 无 |
| §5.3 文本编码处理 | ✅ `parse_utils.py:65-78` | 无 |
| §6 结构融合 | ✅ 现有实现 | 无 |
| §7 分块规范 | ✅ 现有实现 | 无 |
| §8 持久化顺序 | ✅ 已实现 | 无 |
| §10 错误码 | ✅ `PARSER_FALLBACK_EXHAUSTED` | 无 |

### 4.2 主 SSOT 对齐

| 主 SSOT 要求 | 现有实现 | 需要修改 |
|--------------|----------|----------|
| §2.2 trace_id 贯穿 | ⚠️ 部分实现 | 需补充到解析流程 |
| §2.2 幂等策略 | ✅ 已实现 | 无 |
| §4.3 通信策略 (领域事件) | ✅ outbox 模式 | 无 |
| §6.1 content_list.json 为定位真值 | ✅ 已实现 | 无 |
| §6.1 full.md 为结构真值 | ✅ 已实现 | 无 |

## 5. 实施计划

### Phase 1: 修改现有代码 (高优先级)

**Task 1.1: 添加 Fallback 2跳限制**

修改 `app/parser_adapters.py:234-265`:

```python
def parse_with_route(
    self,
    *,
    route: ParseRoute,
    document_id: str,
    default_text: str,
) -> dict[str, object]:
    candidates = [route.selected_parser, *route.fallback_chain]

    # SSOT §3 约束: fallback 链最多 2 跳
    max_attempts = min(3, len(candidates))  # selected + 2 fallbacks
    candidates = candidates[:max_attempts]

    last_error: ApiError | None = None
    for parser_name in candidates:
        ...
```

**Task 1.2: 添加 trace_id 到解析流程**

修改 `ParserAdapter.parse` 方法签名和 `parse_with_route` 调用:

```python
def parse(
    self,
    *,
    document_id: str,
    default_text: str,
    parser_version: str,
    trace_id: str | None = None,  # 新增
) -> dict[str, object]: ...
```

### Phase 2: 创建解析器服务 (中优先级)

**Task 2.1: 创建 MinerU 服务**

- `services/mineru/mineru_service.py`
- `services/mineru/requirements.txt`
- 更新 `services/mineru/Dockerfile`

**Task 2.2: 创建 Docling 服务**

- `services/docling/docling_service.py`
- `services/docling/Dockerfile`
- `services/docling/requirements.txt`

**Task 2.3: 创建 OCR 服务**

- `services/ocr/ocr_service.py`
- `services/ocr/Dockerfile`
- `services/ocr/requirements.txt`

### Phase 3: 更新适配器 (中优先级)

**Task 3.1: 实现 MineruParserAdapter (双模式)**

在 `app/parser_adapters.py` 添加:

```python
class MineruParserAdapter:
    """MinerU parser adapter with dual-mode support (official API or local)."""

    def __init__(
        self,
        *,
        mode: str = "local",
        endpoint: str = "",
        api_key: str = "",
        timeout_s: float = 120.0,
    ) -> None:
        self.name = "mineru"
        self._mode = mode
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout_s = timeout_s
```

### Phase 4: 测试

**Task 4.1: Fallback 链测试**

- `tests/test_parser_fallback_chain.py`

**Task 4.2: MinerU 双模式测试**

- `tests/test_mineru_adapter.py`

## 6. 文件清单

### 6.1 需修改的文件

| 文件 | 修改内容 |
|------|----------|
| `app/parser_adapters.py` | 添加 2 跳限制、trace_id 参数、MineruParserAdapter |

### 6.2 需创建的文件

| 文件 | 用途 |
|------|------|
| `services/mineru/mineru_service.py` | MinerU FastAPI 服务 |
| `services/mineru/requirements.txt` | Python 依赖 |
| `services/docling/docling_service.py` | Docling FastAPI 服务 |
| `services/docling/Dockerfile` | Docling Docker 镜像 |
| `services/docling/requirements.txt` | Python 依赖 |
| `services/ocr/ocr_service.py` | OCR FastAPI 服务 |
| `services/ocr/Dockerfile` | OCR Docker 镜像 |
| `services/ocr/requirements.txt` | Python 依赖 |

### 6.3 测试文件

| 文件 | 用途 |
|------|------|
| `tests/test_parser_fallback_chain.py` | Fallback 链测试 |
| `tests/test_mineru_adapter.py` | MinerU 适配器测试 |

## 7. 验收标准

1. **SSOT §3 2跳限制**: fallback 链最多尝试 3 个解析器 (selected + 2 fallbacks)
2. **SSOT §2.2 trace_id**: 解析流程中 trace_id 可追踪
3. **MinerU 双模式**: 支持官方 API 和本地部署
4. **所有测试通过**: `pytest tests/test_parser*.py -v`

## 8. 参考来源

1. SSOT: `docs/plans/2026-02-21-end-to-end-unified-design.md`
2. 解析规范: `docs/design/2026-02-21-mineru-ingestion-spec.md`
3. MinerU 官方 API: https://mineru.net/apiManage/docs
4. MinerU GitHub: https://github.com/opendatalab/MinerU
5. Docling GitHub: https://github.com/docling-project/docling
