# RAGFlow 深度研究报告

> 研究对象: https://github.com/infiniflow/ragflow
> 研究日期: 2026-02-20
> 研究目的: 为辅助评标专家系统提供文档解析和 RAG 架构参考
> 项目 Star: 20k+

---

## 1. 项目概述

### 1.1 项目定位

**RAGFlow** 是一款领先的**开源 RAG（检索增强生成）引擎**，核心特性包括：

- **深度文档理解**: 基于视觉+解析器的混合方案，支持复杂文档结构
- **模板化分块**: 针对不同文档类型提供专门的分块策略
- **有据引用**: 答案生成时附带原文引用，增强可追溯性
- **Agent 能力融合**: RAG 与 Agent 能力结合，支持复杂推理任务
- **质量导向**: "Quality in, quality out" 理念，重视输入质量

### 1.2 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| **后端框架** | Flask | Python Web 框架，模块化 Blueprint 设计 |
| **前端框架** | React + TypeScript + UmiJS | 现代化前端技术栈 |
| **向量存储** | Elasticsearch / Infinity | 高性能向量检索引擎 |
| **对象存储** | MinIO | S3 兼容的对象存储服务 |
| **关系数据库** | MySQL | 结构化数据存储 |
| **缓存** | Redis | 高速缓存和会话管理 |
| **部署方式** | Docker Compose | 容器化一键部署 |
| **文档理解** | DeepDoc | 自研深度文档理解引擎 |

### 1.3 目录结构

```
RAGFlow/
├── api/                    # Flask API 服务
│   ├── apps/              # 模块化应用 (Blueprint)
│   │   ├── sdk/           # SDK 接口
│   │   ├── api/           # 公共 API
│   │   └── ...
│   ├── utils/             # 工具函数
│   └── settings.py        # 配置管理
├── rag/                   # 核心处理模块
│   ├── app/               # 文档处理应用
│   │   ├── naive.py       # 主分块逻辑
│   │   ├── qa.py          # QA 对生成
│   │   ├── book.py        # 书籍处理
│   │   ├── manual.py      # 手册处理
│   │   ├── paper.py       # 论文处理
│   │   └── ...
│   ├── nlp/               # NLP 工具
│   │   ├── __init__.py    # Tokenization, Chunk 合并
│   │   └── ...
│   ├── raptor.py          # RAPTOR 层次化聚类
│   ├── graphrag/          # GraphRAG 实现
│   ├── llm/               # LLM 集成
│   │   ├── chat_model.py  # 对话模型接口
│   │   ├── embedding_model.py  # 嵌入模型接口
│   │   └── ...
│   └── utils/             # 通用工具
├── agent/                 # Agent 系统
│   ├── component/         # 组件化工作流
│   └── ...
├── deepdoc/               # 深度文档理解引擎
│   ├── vision/            # 视觉模型 (OCR, Layout)
│   ├── parser/            # 文档解析器
│   └── ...
├── web/                   # 前端 React 应用
│   ├── src/
│   └── ...
└── docker/                # Docker 配置
    ├── docker-compose.yml
    └── ...
```

---

## 2. 文档解析 Pipeline

### 2.1 支持的文档格式

| 格式类型 | 支持格式 | 处理策略 |
|----------|----------|----------|
| **PDF** | .pdf | DeepDoc / MinerU / Docling / TCADP / PaddleOCR |
| **Word** | .docx, .doc | DOCX 解析器 |
| **Excel** | .xlsx, .csv | 表格解析器 |
| **文本** | .txt, .md, .html, .json | 纯文本解析器 |
| **图片** | .png, .jpg, .jpeg | OCR 处理 |

