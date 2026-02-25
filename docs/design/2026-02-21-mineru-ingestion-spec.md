# MinerU 解析入库规范（content_list + full.md）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 保留原文定位能力：`page + bbox`。
2. 保留结构语义：`section + heading_path`。
3. 产出稳定 chunk，支持检索、评分与引用回跳。
4. 明确异常分类、重试边界、失败落库策略。

## 2. 输入与发现规则

### 2.1 标准输入

1. `*_content_list.json`（定位主来源）
2. `full.md`（结构主来源）
3. `*_middle.json`（调试辅助，可选）

### 2.2 兼容输入

1. `*context_list.json`（旧命名兼容）
2. `*.md`（当 `full.md` 缺失时回退）

### 2.3 文件发现顺序

```text
1) *_content_list.json
2) *context_list.json
3) full.md
4) *.md
5) *_middle.json
```

## 3. 解析器路由

```text
doc_type_detect
 -> mineru (default for complex PDF)
 -> docling (office/html/standard pdf)
 -> ocr_fallback (scanned pages only)
```

约束：

1. 主解析失败才允许 fallback。
2. fallback 链最多 2 跳，避免无限回退。
3. 每次路由决策都写入 parse manifest。

### 3.1 文件 URL 获取策略

MinerU 云端 API 只接受 URL，不支持直接文件上传。系统支持两种方式获取 URL：

| 场景 | 优先级 | 方式 |
|------|--------|------|
| 文档有 `source_url` | 1 | 直接使用 |
| 文档有 `storage_uri` (S3) | 2 | 生成预签名 URL |
| 文档有 `storage_uri` (本地) | - | 不支持，回退到本地解析 |

**预签名 URL 参数**:
- 有效期: 3600 秒 (1 小时)
- 仅 S3 后端支持

## 4. parse manifest 契约

每次解析必须生成 `document_parse_runs.manifest`，最小字段：

1. `document_id`
2. `tenant_id`
3. `selected_parser`
4. `fallback_chain`
5. `input_files[{name, sha256, size}]`
6. `started_at`
7. `ended_at`
8. `status`
9. `error_code`

## 5. 字段标准化

### 5.1 content item 必需字段

1. `text`
2. `type`
3. `page_idx`
4. `bbox`

### 5.2 bbox 归一化

输入可能形态：

1. `[x0,y0,x1,y1]`（xyxy）
2. `[x,y,w,h]`（xywh）

统一输出：`[x0,y0,x1,y1]`。

判定规则：

1. 若 `x1>x0 && y1>y0` 直接视为 xyxy。
2. 若 `w>0 && h>0` 且不满足上条，视为 xywh 转换。
3. 无法判定 -> `MINERU_BBOX_FORMAT_INVALID`。

### 5.3 文本与编码

1. 编码读取优先 `utf-8`，失败尝试 `gb18030`。
2. 换行统一为 `\n`。
3. 移除非法控制字符（保留 `\t`）。
4. 失败错误码：`TEXT_ENCODING_UNSUPPORTED`。

## 6. 结构融合策略（定位真值 + 结构真值）

1. 以 JSON item 顺序构建定位片段。
2. 用 `full.md` 构建 heading 树。
3. 将 heading_path 映射回 JSON 片段，生成结构化 chunk。

融合冲突时：

1. 定位冲突：以 JSON 为准。
2. 结构冲突：以 `full.md` 为准，但必须记录冲突标记。
3. 两者均缺失：标注 `structure_missing=true`。

## 7. 分块规范

### 7.1 分块参数（默认）

1. `target_size_tokens = 450`
2. `max_size_tokens = 700`
3. `overlap_tokens = 80`
4. `min_size_tokens = 120`

### 7.2 分块边界规则

优先在以下边界切分：

1. 标题层级变化
2. 表格块边界
3. 列表块边界
4. 页面跳转边界

禁止：

1. 把同一表格切成多段（除超大表格）。
2. 把同一句跨 chunk 截断且无 overlap。

### 7.3 chunk 元数据最小字段

1. `chunk_id`
2. `tenant_id`
3. `project_id`
4. `document_id`
5. `supplier_id`
6. `pages[]`
7. `positions[]`（`{page,bbox,start,end}`）
8. `section`
9. `heading_path[]`
10. `chunk_type`（`text/table/image/formula/list`）
11. `parser`
12. `parser_version`

## 8. 持久化顺序

```text
raw_file stored
 -> parse manifest stored
 -> chunks stored (PostgreSQL)
 -> images stored (Object Storage)  # 新增：图片持久化
 -> vectors indexed (Chroma/LightRAG)
 -> document status = indexed
```

失败回滚策略：

1. PG chunks 失败：不进入向量写入。
2. 向量写入部分成功：记录待修复任务，不标记 indexed。
3. 全部失败：进入任务重试/最终 DLQ。

### 8.1 图片存储规范（新增）

MinerU 解析结果中的 `images/` 目录图片需持久化：

**存储路径：**
```text
tenants/{tenant_id}/document_parse/{document_id}/images/{filename}
```

**支持格式：**
- `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`, `.svg`

**元数据记录：**
- `manifest.images_count`: 图片数量
- `result.images_storage_uris`: 图片 URI 列表

**用途：**
1. 引用回跳时展示上下文截图
2. 表格/图表内容可视化
3. OCR 结果校验

## 9. 引用回跳契约

后续检索/评分输出中的 citation 必须满足：

1. 可唯一定位 `chunk_id`
2. 至少一条 `positions[{page,bbox}]`
3. `bbox` 坐标可映射到 PDF viewport
4. 若有多页位置，默认返回与 claim 最相关的一条作为 `primary_position`

## 10. 错误码与处理

1. `DOC_PARSE_OUTPUT_NOT_FOUND`：关键输出缺失，立即失败。
2. `DOC_PARSE_SCHEMA_INVALID`：JSON 结构错误，最多重试 1 次。
3. `MINERU_BBOX_FORMAT_INVALID`：bbox 非法，不可重试。
4. `TEXT_ENCODING_UNSUPPORTED`：编码不可识别，不可重试。
5. `PARSER_FALLBACK_EXHAUSTED`：fallback 链耗尽，进入 DLQ。

## 11. 验收标准

1. `content_list/context_list` 均可被正确处理。
2. chunk 位置回跳成功率 >= 98%。
3. 同一文档重复解析（同版本配置）产出差异 <= 1%。
4. 解析失败样本均有明确错误码与 trace。

## 12. 参考来源（核验：2026-02-21）

1. MinerU: https://github.com/opendatalab/MinerU
2. Docling: https://github.com/docling-project/docling
3. 历史融合提交：`76f898d`, `a21fa09`, `7f05f7e`
