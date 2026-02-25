# MinerU/Docling 集成实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 补充解析器集成缺失功能，对齐 SSOT §3 (fallback 2跳限制) 和 §2.3 (文件发现 5级优先级)

**Architecture:** 复用现有 `parser_adapters.py` 和 `parse_utils.py`，仅修改缺失部分

**Tech Stack:** Python 3.11, pytest

**Design Doc:** `docs/plans/2026-02-24-mineru-docling-integration-design.md`

---

## 现有代码分析

### 已实现 ✅

| 功能 | 文件位置 | SSOT |
|------|----------|------|
| bbox 归一化 (xyxy/xywh) | `app/parse_utils.py:29-57` | §5.2 ✅ |
| 编码回退 (utf-8 → gb18030) | `app/parse_utils.py:65-78` | §5.3 ✅ |
| 文件发现 (2级) | `app/parse_utils.py:18-26` | ⚠️ §2.3 部分 |
| ParserAdapterRegistry | `app/parser_adapters.py:230-266` | §3 ⚠️ |
| HttpParserAdapter | `app/parser_adapters.py:70-227` | ✅ |
| LocalParserAdapter | `app/parser_adapters.py:289-325` | ✅ |
| select_parse_route | `app/parser_adapters.py:269-278` | ✅ |
| 本地 PDF 解析 (PyMuPDF) | `app/document_parser.py:137-212` | ✅ |
| 本地 DOCX 解析 | `app/document_parser.py:215-266` | ✅ |
| 分块逻辑 | `app/document_parser.py:68-134` | ✅ |

### 需修改 ⚠️

| 功能 | 文件位置 | 问题 | SSOT 要求 |
|------|----------|------|-----------|
| **Fallback 无限制** | `parser_adapters.py:241-255` | 遍历所有 fallback | §3 最多 2 跳 |
| **文件发现只有 2 级** | `parse_utils.py:18-26` | 缺少 full.md, *.md, *_middle.json | §2.3 5 级优先级 |

---

## Phase 1: 修改现有代码 (必须)

### Task 1.1: 添加 Fallback 2跳限制

**Files:**
- Modify: `app/parser_adapters.py:234-266`
- Create: `tests/test_parser_fallback_limit.py`

**Step 1: 编写失败测试**

Create `tests/test_parser_fallback_limit.py`:

```python
"""Tests for SSOT §3 fallback 2-hop limit."""
import pytest
from app.errors import ApiError
from app.parser_adapters import (
    ParserAdapterRegistry,
    ParseRoute,
    StubParserAdapter,
)


class AlwaysFailAdapter(StubParserAdapter):
    """Adapter that always fails."""
    def parse(self, **kwargs):
        raise ApiError(
            code="PARSE_FAILED",
            message="intentional failure",
            error_class="transient",
            retryable=True,
            http_status=503,
        )


def test_fallback_chain_limited_to_2_hops():
    """SSOT §3: fallback 链最多 2 跳 (selected + 2 fallbacks = 3 次尝试)."""
    # 4 个候选，只有最后一个能成功
    adapters = {
        "a": AlwaysFailAdapter(name="a", section="a"),
        "b": AlwaysFailAdapter(name="b", section="b"),
        "c": AlwaysFailAdapter(name="c", section="c"),
        "d": StubParserAdapter(name="d", section="d"),  # 这个能成功
    }
    registry = ParserAdapterRegistry(adapters)

    route = ParseRoute(
        selected_parser="a",
        fallback_chain=["b", "c", "d"],  # 4 个候选
        parser_version="v1",
    )

    # SSOT 约束: 只尝试前 3 个 (a, b, c)，d 不应被尝试
    with pytest.raises(ApiError, match="PARSER_FALLBACK_EXHAUSTED"):
        registry.parse_with_route(
            route=route,
            document_id="doc_1",
            default_text="test",
        )


def test_fallback_succeeds_within_2_hops():
    """When success is within 2 hops, should return result."""
    adapters = {
        "a": AlwaysFailAdapter(name="a", section="a"),
        "b": StubParserAdapter(name="b", section="b"),  # 第 2 个成功
        "c": StubParserAdapter(name="c", section="c"),
    }
    registry = ParserAdapterRegistry(adapters)

    route = ParseRoute(
        selected_parser="a",
        fallback_chain=["b", "c"],
        parser_version="v1",
    )

    result = registry.parse_with_route(
        route=route,
        document_id="doc_1",
        default_text="test",
    )

    assert result["parser"] == "b"
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_parser_fallback_limit.py -v`
Expected: FAIL - 当前没有 2 跳限制

