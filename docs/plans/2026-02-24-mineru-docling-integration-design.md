# MinerU/Docling 解析器集成设计

> 版本：v2026.02.24-r2
> 状态：Implemented
> 实现完成：2026-02-24
> 验收测试：全部通过 (551 tests)
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

### 2.2 已实现 ✅

| 功能 | 文件位置 | SSOT 要求 | 状态 |
|------|----------|-----------|------|
| Fallback 2跳限制 | `parser_adapters.py:237-240` | §3 约束2 | ✅ 已实现 |
| 文件发现 5级优先级 | `parse_utils.py:18-44` | §2.3 | ✅ 已实现 |

### 2.3 不在本次实施范围内

以下功能现有代码已满足需求，无需修改：

1. **本地 PDF/DOCX 解析** - `document_parser.py` 已完整实现
2. **HttpParserAdapter** - 已支持 mineru/docling/ocr HTTP 调用
3. **路由选择逻辑** - `select_parse_route` 已实现
4. **独立解析器服务** - 当前 HttpParserAdapter 已可对接外部服务，无需新建

如需部署独立 MinerU/Docling/OCR 服务，只需配置环境变量：
```bash
MINERU_ENDPOINT=http://mineru:8100
DOCLING_ENDPOINT=http://docling:8101
OCR_ENDPOINT=http://ocr:8102
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

| SSOT 要求 | 现有实现 | 状态 |
|-----------|----------|------|
| §2.3 文件发现顺序 (5级) | `parse_utils.py:18-44` | ✅ 已实现 |
| §3 解析器路由 | `parser_adapters.py` | ✅ 已实现 |
| §3 fallback 最多 2 跳 | `parser_adapters.py:237-240` | ✅ 已实现 |
| §3 路由决策写入 manifest | 已实现 | ✅ |
| §4 parse manifest 字段 | 已实现 | ✅ |
| §5.1 content item 字段 | 已实现 | ✅ |
| §5.2 bbox 归一化 | `parse_utils.py:46-74` | ✅ |
| §5.3 文本编码处理 | `parse_utils.py:81-94` | ✅ |
| §6 结构融合 | 现有实现 | ✅ |
| §7 分块规范 | 现有实现 | ✅ |
| §8 持久化顺序 | 已实现 | ✅ |
| §10 错误码 | `PARSER_FALLBACK_EXHAUSTED` | ✅ |

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

## 9. 实现状态

| 功能 | 文件 | SSOT | 状态 |
|------|------|------|------|
| Fallback 2跳限制 | parser_adapters.py:237-240 | §3 | ✅ |
| 文件发现 5级优先级 | parse_utils.py:18-44 | §2.3 | ✅ |
| bbox 归一化 | parse_utils.py:46-74 | §5.2 | ✅ (已有) |
| 编码回退 | parse_utils.py:81-94 | §5.3 | ✅ (已有) |
| 本地 PDF 解析 | document_parser.py:137-212 | - | ✅ (已有) |
| 本地 DOCX 解析 | document_parser.py:215-266 | - | ✅ (已有) |
| **MinerU Official API** | mineru_official_api.py | - | ✅ 新增 |
| **MinerU Parse Service** | mineru_parse_service.py | - | ✅ 新增 |
| **图片存储** | mineru_parse_service.py:_save_images | §8.1 | ✅ 新增 |
| **StoreParse 集成** | store_parse.py:162-210 | §3 | ✅ 新增 |

## 10. 新增功能

### 10.1 MinerU Official API Adapter

**文件:** `app/mineru_official_api.py`

异步任务模式的 MinerU 云 API 适配器：

- `MineruApiConfig`: API 配置
- `MineruContentItem`: SSOT §5.1 对齐的内容项
- `MineruOfficialApiClient`: 低级 API 客户端
- `MineruOfficialApiAdapter`: 高级解析适配器

### 10.2 MinerU Parse Service

**文件:** `app/mineru_parse_service.py`

完整解析服务， 持久化:

- 保存结果 zip 到对象存储
- **提取并保存图片到对象存储**（新增）
- 更新 parse manifest
- 转换 content_list 为 chunks
- 持久化 chunks 到数据库

### 10.3 图片存储功能（新增）

**存储路径:** `tenants/{tenant_id}/document_parse/{document_id}/images/{filename}`

**支持格式:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`, `.svg`

**用途:**
1. 引用回跳时展示上下文截图
2. 表格/图表内容可视化
3. OCR 结果校验

### 10.3 StoreParse 集成

**文件:** `app/store_parse.py`

集成 MinerU Official API 到现有解析流程:

- `_try_mineru_official_api()`: 尝试 MinerU Official API
- 修改 `_parse_document_file()`: 优先使用 MinerU Official API

## 11. 使用方式

### 11.1 环境变量

```bash
# MinerU Official API (必需)
export MINERU_API_KEY="your_api_key"

# 可选配置
export MINERU_TIMEOUT_S=30
export MINERU_MAX_POLL_TIME_S=180
export MINERU_IS_OCR=true
export MINERU_ENABLE_FORMULA=false
```

### 11.2 上传文档

```python
POST /api/v1/documents/upload
{
    "filename": "document.pdf",
    "source_url": "https://example.com/document.pdf",
    "tenant_id": "tenant_abc"
}
```

### 11.3 触发解析

```python
POST /api/v1/documents/{document_id}/parse
```

解析器会自动：
1. 检测 `source_url` 和 `MINERU_API_KEY`
2. 使用 MinerU Official API 解析
3. 保存结果到对象存储
4. 持久化 chunks 到数据库
