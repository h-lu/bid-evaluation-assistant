# MinerU/Docling 解析器集成设计

> 版本：v2026.02.24-r1
> 状态：Approved
> 对齐：`docs/design/2026-02-21-mineru-ingestion-spec.md`

## 1. 目标

1. 实现 MinerU/Docling/OCR 三层解析器服务
2. MinerU 支持官方 API 和本地部署两种模式
3. 完全对齐 SSOT 规范
4. 复用现有 `parser_adapters.py` 架构

## 2. 架构设计

### 2.1 服务拓扑

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

### 2.2 MinerU 双模式支持

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

### 2.3 解析器路由

```text
doc_type_detect
 -> mineru (default for complex PDF)
 -> docling (office/html/standard pdf)
 -> ocr_fallback (scanned pages only)

约束：
1. 主解析失败才允许 fallback
2. fallback 链最多 2 跳
3. 每次路由决策写入 parse manifest
```

## 3. 环境变量配置

```bash
# MinerU 配置
MINERU_API_MODE=local          # local | official
MINERU_ENDPOINT=http://mineru:8100  # 本地模式端点
MINERU_API_KEY=                # 官方模式 API Key
MINERU_TIMEOUT_S=120

# Docling 配置
DOCLING_ENDPOINT=http://docling:8101
DOCLING_TIMEOUT_S=60

# OCR 配置
OCR_ENDPOINT=http://ocr:8102
OCR_TIMEOUT_S=180
```

## 4. API 契约

### 4.1 MinerU 服务

**官方 API 请求格式**:
```
POST https://api.mineru.net/v1/parse
Headers: Authorization: Bearer <token>
Body: {
  "url": "https://example.com/document.pdf",
  "is_ocr": true,
  "enable_formula": false
}
```

**本地 API 请求格式**:
```
POST http://localhost:8100/v1/parse
Body: multipart/form-data
  - file: <PDF 文件>
```

**统一响应格式**:
```json
{
  "content_list": [
    {
      "text": "段落文本",
      "type": "text",
      "page_idx": 0,
      "bbox": [x0, y0, x1, y1]
    }
  ],
  "full_md": "# 完整 Markdown 内容",
  "metadata": {
    "page_count": 10,
    "parser_version": "mineru-2.0"
  }
}
```

### 4.2 Docling 服务

**请求格式**:
```
POST http://localhost:8101/v1/parse
Body: multipart/form-data
  - file: <文档文件>
```

**响应格式**: 与 MinerU 相同

### 4.3 OCR 服务

**请求格式**:
```
POST http://localhost:8102/v1/parse
Body: multipart/form-data
  - file: <文档文件>
```

**响应格式**: 与 MinerU 相同

## 5. 文件清单

### 5.1 新增文件

| 文件 | 用途 |
|------|------|
| `services/mineru/mineru_service.py` | MinerU FastAPI 服务 |
| `services/mineru/Dockerfile` | MinerU Docker 镜像 |
| `services/mineru/requirements.txt` | Python 依赖 |
| `services/docling/docling_service.py` | Docling FastAPI 服务 |
| `services/docling/Dockerfile` | Docling Docker 镜像 |
| `services/docling/requirements.txt` | Python 依赖 |
| `services/ocr/ocr_service.py` | OCR FastAPI 服务 |
| `services/ocr/Dockerfile` | OCR Docker 镜像 |
| `services/ocr/requirements.txt` | Python 依赖 |

### 5.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `app/parser_adapters.py` | 添加 MineruParserAdapter (双模式)、DoclingParserAdapter、OcrParserAdapter |
| `docker-compose.production.yml` | 添加 parser 服务定义 |
| `.env.example` | 添加新环境变量 |
| `app/parse_utils.py` | 完善输入文件发现规则 (5级优先级) |
| `app/parser_adapters.py` | 添加 fallback 2跳限制 |

### 5.3 测试文件

| 文件 | 用途 |
|------|------|
| `tests/test_mineru_adapter.py` | MinerU 适配器单元测试 |
| `tests/test_docling_adapter.py` | Docling 适配器单元测试 |
| `tests/test_ocr_adapter.py` | OCR 适配器单元测试 |
| `tests/test_parser_fallback_chain.py` | Fallback 链集成测试 |

## 6. Docker Compose 配置

```yaml
services:
  # MinerU Parser Service
  mineru:
    build:
      context: ./services/mineru
      dockerfile: Dockerfile
    ports:
      - "8100:8000"
    environment:
      - MINERU_DEVICE=${MINERU_DEVICE:-cpu}
    volumes:
      - mineru-models:/root/.cache/mineru
      - mineru-output:/tmp/mineru_output
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    profiles:
      - parsers
      - full

  # Docling Parser Service
  docling:
    build:
      context: ./services/docling
      dockerfile: Dockerfile
    ports:
      - "8101:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    profiles:
      - parsers
      - full

  # OCR Fallback Service
  ocr:
    build:
      context: ./services/ocr
      dockerfile: Dockerfile
    ports:
      - "8102:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    profiles:
      - parsers
      - full

volumes:
  mineru-models:
  mineru-output:
```

## 7. SSOT 对齐检查

| SSOT 要求 | 实现状态 |
|-----------|----------|
| §2 输入文件发现规则 | 修改 `parse_utils.py` |
| §3 解析器路由 | 已实现 + 添加2跳限制 |
| §4 Parse Manifest | ✅ 已实现 |
| §5.1 content item 字段 | ✅ 已实现 |
| §5.2 bbox 归一化 | ✅ 已实现 |
| §5.3 文本编码处理 | ✅ 已实现 |
| §6 结构融合 | 现有基础实现 |
| §7 分块规范 | 使用现有实现 |
| §8 持久化顺序 | ✅ 已实现 |
| §10 错误码 | ✅ 已实现 |

## 8. 实现阶段

### Phase 1: 解析器服务
1. 创建 `services/mineru/` (mineru_service.py + Dockerfile)
2. 创建 `services/docling/` (docling_service.py + Dockerfile)
3. 创建 `services/ocr/` (ocr_service.py + Dockerfile)

### Phase 2: 适配器更新
1. 实现 `MineruParserAdapter` (双模式)
2. 实现 `DoclingParserAdapter`
3. 实现 `OcrParserAdapter`
4. 更新 `build_default_parser_registry()`
5. 添加 fallback 2跳限制

### Phase 3: 集成配置
1. 更新 `docker-compose.production.yml`
2. 更新 `.env.example`
3. 完善输入文件发现规则

### Phase 4: 测试
1. 单元测试 (3个适配器)
2. 集成测试 (fallback 链)
3. E2E 测试 (真实 PDF 解析)

## 9. 参考来源

1. MinerU 官方 API: https://mineru.net/apiManage/docs
2. MinerU GitHub: https://github.com/opendatalab/MinerU
3. Docling GitHub: https://github.com/docling-project/docling
4. SSOT 规范: `docs/design/2026-02-21-mineru-ingestion-spec.md`