**Step 3: 修改 parse_with_route**

Modify `app/parser_adapters.py:234-266`:

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
    # selected_parser + 最多 2 个 fallback = 最多 3 次尝试
    max_attempts = min(3, len(candidates))
    candidates = candidates[:max_attempts]

    last_error: ApiError | None = None
    for parser_name in candidates:
        adapter = self._adapters.get(parser_name)
        if adapter is None:
            continue
        try:
            return adapter.parse(
                document_id=document_id,
                default_text=default_text,
                parser_version=route.parser_version,
            )
        except ApiError as exc:
            last_error = exc
            continue

    raise ApiError(
        code="PARSER_FALLBACK_EXHAUSTED",
        message=(
            f"no parser adapter available after {len(candidates)} attempts: {last_error.code}"
            if last_error is not None
            else "no parser adapter available"
        ),
        error_class="transient",
        retryable=True,
        http_status=503,
    )
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_parser_fallback_limit.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add app/parser_adapters.py tests/test_parser_fallback_limit.py
git commit -m "feat(parsers): add fallback 2-hop limit per SSOT §3

SSOT §3 约束: fallback 链最多 2 跳
- max_attempts = min(3, len(candidates))
- candidates[:max_attempts]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 1.2: 补充文件发现 5 级优先级

**Files:**
- Modify: `app/parse_utils.py:18-26`
- Modify: `tests/test_parse_utils.py`

**Step 1: 编写失败测试**

Add to `tests/test_parse_utils.py`:

```python
def test_select_content_source_5_level_priority():
    """SSOT §2.3: 文件发现 5 级优先级."""
    # 级别 1: *_content_list.json 优先
    files = ["a_context_list.json", "z_content_list.json", "full.md", "other.md", "x_middle.json"]
    assert select_content_source(files) == "z_content_list.json"

    # 级别 2: *context_list.json (无 content_list 时)
    files = ["a_context_list.json", "full.md", "other.md", "x_middle.json"]
    assert select_content_source(files) == "a_context_list.json"

    # 级别 3: full.md (无 content_list/context_list 时)
    files = ["full.md", "other.md", "x_middle.json"]
    assert select_content_source(files) == "full.md"

    # 级别 4: *.md (无 full.md 时)
    files = ["other.md", "x_middle.json"]
    assert select_content_source(files) == "other.md"

    # 级别 5: *_middle.json (无 md 时)
    files = ["x_middle.json", "y_middle.json"]
    assert select_content_source(files) == "x_middle.json"

    # 无匹配
    files = ["unknown.txt", "data.bin"]
    assert select_content_source(files) is None
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_parse_utils.py::test_select_content_source_5_level_priority -v`
Expected: FAIL - 当前只有 2 级

**Step 3: 修改 select_content_source**

Modify `app/parse_utils.py:18-26`:

```python
def select_content_source(files: Iterable[str]) -> str | None:
    """Select content source file based on SSOT §2.3 5-level priority.

    Priority order:
    1) *_content_list.json
    2) *context_list.json
    3) full.md
    4) *.md
    5) *_middle.json
    """
    names = list(files)

    # Level 1: *_content_list.json
    for name in names:
        if name.endswith("_content_list.json"):
            return name

    # Level 2: *context_list.json (legacy naming)
    for name in names:
        if name.endswith("context_list.json"):
            return name

    # Level 3: full.md
    for name in names:
        if name == "full.md" or name.endswith("/full.md"):
            return name

    # Level 4: *.md (any markdown)
    for name in names:
        if name.endswith(".md"):
            return name

    # Level 5: *_middle.json (debug only)
    for name in names:
        if name.endswith("_middle.json"):
            return name

    return None
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_parse_utils.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add app/parse_utils.py tests/test_parse_utils.py
git commit -m "feat(parse): add 5-level file discovery priority per SSOT §2.3

SSOT §2.3 文件发现顺序:
1) *_content_list.json
2) *context_list.json
3) full.md
4) *.md
5) *_middle.json

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: 运行完整测试套件

### Task 2.1: 运行所有解析相关测试

**Step 1: 运行测试**

Run: `pytest tests/test_parser*.py tests/test_parse*.py tests/test_document*.py -v --tb=short`
Expected: ALL PASS

**Step 2: 验证无回归**

Run: `pytest tests/ -v --tb=short -x`
Expected: 无新失败

---

## Phase 3: 更新设计文档

### Task 3.1: 标记设计文档为已实现

**Files:**
- Modify: `docs/plans/2026-02-24-mineru-docling-integration-design.md`

**Step 1: 更新状态**

Change header from:
```markdown
> 状态：Draft
```

To:
```markdown
> 状态：Implemented
> 实现完成：2026-02-24
> 验收测试：全部通过
```

**Step 2: 添加实现状态章节**

Add at end of file:
```markdown
## 9. 实现状态