### 2.2 解析器架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Document Input                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Parser Selection                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│
│  │DeepDoc  │ │ MinerU  │ │ Docling │ │ TCADP   │ │PaddleOCR│
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   DeepDoc Processing                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │     OCR     │───>│   Layout    │───>│   TSR       │     │
│  │  (文字识别)  │    │  (版面分析)  │    │ (表格结构)   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Chunking Strategy                           │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────┐ ┌─────────┐│
│  │  Naive   │ │ With Images  │ │  DOCX Mode   │ │ Special ││
│  │  Merge   │ │   Context    │ │   Context    │ │ Parser  ││
│  └──────────┘ └──────────────┘ └──────────────┘ └─────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Output Chunks                              │
│  [Chunk 1 + Position] [Chunk 2 + Position] [...]            │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 解析器注册表模式

```python
# rag/app/naive.py

PARSERS = {
    "deepdoc": by_deepdoc,
    "mineru": by_mineru,
    "docling": by_docling,
    "tcadp": by_tcadp,
    "paddleocr": by_paddleocr,
    "plaintext": by_plaintext,  # default
}

def chunk(
    filename: str,
    binary=None,
    from_page: int = 0,
    to_page: int = 100000,
    lang: str = "Chinese",
    callback=None,
    **kwargs
):
    """
    主入口函数：根据文件类型选择解析器和分块策略
    """
    parser_name = kwargs.get("parser_id", "plaintext")
    parser_func = PARSERS.get(parser_name, by_plaintext)

    # 调用对应解析器
    return parser_func(
        filename, binary, from_page, to_page, lang, callback, **kwargs
    )
```

**设计亮点**:
- **策略模式**: 解析器可插拔，便于扩展
- **默认回退**: 未知解析器自动使用 plaintext
- **统一接口**: 所有解析器遵循相同签名

### 2.4 DeepDoc 模块详解

DeepDoc 是 RAGFlow 的核心文档理解引擎，包含三大能力：

#### 2.4.1 OCR (光学字符识别)

```python
# 支持 10 种布局组件
LAYOUT_COMPONENTS = [
    "Text",           # 正文文本
    "Title",          # 标题
    "Figure",         # 图片
    "Figure caption", # 图片说明
    "Table",          # 表格
    "Table caption",  # 表格说明
    "Header",         # 页眉
    "Footer",         # 页脚
    "Reference",      # 参考文献
    "Equation",       # 公式
]
```

#### 2.4.2 布局识别 (Layout Recognition)

- 自动识别文档结构
- 支持多栏布局
- 处理页眉页脚
- 识别表格位置

#### 2.4.3 表格结构识别 (TSR - Table Structure Recognition)

- 表格自动旋转（扫描 PDF 旋转校正）
- 单元格合并检测
- 表头识别
- 表格内容提取

### 2.5 分块策略详解

#### 2.5.1 Naive Merge（基础分块）

```python
# rag/nlp/__init__.py

def naive_merge(
    sections: list[tuple[str, str]],
    split_characters: list[str] = None,
    chunk_token_num: int = 128,
    delimiter: str = "\n!?;。！？；"
) -> list[tuple[str, str]]:
    """
    基础文本分块算法

    Args:
        sections: [(text, type), ...] 文本段落列表
        split_characters: 分割字符
        chunk_token_num: 目标 token 数
        delimiter: 分隔符集合

    Returns:
        [(chunk_text, chunk_type), ...]
    """
    # 1. 按分隔符拆分
    # 2. 合并到目标 token 数
    # 3. 处理边界情况
```

#### 2.5.2 Naive Merge with Images（图片上下文分块）

```python
def naive_merge_with_images(
    sections: list[tuple[str, str]],
    split_characters: list[str] = None,
    chunk_token_num: int = 128,
    delimiter: str = "\n!?;。！？；",
    image_context_size: int = 1000
) -> list[tuple[str, str, list]]:
    """
    保留图片关联的分块算法

    特性:
    - 图片信息附加到相邻文本块
    - image_context_size 控制图片描述长度
    """
```

**应用场景**: 技术文档中图片与文字混排

#### 2.5.3 Naive Merge DOCX（Word 文档专用）

