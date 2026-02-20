# MinerU 输出格式处理研究

> 研究日期：2026-02-20
> 研究问题：MinerU JSON 不能很好保存文档结构，Markdown 无法保留页面位置信息
> 数据来源：Web Search、Context7、官方文档

---

## 一、问题分析

### 1.1 两种输出格式的优缺点

| 格式 | 优点 | 缺点 |
|------|------|------|
| **JSON** (content_list.json) | ✅ 包含 bbox 坐标、页码、块类型<br>✅ 位置信息完整 | ❌ 文档结构不够直观<br>❌ 表格/列表结构需要额外处理 |
| **Markdown** | ✅ 保留标题层级结构<br>✅ 表格/列表格式清晰<br>✅ 可读性强 | ❌ **无页码信息**<br>❌ **无位置坐标**<br>❌ 溯源困难 |

### 1.2 核心矛盾

```
┌─────────────────────────────────────────────────────────────┐
│                      核心问题                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   JSON 输出 ──────→ 位置信息 ✅  但 结构表达 ❌              │
│                                                             │
│   MD 输出 ────────→ 结构清晰 ✅  但 位置信息 ❌              │
│                                                             │
│   RAG 系统需要 ───→ 两者都要！                              │
│                   • 语义检索需要结构化文本                   │
│                   • 溯源引用需要页码/位置                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、MinerU 中间文件结构分析

### 2.1 middle.json（中间态文件）

包含完整的块级别元数据：

```json
{
  "blocks": [
    {
      "id": "block_001",
      "text": "提取的文本内容",
      "bbox": [x, y, width, height],
      "page": 1,
      "type": "text",
      "style": {
        "font": "Arial",
        "size": 12
      },
      "hierarchy": {
        "section": "1. 引言",
        "level": 2
      }
    }
  ]
}
```

**关键字段：**
| 字段 | 说明 | 用途 |
|------|------|------|
| `bbox` | 边界框坐标 [x, y, w, h] | 精确定位 |
| `page` | 页码 | 溯源引用 |
| `type` | 块类型（text/table/image/formula） | 分类处理 |
| `hierarchy` | 章节层级 | 结构理解 |

### 2.2 content_list.json（最终输出）

```json
[
  {
    "text": "本文提出一种新的深度学习架构...",
    "type": "text",
    "page_idx": 2,
    "bbox": [50, 200, 400, 350]
  }
]
```

---

## 三、解决方案

### 方案 A：JSON + Metadata 分离（推荐 ⭐）

**核心思路**：使用 JSON 的位置信息，同时提取结构化元数据

```python
from typing import List, Dict, Any
from pydantic import BaseModel

class ChunkMetadata(BaseModel):
    """分块元数据"""
    source: str           # 文件路径
    page: int             # 页码
    bbox: List[float]     # 边界框 [x0, y0, x1, y1]
    block_type: str       # 块类型
    section: str = ""     # 所属章节
    heading_path: List[str] = []  # 标题路径

class DocumentChunk(BaseModel):
    """文档分块"""
    content: str
    metadata: ChunkMetadata


def process_mineru_output(content_list: List[Dict], markdown: str) -> List[DocumentChunk]:
    """
    处理 MinerU 输出，合并 JSON 位置信息和 Markdown 结构

    策略：
    1. 从 JSON 提取位置信息（bbox, page）
    2. 从 Markdown 提取结构信息（标题层级）
    3. 合并生成带完整元数据的分块
    """
    chunks = []
    current_section = ""
    heading_stack = []

    for item in content_list:
        # 提取位置信息
        metadata = ChunkMetadata(
            source=item.get("source", ""),
            page=item.get("page_idx", 0),
            bbox=item.get("bbox", [0, 0, 0, 0]),
            block_type=item.get("type", "text"),
            section=current_section,
            heading_path=heading_stack.copy()
        )

        chunk = DocumentChunk(
            content=item["text"],
            metadata=metadata
        )
        chunks.append(chunk)

        # 更新标题栈（如果检测到标题）
        if item.get("type") == "title":
            heading_stack.append(item["text"])
            current_section = item["text"]

    return chunks
```

### 方案 B：结构感知分块器

**核心思路**：在分块时保留位置信息

```python
from typing import List, Tuple
import re