| 功能 | 文件 | SSOT | 状态 |
|------|------|------|------|
| Fallback 2跳限制 | parser_adapters.py:237-240 | §3 | ✅ |
| 文件发现 5级优先级 | parse_utils.py:18-44 | §2.3 | ✅ |
| bbox 归一化 | parse_utils.py:46-74 | §5.2 | ✅ (已有) |
| 编码回退 | parse_utils.py:81-94 | §5.3 | ✅ (已有) |
| 本地 PDF 解析 | document_parser.py:137-212 | - | ✅ (已有) |
| 本地 DOCX 解析 | document_parser.py:215-266 | - | ✅ (已有) |
```

**Step 3: Commit**

```bash
git add docs/plans/2026-02-24-mineru-docling-integration-design.md
git commit -m "docs: mark MinerU/Docling design as implemented

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Verification Checklist

- [x] Fallback 2跳限制已实现 (SSOT §3)
- [x] 文件发现 5级优先级已实现 (SSOT §2.3)
- [x] 所有现有测试继续通过
- [x] 新测试覆盖新功能
- [x] 设计文档已更新
- [x] MinerU Official API 集成完成
- [x] 解析结果持久化完成

---

## SSOT Alignment Summary

| SSOT 约束 | 实现任务 | 状态 |
|-----------|----------|------|
| §3 fallback 最多 2 跳 | Task 1.1 | ✅ |
| §2.3 文件发现 5 级优先级 | Task 1.2 | ✅ |
| §5.2 bbox 归一化 | 现有实现 | ✅ |
| §5.3 编码回退 | 现有实现 | ✅ |
| §10 错误码 | 现有实现 | ✅ |
| §4 parse manifest | Task 1.3 | ✅ |
| §8 持久化顺序 | Task 1.3 | ✅ |

---

## 不在本次实施范围内

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

---

## Phase 4: MinerU Official API 集成 (已完成)

### Task 4.1: 创建 MinerU Official API 适配器

**Files:**
- Create: `app/mineru_official_api.py`
- Create: `tests/test_mineru_official_api.py`
- Create: `tests/test_mineru_official_api_adapter.py`

**实现内容:**
- `MineruApiConfig`: API 配置类
- `MineruContentItem`: 内容项模型 (SSOT §5.1)
- `MineruOfficialApiClient`: 低级 API 客户端
- `MineruOfficialApiAdapter`: 高级适配器

**SSOT 对齐:**
- §5.1 字段标准化: text, type, page_idx, bbox
- §5.2 bbox 归一化
- §10 错误码

**Commit:** `e2c9844`

### Task 4.2: 创建 MinerU 解析持久化服务

**Files:**
- Create: `app/mineru_parse_service.py`
- Create: `tests/test_mineru_parse_service.py`

**实现内容:**
- `MineruParseService`: 完整解析流程服务
- `MineruParseResult`: 解析结果数据类
- `build_mineru_parse_service()`: 工厂函数

**SSOT 对齐:**
- §4 parse manifest 契约
- §8 持久化顺序
- §7.3 chunk 元数据字段

**Commit:** `4db1bf0`

### Task 4.3: 集成到现有解析流程

**Files:**
- Modify: `app/store_parse.py`

**实现内容:**
- 添加 `_try_mineru_official_api()` 方法
- 修改 `_parse_document_file()` 集成 MinerU Official API
- 支持 `source_url` 字段

**解析路由:**
1. MinerU Official API (MINERU_API_KEY + source_url)
2. Local PyMuPDF (file_bytes available)
3. Stub adapter (fallback)

**Commit:** `aff9f09`

---

## 新增环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MINERU_API_KEY` | MinerU Official API Key | (必需) |
| `MINERU_TIMEOUT_S` | 请求超时 (秒) | 30 |
| `MINERU_MAX_POLL_TIME_S` | 最大轮询时间 (秒) | 180 |
| `MINERU_IS_OCR` | 启用 OCR | true |
| `MINERU_ENABLE_FORMULA` | 启用公式识别 | false |

---

## 新增测试统计

| 测试文件 | 测试数 | 状态 |
|----------|--------|------|
| `test_mineru_official_api.py` | 5 | ✅ |
| `test_mineru_official_api_adapter.py` | 21 | ✅ |
| `test_mineru_parse_service.py` | 13 | ✅ |

**总计:** 39 个新测试，