```python
def naive_merge_docx(
    sections: list[tuple[str, str]],
    chunk_token_num: int = 128,
    delimiter: str = "\n!?;。！？；",
    table_context_size: int = 1000,
    image_context_size: int = 1000
) -> list[tuple[str, str, list]]:
    """
    Word 文档专用分块

    特性:
    - 表格上下文附加 (table_context_size)
    - 图片上下文附加 (image_context_size)
    - 保留原始格式信息
    """
```

### 2.6 分块配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chunk_token_num` | int | 128 | 目标 chunk token 数 |
| `delimiter` | str | "\n!?;。！？；" | 句子分隔符 |
| `overlapped_percent` | float | 0 | chunk 重叠百分比 |
| `table_context_size` | int | 1000 | 表格上下文大小 |
| `image_context_size` | int | 1000 | 图片上下文大小 |

### 2.7 位置追踪机制

```python
def add_positions(
    chunks: list[dict],
    doc_text: str,
    page_map: list[tuple[int, int, int]]
) -> list[dict]:
    """
    为每个 chunk 添加位置信息

    Args:
        chunks: 分块列表
        doc_text: 完整文档文本
        page_map: [(page_num, start_pos, end_pos), ...]

    Returns:
        chunks with positions: [{
            "content": "...",
            "positions": [(page, start, end), ...]
        }, ...]
    """
```

**应用价值**:
- 溯源引用时定位原文位置
- 支持 PDF 高亮显示
- 便于审计追溯

---

## 3. RAG 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAGFlow Architecture                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │   Document  │    │   Chunking  │    │  Embedding  │            │
│  │   Upload    │───>│   Pipeline  │───>│   Service   │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│                                                │                    │
│                                                ▼                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Vector Store (ES / Infinity)              │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │  │
│  │  │  Chunks   │  │  Vectors  │  │  Metadata │  │ Positions │ │  │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                │                    │
│                                                ▼                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │   Query     │    │  Retrieval  │    │   Rerank    │            │
│  │   Analysis  │───>│   & Rank    │───>│   (Optional)│            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│                                                │                    │
│                                                ▼                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │   Context   │    │    LLM      │    │   Answer    │            │
│  │   Assembly  │───>│  Generation │───>│  +Citation  │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 RAPTOR 实现详解

**RAPTOR** (Recursive Abstractive Processing for Tree-Organized Retrieval) 是一种层次化文档摘要技术，用于提升检索效果。

```python
# rag/raptor.py

class RecursiveAbstractiveProcessing4TreeOrganizedRetrieval:
    """
    RAPTOR: 递归抽象处理树状组织检索

    核心思想:
    1. 将文档块聚类成组
    2. 对每个组生成摘要
    3. 递归处理，形成层次树
    4. 检索时同时搜索叶节点和摘要节点
    """

    async def __call__(
        self,
        chunks: list[dict],
        embedding_model,
        llm,
        ...
    ):
        # 1. 生成嵌入向量
        embeddings = await self._get_embeddings(chunks, embedding_model)

        # 2. UMAP 降维
        reduced_embeddings = umap.UMAP(
            n_neighbors=max(2, n_neighbors),
            n_components=min(12, len(embeddings) - 2),
            metric="cosine",
        ).fit_transform(embeddings)

        # 3. GMM 聚类
        n_clusters = self._get_optimal_clusters(
            reduced_embeddings, random_state, task_id=task_id
        )

        # 4. 对每个聚类生成摘要
        for cluster_id in range(n_clusters):
            cluster_chunks = [chunks[i] for i in cluster_indices[cluster_id]]
            summary = await self._summarize(cluster_chunks, llm)

        # 5. 递归处理
        if depth < max_depth:
            await self(level + 1, summaries, ...)
```

#### 3.2.1 最优聚类数选择 (BIC)

