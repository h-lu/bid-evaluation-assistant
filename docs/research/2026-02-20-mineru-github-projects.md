# GitHub 上使用 MinerU 解析文档的项目研究

> 研究日期：2026-02-20
> 研究范围：GitHub 上使用 MinerU 输出进行文档解析、分块、向量化的项目
> 数据来源：Web Search、GitHub

---

## 一、核心发现

### 1.1 GitHub 项目汇总

| 项目 | Stars | 描述 | 与 MinerU 集成方式 |
|------|-------|------|-------------------|
| **[MinerU](https://github.com/opendatalab/MinerU)** | 50k+ | 官方仓库，PDF 解析核心 | 直接使用 |
| **[Yuxi-Know](https://github.com/xerrors/Yuxi-Know)** | 3.4k+ | LightRAG + LangGraph 知识库平台 | PDF 解析后接入 |
| **[RAG-Anything](https://github.com/HKUDS/RAG-Anything)** | 6.8k+ | 港大多模态 RAG 框架 | MinerU + Docling 自动选择 |
| **LazyLLM** | - | RAG 框架，内置 MinerU Reader | 内置 MineruPDFReader |
| **Markify** | - | 文档解析服务 | MinerU + markitdown 组合 |

### 1.2 集成方式对比

| 集成方式 | 项目 | 复杂度 | 推荐场景 |
|----------|------|--------|----------|
| **直接调用 CLI** | 通用 | 低 | 简单场景，批量处理 |
| **Python API** | MinerU 官方 | 中 | 需要精细控制 |
| **自定义 Reader** | LazyLLM | 中 | LangChain/LlamaIndex 集成 |
| **服务化部署** | Yuxi-Know | 高 | 企业级生产环境 |

---

## 二、重点项目详解

### 2.1 Yuxi-Know（强烈推荐 ⭐⭐⭐⭐⭐）

**项目地址**: https://github.com/xerrors/Yuxi-Know

**技术栈**:
```
┌─────────────────────────────────────────────────────────────┐
│                    Yuxi-Know 架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   前端: Vue.js                                              │
│   后端: FastAPI + LangGraph v1                              │
│   RAG:   LightRAG（双层检索 + 知识图谱）                     │
│   解析:  MinerU / PP-Structure                              │
│   图库:  Neo4j                                              │
│   向量:  Milvus / ChromaDB                                  │
│   协议:  MCP（Model Context Protocol）                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**与我们系统的相似度**: 90%+
- ✅ LightRAG 作为 RAG 引擎
- ✅ LangGraph 作为工作流编排
- ✅ MinerU 作为 PDF 解析
- ✅ FastAPI 后端
- ✅ 知识图谱支持

**可借鉴内容**:
1. MinerU 解析后的文档处理流程
2. LightRAG 与 LangGraph 的集成方式
3. 位置信息保留与溯源引用

### 2.2 RAG-Anything

**项目地址**: https://github.com/HKUDS/RAG-Anything

**特点**: 自动选择最佳解析器

```python
from raganything import RAGAnything

# 自动选择解析器
rag = RAGAnything(
    storage_path="./rag_storage",
    parser="auto",  # 自动选择 MinerU 或 Docling
    parse_method="auto",
)
```

**解析器选择逻辑**:
```
文档输入
    │
    ├── 复杂布局 PDF? ───→ MinerU
    │
    ├── Office 文档? ────→ Docling
    │
    └── 标准格式? ───────→ Docling
```

### 2.3 LazyLLM MinerU Reader

**集成方式**: 内置 MineruPDFReader

```python
from lazyllm.tools.rag import Document
from lazyllm.tools.rag.readers import MineruPDFReader

# 创建文档实例
documents = lazyllm.Document(dataset_path="./docs")

# 注册 MinerU 作为 PDF Reader
documents.add_reader("*.pdf", MineruPDFReader(
    url="http://localhost:8000"  # MinerU 服务地址
))

# 读取并解析
data = documents.read()
```

**部署 MinerU 服务**:
```bash
# 安装
lazyllm install mineru

# 部署服务
lazyllm deploy mineru --port 8000 --cache_dir ./cache
```

---

## 三、MinerU 输出处理最佳实践

### 3.1 官方推荐的输出格式

| 文件 | 用途 | 是否推荐用于 RAG |
|------|------|-----------------|
| `content_list.json` | 简化版结构化内容 | ✅ **推荐** |
| `middle.json` | 完整中间态数据 | ⚠️ 包含过多信息 |
| `*.md` | Markdown 输出 | ⚠️ 缺少位置信息 |

### 3.2 content_list.json 结构

```json
[
  {
    "text": "提取的文本内容",
    "type": "text",
    "page_idx": 1,
    "bbox": [50, 100, 400, 200]
  },
  {
    "text": "| 列1 | 列2 |\n|-----|-----|\n| A | B |",
    "type": "table",
    "page_idx": 2,
    "bbox": [50, 100, 500, 300]
  }
]
```

### 3.3 处理流程（来自 Yuxi-Know）

```python
import json
from typing import List, Dict, Any

class MinerUDocumentProcessor:
    """处理 MinerU content_list.json 输出"""

    def __init__(self, chunk_size: int = 512, overlap: int = 77):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process_content_list(self, content_list_path: str) -> List[Dict]:
        """处理 content_list.json"""
        with open(content_list_path, 'r', encoding='utf-8') as f:
            items = json.load(f)

        chunks = []
        current_chunk = {
            "content": "",
            "metadata": {
                "pages": set(),
                "positions": [],
                "types": set()
            }
        }
        current_section = ""

        for item in items:
            text = item.get("text", "").strip()
            if not text:
                continue

            page = item.get("page_idx", 0)
            bbox = item.get("bbox", [0, 0, 0, 0])
            item_type = item.get("type", "text")

            # 更新章节（如果是标题）
            if item_type in ["title", "section_header"]:
                current_section = text

            # 检查是否需要分块
            if len(current_chunk["content"]) + len(text) > self.chunk_size:
                if current_chunk["content"]:
                    chunks.append(self._finalize_chunk(
                        current_chunk,
                        section=current_section
                    ))
                # 新分块（带 overlap）
                overlap_text = current_chunk["content"][-self.overlap:]
                current_chunk = {
                    "content": overlap_text + text + "\n",
                    "metadata": {
                        "pages": {page},
                        "positions": [{"page": page, "bbox": bbox}],
                        "types": {item_type}
                    }
                }
            else:
                current_chunk["content"] += text + "\n"
                current_chunk["metadata"]["pages"].add(page)
                current_chunk["metadata"]["positions"].append({
                    "page": page,
                    "bbox": bbox
                })
                current_chunk["metadata"]["types"].add(item_type)

        # 处理最后一个分块
        if current_chunk["content"].strip():
            chunks.append(self._finalize_chunk(
                current_chunk,
                section=current_section
            ))

        return chunks

    def _finalize_chunk(self, chunk: Dict, section: str = "") -> Dict:
        """完成分块"""
        return {
            "content": chunk["content"].strip(),
            "metadata": {
                "pages": sorted(list(chunk["metadata"]["pages"])),
                "positions": chunk["metadata"]["positions"],
                "types": list(chunk["metadata"]["types"]),
                "section": section
            }
        }
```

### 3.4 接入 LightRAG

```python
from lightrag import LightRAG
from lightrag.llm import openai_complete_if_cache, openai_embedding

# 初始化 LightRAG
rag = LightRAG(
    working_dir="./rag_storage",
    llm_model_func=openai_complete_if_cache,
    embedding_func=openai_embedding
)

# 处理 MinerU 输出
processor = MinerUDocumentProcessor(chunk_size=512, overlap=77)
chunks = processor.process_content_list("output/content_list.json")

# 插入到 LightRAG
for chunk in chunks:
    rag.insert(
        chunk["content"],
        metadata=chunk["metadata"]  # 保留元数据
    )
```

---

## 四、LangChain / LlamaIndex 集成

### 4.1 LangChain 自定义 Loader

```python
from langchain.docstore.document import Document
from typing import List, Optional
import subprocess
import json
import os

class MinerUPDFLoader:
    """MinerU PDF Loader for LangChain"""

    def __init__(
        self,
        file_path: str,
        output_dir: str = "./mineru_output",
        parse_method: str = "auto"
    ):
        self.file_path = file_path
        self.output_dir = output_dir
        self.parse_method = parse_method

    def load(self) -> List[Document]:
        """解析 PDF 并返回 LangChain Document 列表"""

        # 1. 调用 MinerU 解析
        subprocess.run([
            "magic-pdf",
            "-p", self.file_path,
            "-o", self.output_dir,
            "-m", self.parse_method
        ], check=True)

        # 2. 读取 content_list.json
        filename = os.path.basename(self.file_path).replace(".pdf", "")
        content_list_path = os.path.join(
            self.output_dir, filename, "content_list.json"
        )

        with open(content_list_path, 'r', encoding='utf-8') as f:
            items = json.load(f)

        # 3. 转换为 LangChain Document
        documents = []
        for item in items:
            doc = Document(
                page_content=item.get("text", ""),
                metadata={
                    "source": self.file_path,
                    "page": item.get("page_idx", 0),
                    "bbox": item.get("bbox", []),
                    "type": item.get("type", "text")
                }
            )
            documents.append(doc)

        return documents


# 使用示例
from langchain.text_splitter import RecursiveCharacterTextSplitter

loader = MinerUPDFLoader("bid_document.pdf")
documents = loader.load()

# 分块
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=77
)
chunks = splitter.split_documents(documents)
```

### 4.2 LlamaIndex 自定义 Reader

```python
from llama_index.core import Document
from llama_index.core.readers.base import BaseReader
from typing import List, Optional
import subprocess
import json
import os

class MinerUPDFReader(BaseReader):
    """MinerU PDF Reader for LlamaIndex"""

    def __init__(
        self,
        output_dir: str = "./mineru_output",
        parse_method: str = "auto",
        keep_position_metadata: bool = True
    ):
        self.output_dir = output_dir
        self.parse_method = parse_method
        self.keep_position_metadata = keep_position_metadata

    def load_data(
        self,
        file_path: str,
        extra_info: Optional[dict] = None
    ) -> List[Document]:
        """加载 PDF 并返回 LlamaIndex Document 列表"""

        # 调用 MinerU
        subprocess.run([
            "magic-pdf",
            "-p", file_path,
            "-o", self.output_dir,
            "-m", self.parse_method
        ], check=True)

        # 读取输出
        filename = os.path.basename(file_path).replace(".pdf", "")
        content_list_path = os.path.join(
            self.output_dir, filename, "content_list.json"
        )

        with open(content_list_path, 'r', encoding='utf-8') as f:
            items = json.load(f)

        # 转换
        documents = []
        extra_info = extra_info or {}

        for item in items:
            metadata = {
                "source": file_path,
                **extra_info
            }

            if self.keep_position_metadata:
                metadata["page"] = item.get("page_idx", 0)
                metadata["bbox"] = str(item.get("bbox", []))
                metadata["content_type"] = item.get("type", "text")

            doc = Document(
                text=item.get("text", ""),
                metadata=metadata
            )
            documents.append(doc)

        return documents


# 使用示例
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

reader = MinerUPDFReader(keep_position_metadata=True)
documents = reader.load_data("bid_document.pdf")

# 分块
parser = SentenceSplitter(chunk_size=512, chunk_overlap=77)
nodes = parser.get_nodes_from_documents(documents)

# 建立索引
index = VectorStoreIndex(nodes)
```

---

## 五、推荐方案

### 5.1 基于我们的架构（模块化单体 + LightRAG）

```
┌─────────────────────────────────────────────────────────────┐
│                    推荐架构                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   src/modules/documents/                                    │
│   ├── infrastructure/                                       │
│   │   ├── parsers/                                          │
│   │   │   ├── mineru_parser.py      # MinerU 封装           │
│   │   │   └── docling_parser.py     # Docling 封装          │
│   │   └── chunkers/                                         │
│   │       └── structure_aware_chunker.py  # 结构感知分块    │
│   │                                                         │
│   src/modules/retrieval/                                    │
│   ├── infrastructure/                                       │
│   │   └── lightrag/                                         │
│   │       └── lightrag_adapter.py    # LightRAG 适配器      │
│   │                                                         │
│   数据流:                                                   │
│   PDF → MinerU → content_list.json → 结构感知分块           │
│       → LightRAG → 检索 + 溯源                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 关键借鉴点

| 借鉴来源 | 借鉴内容 |
|----------|----------|
| **Yuxi-Know** | LightRAG + LangGraph 集成模式 |
| **RAG-Anything** | 解析器自动选择策略 |
| **LazyLLM** | Reader 组件设计模式 |
| **MinerU 官方** | content_list.json 结构 |

### 5.3 实现优先级

1. **Phase 1**: 实现 MinerUParser 封装
2. **Phase 2**: 实现 StructureAwareChunker（保留位置信息）
3. **Phase 3**: 接入 LightRAG
4. **Phase 4**: 实现溯源引用

---

## 六、参考资料

**GitHub 项目：**
- [MinerU 官方](https://github.com/opendatalab/MinerU)
- [Yuxi-Know](https://github.com/xerrors/Yuxi-Know)
- [RAG-Anything](https://github.com/HKUDS/RAG-Anything)
- [GitHub MinerU Topics](https://github.com/topics/mineru)

**集成教程：**
- [MinerU RAG 最佳实践](https://m.blog.csdn.net/IndigoNight21/article/details/157010168)
- [LazyLLM MinerU Reader](https://github.com/LazyAGI/Tutorial)
- [LightRAG × Yuxi-Know 实战](https://blog.csdn.net/weixin_58753619/article/details/153477219)

---

*文档版本：v1.0*
*创建日期：2026-02-20*