class StructureAwareChunker:
    """结构感知分块器 - 保留位置信息"""

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 64,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def chunk_with_positions(
        self,
        content_list: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        分块并保留位置信息

        输入: MinerU content_list.json
        输出: 带位置元数据的分块列表
        """
        chunks = []
        current_chunk = {
            "content": "",
            "positions": [],  # 位置列表
            "metadata": {}
        }

        for item in content_list:
            text = item.get("text", "")
            page = item.get("page_idx", 0)
            bbox = item.get("bbox", [0, 0, 0, 0])

            # 位置标签格式：@@{page}\t{x0}\t{x1}\t{top}\t{bottom}##
            position_tag = f"@@{page}\t{bbox[0]}\t{bbox[2]}\t{bbox[1]}\t{bbox[3]}##"

            # 添加到当前分块
            if len(current_chunk["content"]) + len(text) <= self.chunk_size:
                current_chunk["content"] += text + "\n"
                current_chunk["positions"].append({
                    "page": page,
                    "bbox": bbox,
                    "start": len(current_chunk["content"]) - len(text) - 1,
                    "end": len(current_chunk["content"]) - 1
                })
            else:
                # 保存当前分块
                if len(current_chunk["content"]) >= self.min_chunk_size:
                    chunks.append(current_chunk)

                # 开始新分块（带 overlap）
                overlap_text = current_chunk["content"][-self.overlap:] if self.overlap > 0 else ""
                current_chunk = {
                    "content": overlap_text + text + "\n",
                    "positions": [{
                        "page": page,
                        "bbox": bbox,
                        "start": len(overlap_text),
                        "end": len(overlap_text) + len(text)
                    }],
                    "metadata": {
                        "source": item.get("source", ""),
                        "section": self._extract_section(item)
                    }
                }

        # 保存最后一个分块
        if len(current_chunk["content"]) >= self.min_chunk_size:
            chunks.append(current_chunk)

        return chunks

    def _extract_section(self, item: Dict) -> str:
        """提取章节信息"""
        hierarchy = item.get("hierarchy", {})
        return hierarchy.get("section", "")

    @staticmethod
    def extract_positions(chunk_content: str) -> List[Dict]:
        """
        从分块内容中提取位置信息

        格式：@@{page}\t{x0}\t{x1}\t{top}\t{bottom}##
        """
        pattern = r"@@(\d+)\t([\d.]+)\t([\d.]+)\t([\d.]+)\t([\d.]+)##"
        matches = re.findall(pattern, chunk_content)

        positions = []
        for match in matches:
            positions.append({
                "page": int(match[0]),
                "bbox": [float(match[1]), float(match[3]), float(match[2]), float(match[4])]
            })

        return positions
```

### 方案 C：混合存储策略（Docling 模式）

**参考 Docling 的 DocChunk 结构：**

```python
from docling.chunking import DocChunk, DocChunkMetadata
from docling_core.types.doc.document import DoclingDocument

def process_with_docling(pdf_path: str) -> List[DocChunk]:
    """
    使用 Docling 处理，自动保留位置和结构
    """
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(pdf_path)

    # 获取结构化分块
    chunker = HierarchicalChunker()
    doc_chunks = list(chunker.chunk(result.document))

    # 每个 chunk 自动包含：
    # - text: 文本内容
    # - meta.headings: 标题路径
    # - meta.doc_items[0].prov[0].page_no: 页码
    # - meta.doc_items[0].prov[0].bbox: 边界框

    return doc_chunks
```

**DocChunk 输出示例：**
```python
DocChunk(
    text="本文提出一种新的深度学习架构...",
    meta=DocChunkMetadata(
        origin=Origin(filename="paper.pdf"),
        headings=["1. 引言", "1.1 背景"],
        doc_items=[
            DocItem(
                prov=[
                    ProvenanceItem(
                        page_no=2,
                        bbox=Bbox(l=50, t=200, r=400, b=350)
                    )
                ]
            )
        ]
    )
)
```

---

## 四、推荐实现方案

### 4.1 最终推荐：JSON + 位置标签注入

**核心思路**：在 Markdown 内容中注入位置标签，实现两全其美

```python
import json
from pathlib import Path
from typing import List, Dict, Any

class MinerUProcessor:
    """MinerU 输出处理器"""

    def __init__(self, chunk_size: int = 512, overlap: int = 77):
        self.chunk_size = chunk_size  # ~512 tokens
        self.overlap = overlap         # ~15-20%

    def process(self, content_list_path: str) -> List[Dict[str, Any]]:
        """
        处理 MinerU content_list.json 输出

        输出格式：
        {
            "id": "chunk_001",
            "content": "文本内容...",
            "metadata": {
                "source": "document.pdf",
                "pages": [1, 2],
                "positions": [
                    {"page": 1, "bbox": [50, 100, 400, 200]},
                    {"page": 2, "bbox": [50, 100, 400, 200]}
                ],
                "section": "1. 引言",
                "heading_path": ["1. 引言", "1.1 背景"],
                "chunk_type": "text"
            }
        }
        """
        with open(content_list_path, 'r', encoding='utf-8') as f:
            content_list = json.load(f)

        # 按页码和位置排序
        sorted_items = sorted(
            content_list,
            key=lambda x: (x.get('page_idx', 0), x.get('bbox', [0])[1] if x.get('bbox') else 0)
        )

        chunks = []
        current_chunk = self._init_chunk()
        heading_stack = []

        for item in sorted_items:
            text = item.get('text', '').strip()
            if not text:
                continue

            page = item.get('page_idx', 0)
            bbox = item.get('bbox', [0, 0, 0, 0])
            item_type = item.get('type', 'text')

            # 更新标题栈
            if item_type in ['title', 'section_header']:
                level = self._get_heading_level(item)
                # 截断到当前层级
                heading_stack = heading_stack[:level]
                heading_stack.append(text)

            # 检查是否需要分块
            if len(current_chunk['content']) + len(text) > self.chunk_size:
                if current_chunk['content']:
                    chunks.append(self._finalize_chunk(current_chunk))
                current_chunk = self._init_chunk(overlap_text=current_chunk['content'][-self.overlap:])

            # 添加内容
            current_chunk['content'] += text + '\n'
            current_chunk['positions'].append({
                'page': page,
                'bbox': bbox,
                'text_len': len(text)
            })
            current_chunk['pages'].add(page)
            current_chunk['heading_stack'] = heading_stack.copy()
            current_chunk['chunk_type'] = item_type

        # 处理最后一个分块
        if current_chunk['content'].strip():
            chunks.append(self._finalize_chunk(current_chunk))

        return chunks

    def _init_chunk(self, overlap_text: str = "") -> Dict:
        """初始化新分块"""
        return {
            'content': overlap_text,
            'positions': [],
            'pages': set(),
            'heading_stack': [],
            'chunk_type': 'text'
        }

    def _finalize_chunk(self, chunk: Dict) -> Dict[str, Any]:
        """完成分块，生成最终格式"""
        return {
            'id': f"chunk_{len(chunk['content'])}_{hash(chunk['content'][:50])}",
            'content': chunk['content'].strip(),
            'metadata': {
                'pages': sorted(list(chunk['pages'])),
                'positions': chunk['positions'],
                'section': chunk['heading_stack'][-1] if chunk['heading_stack'] else '',
                'heading_path': chunk['heading_stack'],
                'chunk_type': chunk['chunk_type']
            }
        }

    def _get_heading_level(self, item: Dict) -> int:
        """获取标题层级"""
        hierarchy = item.get('hierarchy', {})
        return hierarchy.get('level', 0)
```

### 4.2 使用示例

```python
# 初始化处理器
processor = MinerUProcessor(
    chunk_size=512,   # ~512 tokens
    overlap=77        # ~15% overlap
)

# 处理 MinerU 输出
chunks = processor.process("output/content_list.json")

# 存储到向量数据库
for chunk in chunks:
    # 存储时保留完整 metadata
    vector_store.add(
        text=chunk['content'],
        metadata=chunk['metadata'],
        id=chunk['id']
    )

# 检索时可以精确溯源
results = vector_store.search(query="评标标准")

for result in results:
    print(f"内容: {result.text[:100]}...")
    print(f"页码: {result.metadata['pages']}")
    print(f"章节: {result.metadata['section']}")
    print(f"位置: {result.metadata['positions']}")
```

### 4.3 溯源引用输出

```python
def format_citation(chunk: Dict) -> str:
    """格式化溯源引用"""
    pages = chunk['metadata']['pages']
    section = chunk['metadata']['section']

    citation = f"📄 来源：{chunk['metadata'].get('source', '未知文档')}"
    if pages:
        citation += f"，第 {', '.join(map(str, pages))} 页"
    if section:
        citation += f"，「{section}」"

    return citation

# 示例输出：
# 📄 来源：招标文件.pdf，第 5, 6 页，「2.2 技术评审标准」
```

---

## 五、RAGFlow / Docling 对比

### 5.1 位置标签生成对比

| 框架 | 位置格式 | 保留信息 |
|------|----------|----------|
| **RAGFlow** | `@@{page}\t{x0}\t{x1}\t{top}\t{bottom}##` | 页码 + bbox |
| **Docling** | `ProvenanceItem(page_no, bbox)` | 页码 + bbox + 置信度 |
| **MinerU JSON** | `{"page_idx": N, "bbox": [...]}` | 页码 + bbox |

### 5.2 推荐策略

```
┌─────────────────────────────────────────────────────────────┐
│                    文档处理流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   PDF 文档                                                  │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              MinerU 解析                             │  │
│   │  输出：content_list.json + content_list.md          │  │
│   └─────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │          MinerUProcessor 处理                        │  │
│   │  1. 从 JSON 提取位置信息 (page, bbox)                │  │
│   │  2. 按结构分块，保留标题层级                          │  │
│   │  3. 每个 chunk 携带完整 metadata                     │  │
│   └─────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│   ┌─────────────────────────────────────────────────────┐  │
│   │            LightRAG 存储                             │  │
│   │  • 向量索引：content embedding                       │  │
│   │  • 元数据过滤：page, section                         │  │
│   │  • 溯源引用：positions                               │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、最佳实践总结

### 6.1 关键原则

| 原则 | 说明 |
|------|------|
| **保留原始 JSON** | JSON 包含完整的位置信息，是溯源的基础 |
| **结构感知分块** | 按文档结构（标题、段落、表格）分块，而非固定长度 |
| **元数据继承** | 每个分块必须继承父文档的元数据 |
| **位置标签注入** | 可选：在内容中注入位置标签，实现精确溯源 |

### 6.2 Chunk 结构规范

```python
{
    "id": "chunk_xxx",
    "content": "文本内容...",
    "metadata": {
        # 必需字段
        "source": "document.pdf",      # 源文件
        "pages": [1, 2],               # 页码列表

        # 位置信息
        "positions": [
            {"page": 1, "bbox": [x0, y0, x1, y1]}
        ],

        # 结构信息
        "section": "2.2 技术评审标准",  # 当前章节
        "heading_path": ["2. 评审", "2.2 技术评审标准"],  # 标题路径

        # 类型信息
        "chunk_type": "text",          # text/table/image/formula
        "language": "zh"
    }
}
```

### 6.3 分块配置建议

| 文档类型 | Chunk Size | Overlap | 特殊处理 |
|----------|------------|---------|----------|
| **招投标文档** | 512 tokens | 15-20% | 保留表格完整性 |
| 技术参数表 | 按表格 | 0% | 整表作为一个 chunk |
| 合同/法律 | 256-512 | 20% | 按条款分块 |
| 资质证书 | 按项 | 0% | 证书信息完整保留 |

---

## 七、参考资料

**MinerU 相关：**
- [MinerU 项目地址](https://github.com/opendatalab/MinerU)
- [MinerU 终极指南](https://m.blog.csdn.net/gitblog_00575/article/details/156704229)
- [MinerU 文档体系解析](https://m.blog.csdn.net/gitblog_00611/article/details/151142665)

**RAG 分块最佳实践：**
- [RAG 文档分块策略详解](https://juejin.cn/post/7607358297457098752)
- [从 Markdown 到向量知识库](https://m.blog.csdn.net/weixin_47420447/article/details/150967394)
- [RAG 元数据管理实践](https://m.blog.csdn.net/weixin_65416248/article/details/157845039)

**Docling 参考：**
- [Docling 官方文档](https://docling-project.github.io/docling/)
- [Docling 视觉定位](https://blog.csdn.net/gitblog_00972/article/details/151146670)

---

*文档版本：v1.0*
*创建日期：2026-02-20*