```python
def _get_optimal_clusters(
    self,
    embeddings: np.ndarray,
    random_state: int,
    task_id: str = None
) -> int:
    """
    使用 BIC 准则选择最优聚类数

    BIC (Bayesian Information Criterion):
    - 越小越好
    - 平衡模型复杂度和拟合效果
    """
    max_clusters = min(12, len(embeddings) - 1)
    n_clusters = np.arange(1, max_clusters + 1)
    bics = []

    for n in n_clusters:
        gmm = GaussianMixture(
            n_components=n,
            covariance_type="full",
            random_state=random_state
        )
        gmm.fit(embeddings)
        bics.append(gmm.bic(embeddings))

    return n_clusters[np.argmin(bics)]
```

#### 3.2.2 RAPTOR 检索优势

```
传统检索: Query → [Chunk 1, Chunk 2, ...] → Answer

RAPTOR 检索:
                    Query
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
      [摘要层]    [摘要层]    [摘要层]
          │           │           │
    ┌─────┼─────┐     │     ┌─────┼─────┐
    ▼     ▼     ▼     ▼     ▼     ▼     ▼
  [叶]  [叶]  [叶]  [叶]  [叶]  [叶]  [叶]

同时检索摘要层和叶节点层，提升长文档检索效果
```

### 3.3 GraphRAG 实现

RAGFlow 还实现了 **GraphRAG**，利用知识图谱增强检索：

```
┌─────────────────────────────────────────────────────────┐
│                    GraphRAG Pipeline                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Documents → Entity Extraction → Graph Construction     │
│                     │                    │              │
│                     ▼                    ▼              │
│              Entity Index          Knowledge Graph      │
│                     │                    │              │
│                     └────────┬───────────┘              │
│                              ▼                          │
│                    Hybrid Retrieval                      │
│                    (Vector + Graph)                      │
│                              │                          │
│                              ▼                          │
│                    Context Fusion                        │
│                              │                          │
│                              ▼                          │
│                    LLM Generation                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**适用场景**:
- 需要理解实体关系的问题
- 多跳推理任务
- 知识密集型问答

### 3.4 嵌入模型支持

```python
# 支持的嵌入模型
EMBEDDING_MODELS = {
    # OpenAI
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",

    # 开源模型
    "BAAI/bge-large-zh-v1.5",
    "BAAI/bge-m3",
    "sentence-transformers/all-MiniLM-L6-v2",

    # 商业 API
    "cohere/embed-multilingual-v3.0",
    ...
}
```

### 3.5 检索策略

#### 3.5.1 混合检索

```python
async def hybrid_search(
    query: str,
    collection_id: str,
    top_k: int = 10,
    similarity_threshold: float = 0.1
) -> list[dict]:
    """
    混合检索: 向量相似度 + 关键词匹配
    """
    # 1. 向量检索
    vector_results = await vector_store.search(
        query, top_k=top_k * 2
    )

    # 2. 关键词检索 (BM25)
    keyword_results = await es_client.search(
        index=collection_id,
        body={
            "query": {
                "match": {"content": query}
            },
            "size": top_k * 2
        }
    )

    # 3. 融合排序 (RRF)
    return reciprocal_rank_fusion(
        vector_results, keyword_results, top_k
    )
```

#### 3.5.2 重排序 (Reranking)

```python
async def rerank(
    query: str,
    candidates: list[dict],
    rerank_model: str = "cohere/rerank-multilingual"
) -> list[dict]:
    """
    对候选结果进行重排序
    """
    # 使用专门的重排序模型
    reranked = await rerank_client.rerank(
        model=rerank_model,
        query=query,
        documents=[c["content"] for c in candidates],
        top_n=len(candidates)
    )

    return sorted_by_rerank_score(candidates, reranked)
```

### 3.6 LLM 集成架构

```python
# rag/llm/chat_model.py

class ChatModel(ABC):
    """LLM 抽象基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        **kwargs
    ) -> str:
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        **kwargs
    ) -> AsyncIterator[str]:
        pass

# 支持的 LLM 提供商
LLM_PROVIDERS = {
    "openai": OpenAIChat,
    "azure": AzureChat,
    "ollama": OllamaChat,
    "deepseek": DeepSeekChat,
    "qwen": QwenChat,
    "zhipu": ZhipuChat,
    "localai": LocalAIChat,
    ...
}
```

---

## 4. 可借鉴点

### 4.1 推荐采用的设计

#### 4.1.1 **解析器注册表模式**

```python
# 设计模式: 策略模式 + 注册表

PARSERS = {
    "deepdoc": by_deepdoc,
    "mineru": by_mineru,
    "docling": by_docling,
    # 新增解析器只需添加一行
    # "custom_parser": by_custom,
}

def chunk(filename, **kwargs):
    parser_name = kwargs.get("parser_id", "plaintext")
    return PARSERS.get(parser_name, by_plaintext)(filename, **kwargs)
```

**优点**:
- 开闭原则: 新增解析器无需修改现有代码
- 配置驱动: 通过参数选择解析器
- 易于测试: 每个解析器独立测试

**应用场景**: 评标系统需要处理多种标书格式（PDF、Word、Excel）

#### 4.1.2 **上下文附加机制**

```python
def naive_merge_docx(
    sections,
    table_context_size: int = 1000,
    image_context_size: int = 1000
):
    """
    为文本块附加表格和图片上下文
    """
    for section in sections:
        if section.type == "table":
            # 附加表格摘要到相邻文本
            context = summarize_table(section, table_context_size)
            attach_context(context)

        if section.type == "image":
            # 附加图片描述到相邻文本
            context = describe_image(section, image_context_size)
            attach_context(context)
```

**优点**:
- 解决多模态信息割裂问题
- 检索时能获取完整上下文
- 可配置上下文大小

**应用场景**: 标书中表格（报价单）和图片（资质证书）需要关联到正文

#### 4.1.3 **位置追踪系统**

```python
@dataclass
class Chunk:
    content: str
    positions: list[Position]  # [(page, start, end), ...]
    metadata: dict

def add_positions(chunks, doc_text, page_map):
    """为每个 chunk 添加精确位置"""
    for chunk in chunks:
        start = doc_text.find(chunk.content)
        chunk.positions = find_page_positions(start, page_map)
    return chunks
```

**优点**:
- 支持溯源引用
- 可高亮原文位置
- 便于审计追溯

**应用场景**: 评标报告引用标书原文时定位具体位置

#### 4.1.4 **RAPTOR 层次化检索**

```
长文档问题:
- 传统分块丢失全局上下文
- 跨块问题难以回答

RAPTOR 解决方案:
- 聚类相关块，生成摘要
- 形成树状层次结构
- 同时检索细节和摘要
```

**优点**:
- 提升长文档检索效果
- 更好的全局理解能力
- 支持多粒度问答

**应用场景**: 处理长篇标书文件（技术方案、服务承诺等）

#### 4.1.5 **混合检索 + 重排序**

```python
async def retrieve(query: str):
    # 1. 向量检索 (语义)
    vector_results = await vector_search(query)

    # 2. 关键词检索 (精确)
    keyword_results = await bm25_search(query)

    # 3. RRF 融合
    merged = reciprocal_rank_fusion(vector_results, keyword_results)

    # 4. 重排序
    reranked = await rerank(query, merged)

    return reranked
```

**优点**:
- 结合语义和精确匹配
- 重排序提升精度
- 可配置检索策略

**应用场景**: 标书检索时同时需要语义理解（技术方案）和精确匹配（价格、日期）

#### 4.1.6 **多解析器支持**

```python
# 不同场景使用不同解析器
解析器选择:
- 扫描版 PDF → DeepDoc / PaddleOCR
- 数字版 PDF → MinerU / Docling
- 复杂表格 → TCADP
- 纯文本 → PlainText
```

**优点**:
- 针对不同文档类型优化
- 灵活选择处理方式
- 成本/质量平衡

**应用场景**: 不同来源的标书文件（扫描件 vs 电子版）

### 4.2 架构设计借鉴

#### 4.2.1 **模块化处理流程**

```
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│   Upload   │───>│   Parse    │───>│   Chunk    │───>│   Index    │
│  (上传)    │    │  (解析)     │    │  (分块)     │    │  (索引)    │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
      │                 │                 │                 │
      ▼                 ▼                 ▼                 ▼
   文件存储         解析器选择        分块策略          向量化
```

**借鉴点**: 评标系统也应采用类似的流水线架构

#### 4.2.2 **DeepDoc 视觉+解析混合**

```
传统方案: PDF → 文本提取 → 分块 → 检索
问题: 丢失版面信息、表格结构

DeepDoc 方案:
PDF → OCR → 版面分析 → 表格识别 → 结构化提取 → 分块 → 检索
```

**借鉴点**: 标书处理需要保留表格结构（报价单、评分表）

#### 4.2.3 **Agent 集成**

```
RAGFlow 的 Agent 能力:
- 工作流编排
- 多步骤推理
- 外部工具调用
- 记忆管理
```

**借鉴点**: 评标流程可以设计为 Agent 工作流

### 4.3 代码模式借鉴

#### 4.3.1 **Token 感知分块**

```python
def naive_merge(sections, chunk_token_num=128):
    """基于 token 数的分块，而非字符数"""
    for section in sections:
        tokens = rag_tokenizer.tokenize(section.text)
        # 按 token 数合并
        if current_tokens + len(tokens) <= chunk_token_num:
            merge(section)
        else:
            start_new_chunk(section)
```

**优点**: 更精确控制 LLM 上下文窗口

#### 4.3.2 **分隔符智能处理**

```python
def split_with_delimiter(text, delimiter="\n!?;。！？；"):
    """
    智能分隔符处理:
    - 支持多种分隔符
    - 保留分隔符在句末
    - 处理特殊引号内的内容
    """
    # 使用正则表达式分割
    pattern = f"([{delimiter}])"
    parts = re.split(pattern, text)
    # 合并分隔符到前一个句子
    return merge_delimiters(parts)
```

#### 4.3.3 **编码自动检测**

```python
def find_codec(content: bytes) -> str:
    """
    支持 50+ 种编码自动检测
    """
    codecs = [
        'utf-8', 'gbk', 'gb2312', 'gb18030',
        'big5', 'shift_jis', 'euc-jp',
        # ... 50+ 种编码
    ]

    for codec in codecs:
        try:
            content.decode(codec)
            return codec
        except:
            continue

    return 'utf-8'  # 默认
```

**应用场景**: 处理不同编码的标书文件

### 4.4 与 Agentic-Procure-Audit-AI 的对比

| 特性 | Agentic-Procure-Audit-AI | RAGFlow |
|------|--------------------------|---------|
| **定位** | 采购审计 Agent | 通用 RAG 引擎 |
| **文档处理** | Tesseract OCR | DeepDoc (OCR + Layout + TSR) |
| **分块策略** | 基础分块 | 多种模板化分块 |
| **检索策略** | 向量检索 | 向量 + BM25 + RAPTOR |
| **LLM 框架** | LangGraph | 自研 + LangChain 兼容 |
| **Agent 能力** | RGSG 工作流 | 组件化工作流 |
| **部署复杂度** | 简单 (Ollama + ChromaDB) | 中等 (Docker Compose) |

### 4.5 对评标系统的具体建议

#### 4.5.1 **文档解析层**

```python
# 建议采用 RAGFlow 的多解析器模式
class BidDocumentParser:
    PARSERS = {
        "scanned": ScannedPDFParser,    # 扫描件
        "digital": DigitalPDFParser,    # 电子版
        "word": WordParser,             # Word 文档
        "excel": ExcelParser,           # Excel 报价单
    }

    def parse(self, file_path: str, doc_type: str):
        parser = self.PARSERS.get(doc_type, DefaultParser)
        return parser().parse(file_path)
```

#### 4.5.2 **分块策略**

```python
# 标书专用分块配置
BID_CHUNKING_CONFIG = {
    "technical_proposal": {
        "chunk_token_num": 256,      # 技术方案需要更大块
        "delimiter": "\n!?;。！？；",
        "overlapped_percent": 0.1,   # 10% 重叠
    },
    "price_table": {
        "chunk_token_num": 512,      # 报价表整块保留
        "table_context_size": 2000,  # 保留表格上下文
    },
    "qualification": {
        "chunk_token_num": 128,      # 资质文件标准分块
        "image_context_size": 500,   # 证书图片上下文
    }
}
```

#### 4.5.3 **检索策略**

```python
# 评标专用检索策略
class BidRetrieval:
    async def retrieve(self, query: str, bid_id: str):
        # 1. 从该标段的所有标书中检索
        vector_results = await self.vector_search(
            query,
            filter={"bid_id": bid_id}
        )

        # 2. 如果涉及价格，使用精确匹配
        if self._is_price_query(query):
            keyword_results = await self.exact_search(query, bid_id)

        # 3. 融合并重排序
        return await self.rerank(query, merged_results)
```

#### 4.5.4 **引用溯源**

```python
# 借鉴 RAGFlow 的位置追踪
class BidCitation:
    def cite(self, chunk: Chunk) -> Citation:
        return Citation(
            vendor_name=chunk.metadata["vendor"],
            page_number=chunk.positions[0].page,
            text_span=chunk.content[:100] + "...",
            confidence=chunk.score
        )
```

---

## 5. 技术选型对比

| 需求 | RAGFlow 方案 | 建议方案 | 理由 |
|------|-------------|----------|------|
| **向量数据库** | Elasticsearch / Infinity | ChromaDB + Elasticsearch | 小规模用 ChromaDB，大规模用 ES |
| **文档解析** | DeepDoc | DeepDoc + PaddleOCR | 中文支持好，开源 |
| **分块策略** | 模板化分块 | 自定义标书模板 | 针对标书优化 |
| **LLM 框架** | 自研 + LangChain | LangGraph | 状态管理清晰 |
| **嵌入模型** | 多模型支持 | BAAI/bge-large-zh-v1.5 | 中文效果好 |
| **部署方式** | Docker Compose | Docker + K8s | 开发用 Docker，生产用 K8s |

---

## 6. 总结

### 6.1 RAGFlow 核心价值

1. **深度文档理解**: DeepDoc 模块提供 OCR + 布局分析 + 表格识别一体化方案
2. **灵活分块策略**: 模板化分块，支持多种文档类型
3. **高级检索技术**: RAPTOR + GraphRAG + 混合检索
4. **位置追踪**: 支持精确溯源引用
5. **模块化架构**: 解析器可插拔，易于扩展

### 6.2 可直接复用的模块

| 模块 | 复用价值 | 复用方式 |
|------|----------|----------|
| DeepDoc | 高 | 直接集成或参考实现 |
| 分块算法 | 高 | 参考实现思路 |
| 位置追踪 | 中 | 参考数据结构 |
| RAPTOR | 中 | 视需求引入 |
| 解析器注册表 | 高 | 直接采用设计模式 |

### 6.3 不建议采用的部分

1. **Flask 框架**: 对于 Agent 系统，LangGraph 更合适
2. **Elasticsearch 强依赖**: 小规模场景 ChromaDB 更轻量
3. **复杂的 Docker 部署**: 开发阶段可用简化方案

---

## 7. 参考资源

- [RAGFlow GitHub](https://github.com/infiniflow/ragflow)
- [RAGFlow 官方文档](https://ragflow.io/docs/)
- [DeepDoc 技术介绍](https://github.com/infiniflow/ragflow/tree/main/deepdoc)
- [RAPTOR 论文](https://arxiv.org/abs/2401.18059)
- [CLAUDE.md 项目指南](https://github.com/infiniflow/ragflow/blob/main/CLAUDE.md)

---

*报告完成于 2026-02-20*
