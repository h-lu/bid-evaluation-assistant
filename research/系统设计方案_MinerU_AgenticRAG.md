# 辅助评标专家系统 —— 系统设计方案

> 基于MinerU API + Agentic RAG的完整系统设计
> 设计时间：2026年2月20日

---

## 一、系统概述

### 1.1 设计目标

构建一个智能评标助手系统，实现：
- **投标文件智能解析**：使用MinerU API将PDF投标文件转为结构化数据
- **合规性自动审查**：基于RAG检索法规库，自动进行资格审查和符合性审查
- **智能评分建议**：多Agent协作完成客观分计算和主观分建议
- **可解释性输出**：提供评分依据和原文溯源

### 1.2 技术栈选型

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **文档解析** | MinerU API / PaddleOCR | PDF解析、扫描件识别 |
| **向量数据库** | ChromaDB | 本地部署，轻量级 |
| **RAG框架** | LangChain + LangGraph | 检索增强、状态管理 |
| **Agent框架** | CrewAI / LangGraph | 多智能体协作 |
| **LLM** | DeepSeek / GPT-4 | 大语言模型推理 |
| **后端API** | FastAPI | 高性能异步框架 |
| **前端** | Vue3 + Element Plus | 评标专家界面 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           评标专家界面 (Vue3)                                 │
│                    文件上传 │ 评审工作台 │ 评分对比 │ 报告导出                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Gateway (FastAPI)                              │
│                    鉴权 │ 限流 │ 审计日志 │ 权限控制                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
┌───────────────────┐        ┌───────────────────┐        ┌───────────────────┐
│   文档处理服务     │        │    Agent服务       │        │    知识库服务      │
│                   │        │                   │        │                   │
│ ┌───────────────┐ │        │ ┌───────────────┐ │        │ ┌───────────────┐ │
│ │ MinerU Parser │ │        │ │ Supervisor    │ │        │ │ ChromaDB      │ │
│ │ (PDF→JSON)    │ │        │ │ Agent         │ │        │ │ (向量存储)    │ │
│ └───────────────┘ │        │ └───────┬───────┘ │        │ └───────────────┘ │
│ ┌───────────────┐ │        │         │         │        │ ┌───────────────┐ │
│ │ Chunker       │ │        │ ▼       ▼       ▼ │        │ │ BM25 Index    │ │
│ │ (文档分块)    │ │        │合规   技术   商务  │        │ │ (关键词检索)  │ │
│ └───────────────┘ │        │Agent  Agent  Agent│        │ └───────────────┘ │
│ ┌───────────────┐ │        │                   │        │                   │
│ │ InfoExtractor │ │        │ ┌───────────────┐ │        │ ┌───────────────┐ │
│ │ (信息提取)    │ │        │ │ 对比分析Agent │ │        │ │ 法规知识库    │ │
│ └───────────────┘ │        │ └───────────────┘ │        │ └───────────────┘ │
└───────────────────┘        └───────────────────┘        └───────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LLM服务 (DeepSeek / GPT-4)                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流架构

```
投标文件(PDF)
     │
     ▼
┌─────────────────┐
│   MinerU API    │  ──→  content_list.json
│   文档解析      │  ──→  middle.json
└─────────────────┘  ──→  images/
     │
     ▼
┌─────────────────┐
│   Chunker       │  ──→  结构化文档块
│   文档分块      │        (带元数据)
└─────────────────┘
     │
     ├──────────────────────────────┐
     ▼                              ▼
┌─────────────────┐        ┌─────────────────┐
│   向量化        │        │   信息提取      │
│   Embedding     │        │   LLM Extract   │
└─────────────────┘        └─────────────────┘
     │                              │
     ▼                              ▼
┌─────────────────┐        ┌─────────────────┐
│   ChromaDB      │        │   结构化数据    │
│   向量存储      │        │   (资质/业绩/报价)│
└─────────────────┘        └─────────────────┘
     │                              │
     └──────────────┬───────────────┘
                    ▼
           ┌─────────────────┐
           │  Agent处理      │
           │  多智能体协作    │
           └─────────────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  评审报告输出    │
           └─────────────────┘
```

---

## 三、核心模块设计

### 3.1 文档解析模块（MinerU集成）

#### 3.1.1 MinerU API调用

```python
# src/document/mineru_parser.py

import httpx
from pathlib import Path
from typing import Optional
import json

class MinerUParser:
    """MinerU文档解析器"""

    def __init__(self, api_key: str, base_url: str = "https://mineru.net/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)

    async def parse_pdf(
        self,
        pdf_path: str,
        output_dir: str,
        parse_method: str = "auto",
        enable_formula: bool = True,
        enable_table: bool = True
    ) -> dict:
        """
        解析PDF文件

        Returns:
            {
                'content_list': [...],  # 简化结构
                'middle_json': {...},   # 完整结构
                'markdown': str,        # Markdown文本
                'images': [str]         # 图片路径列表
            }
        """
        url = f"{self.base_url}/extract"

        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with aiofiles.open(pdf_path, 'rb') as f:
            file_content = await f.read()

        files = {'file': (Path(pdf_path).name, file_content, 'application/pdf')}
        data = {
            'parse_method': parse_method,
            'formula_enable': str(enable_formula).lower(),
            'table_enable': str(enable_table).lower(),
            'return_markdown': 'true'
        }

        response = await self.client.post(
            url,
            headers=headers,
            files=files,
            data=data
        )

        if response.status_code != 200:
            raise Exception(f"MinerU API调用失败: {response.text}")

        result = response.json()

        # 保存结果
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        pdf_name = Path(pdf_path).stem

        # 保存content_list.json
        content_list = result.get('content_list', [])
        with open(output_path / f"{pdf_name}_content_list.json", 'w', encoding='utf-8') as f:
            json.dump(content_list, f, ensure_ascii=False, indent=2)

        # 保存middle.json
        middle_json = result.get('middle_json', {})
        with open(output_path / f"{pdf_name}_middle.json", 'w', encoding='utf-8') as f:
            json.dump(middle_json, f, ensure_ascii=False, indent=2)

        return {
            'content_list': content_list,
            'middle_json': middle_json,
            'markdown': result.get('markdown', ''),
            'images': result.get('images', [])
        }

    async def batch_parse(self, pdf_paths: list[str], output_dir: str) -> list[dict]:
        """批量解析PDF文件"""
        tasks = [self.parse_pdf(pdf, output_dir) for pdf in pdf_paths]
        return await asyncio.gather(*tasks)
```

#### 3.1.2 Content List处理器

```python
# src/document/content_processor.py

from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ContentBlock:
    """内容块"""
    type: str           # text, title, table, image
    content: str        # 文本内容
    page_idx: int       # 页码
    level: int = 0      # 标题级别
    bbox: list = None   # 边界框
    image_path: str = None  # 图片路径

class ContentListProcessor:
    """Content List处理器"""

    def __init__(self, content_list: List[Dict]):
        self.content_list = content_list
        self.blocks = self._parse_blocks()

    def _parse_blocks(self) -> List[ContentBlock]:
        """解析内容块"""
        blocks = []
        for item in self.content_list:
            block = ContentBlock(
                type=item.get('type', 'text'),
                content=item.get('text', ''),
                page_idx=item.get('page_idx', 0),
                level=item.get('level', 0),
                bbox=item.get('bbox'),
                image_path=item.get('img_path')
            )
            blocks.append(block)
        return blocks

    def extract_text(self) -> str:
        """提取纯文本"""
        texts = []
        for block in self.blocks:
            if block.type == 'text':
                texts.append(block.content)
            elif block.type == 'title':
                prefix = '#' * block.level if block.level else '#'
                texts.append(f"\n{prefix} {block.content}\n")
        return '\n'.join(texts)

    def extract_structure(self) -> Dict[str, Any]:
        """提取文档结构"""
        structure = {
            'titles': [],
            'tables': [],
            'images': [],
            'sections': []
        }

        current_section = None

        for block in self.blocks:
            if block.type == 'title':
                if current_section:
                    structure['sections'].append(current_section)
                current_section = {
                    'title': block.content,
                    'level': block.level,
                    'page': block.page_idx,
                    'content': []
                }
                structure['titles'].append({
                    'text': block.content,
                    'level': block.level,
                    'page': block.page_idx
                })
            elif block.type == 'table':
                structure['tables'].append({
                    'page': block.page_idx,
                    'image_path': block.image_path
                })
                if current_section:
                    current_section['content'].append({
                        'type': 'table',
                        'page': block.page_idx
                    })
            elif block.type == 'image':
                structure['images'].append({
                    'page': block.page_idx,
                    'image_path': block.image_path
                })
            elif block.type == 'text' and current_section:
                current_section['content'].append({
                    'type': 'text',
                    'text': block.content[:100] + '...'  # 摘要
                })

        if current_section:
            structure['sections'].append(current_section)

        return structure

    def get_sections_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """根据关键词提取相关章节"""
        results = []
        for block in self.blocks:
            if block.type == 'title':
                for kw in keywords:
                    if kw in block.content:
                        results.append({
                            'title': block.content,
                            'page': block.page_idx
                        })
                        break
        return results
```

### 3.2 RAG检索模块

#### 3.2.1 混合检索器

```python
# src/rag/hybrid_retriever.py

from langchain.vectorstores import ChromaDB
from langchain.embeddings import OpenAIEmbeddings
from rank_bm25 import BM25Okapi
import jieba
from typing import List, Tuple

class HybridRetriever:
    """混合检索器：向量检索 + BM25"""

    def __init__(
        self,
        persist_directory: str,
        embedding_model: str = "text-embedding-3-small"
    ):
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        self.vectorstore = ChromaDB(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )
        self.bm25_index = None
        self.documents = []

    def build_bm25_index(self, documents: List[str]):
        """构建BM25索引"""
        tokenized_docs = [list(jieba.cut(doc)) for doc in documents]
        self.bm25_index = BM25Okapi(tokenized_docs)
        self.documents = documents

    def search(
        self,
        query: str,
        k: int = 10,
        alpha: float = 0.5
    ) -> List[Tuple[str, float]]:
        """
        混合检索

        Args:
            query: 查询文本
            k: 返回数量
            alpha: 向量检索权重 (1-alpha为BM25权重)
        """
        # 1. 向量检索
        vec_results = self.vectorstore.similarity_search_with_score(query, k=k*2)

        # 2. BM25检索
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25_index.get_scores(tokenized_query)

        # 3. RRF融合
        fused_results = self._reciprocal_rank_fusion(
            vec_results,
            bm25_scores,
            k=60,
            alpha=alpha
        )

        return fused_results[:k]

    def _reciprocal_rank_fusion(
        self,
        vec_results: List,
        bm25_scores: List[float],
        k: int = 60,
        alpha: float = 0.5
    ) -> List[Tuple[str, float]]:
        """倒数排名融合"""
        scores = {}

        # 向量检索分数
        for rank, (doc, score) in enumerate(vec_results):
            doc_id = doc.metadata.get('id', str(hash(doc.page_content)))
            scores[doc_id] = {
                'doc': doc,
                'score': alpha * (1.0 / (k + rank + 1))
            }

        # BM25分数
        ranked_bm25 = sorted(
            enumerate(bm25_scores),
            key=lambda x: x[1],
            reverse=True
        )[:len(vec_results)]

        for rank, (idx, score) in enumerate(ranked_bm25):
            doc_id = str(idx)
            if doc_id in scores:
                scores[doc_id]['score'] += (1 - alpha) * (1.0 / (k + rank + 1))
            else:
                scores[doc_id] = {
                    'doc': self.documents[idx],
                    'score': (1 - alpha) * (1.0 / (k + rank + 1))
                }

        # 排序返回
        sorted_results = sorted(
            scores.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )

        return [(item[1]['doc'], item[1]['score']) for item in sorted_results]
```

#### 3.2.2 文档分块策略

```python
# src/rag/chunker.py

from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Chunk:
    """文档块"""
    content: str
    metadata: Dict
    chunk_id: str

class BidDocumentChunker:
    """投标文档专用分块器"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_content_list(
        self,
        content_list: List[Dict],
        doc_metadata: Dict
    ) -> List[Chunk]:
        """
        基于content_list的分块策略
        保留文档结构信息
        """
        chunks = []
        current_chunk_text = []
        current_size = 0
        current_metadata = {
            'doc_id': doc_metadata.get('doc_id'),
            'doc_name': doc_metadata.get('doc_name'),
            'section': None,
            'start_page': 0,
            'end_page': 0
        }

        for item in content_list:
            item_type = item.get('type', 'text')
            page_idx = item.get('page_idx', 0)

            if item_type == 'title':
                # 标题：保存当前块，开启新块
                if current_chunk_text:
                    chunks.append(self._create_chunk(
                        current_chunk_text,
                        current_metadata
                    ))
                    current_chunk_text = []

                # 更新章节信息
                current_metadata['section'] = item.get('text', '')
                current_metadata['start_page'] = page_idx
                current_size = 0

            elif item_type == 'text':
                text = item.get('text', '')
                text_len = len(text)

                if current_size + text_len > self.chunk_size:
                    # 块已满
                    if current_chunk_text:
                        chunks.append(self._create_chunk(
                            current_chunk_text,
                            current_metadata
                        ))
                        # 保留重叠
                        current_chunk_text = self._get_overlap(current_chunk_text)
                        current_size = sum(len(t) for t in current_chunk_text)

                current_chunk_text.append(text)
                current_size += text_len
                current_metadata['end_page'] = page_idx

            elif item_type == 'table':
                # 表格单独成块
                table_chunk = Chunk(
                    content=f"[表格：第{page_idx + 1}页]",
                    metadata={
                        **current_metadata,
                        'type': 'table',
                        'page': page_idx,
                        'image_path': item.get('img_path')
                    },
                    chunk_id=f"{doc_metadata.get('doc_id')}_table_{page_idx}"
                )
                chunks.append(table_chunk)

        # 保存最后一个块
        if current_chunk_text:
            chunks.append(self._create_chunk(
                current_chunk_text,
                current_metadata
            ))

        return chunks

    def _create_chunk(
        self,
        texts: List[str],
        metadata: Dict
    ) -> Chunk:
        """创建文档块"""
        content = '\n'.join(texts)
        return Chunk(
            content=content,
            metadata={
                **metadata,
                'type': 'text',
                'char_count': len(content)
            },
            chunk_id=f"{metadata.get('doc_id')}_{metadata.get('start_page')}_{hash(content) % 10000}"
        )

    def _get_overlap(self, texts: List[str]) -> List[str]:
        """获取重叠内容"""
        overlap_texts = []
        total_len = 0

        for text in reversed(texts):
            if total_len + len(text) > self.chunk_overlap:
                break
            overlap_texts.insert(0, text)
            total_len += len(text)

        return overlap_texts
```

### 3.3 多智能体模块

#### 3.3.1 状态定义（LangGraph）

```python
# src/agents/state.py

from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import add_messages

class BidDocument(TypedDict):
    """投标文档结构"""
    doc_id: str
    company_name: str
    content_list: List[Dict]
    extracted_info: Dict

class ReviewResult(TypedDict):
    """审查结果"""
    passed: bool
    items: List[Dict]
    warnings: List[str]
    confidence: float

class AgentState(TypedDict):
    """Agent状态"""
    # 输入
    tender_id: str
    tender_requirements: Dict          # 招标要求
    bid_documents: List[BidDocument]   # 投标文件列表

    # 中间状态
    messages: Annotated[list, add_messages]
    current_stage: str                 # 当前阶段
    extracted_data: Dict               # 提取的结构化数据

    # 各Agent输出
    compliance_result: Optional[ReviewResult]     # 合规审查结果
    technical_result: Optional[ReviewResult]      # 技术评审结果
    commercial_result: Optional[ReviewResult]     # 商务评审结果

    # 评分
    objective_scores: Optional[Dict]              # 客观分
    subjective_suggestions: Optional[Dict]        # 主观分建议

    # 对比分析
    comparison_result: Optional[Dict]

    # 最终输出
    final_report: Optional[Dict]

    # 控制流
    next_agent: str
    errors: List[str]
```

#### 3.3.2 Supervisor Agent

```python
# src/agents/supervisor.py

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import Literal

from .state import AgentState

class SupervisorAgent:
    """Supervisor Agent - 任务协调者"""

    def __init__(self, llm):
        self.llm = llm
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建工作流图"""
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("extractor", self.extractor_node)
        workflow.add_node("compliance", self.compliance_node)
        workflow.add_node("technical", self.technical_node)
        workflow.add_node("commercial", self.commercial_node)
        workflow.add_node("comparison", self.comparison_node)
        workflow.add_node("scoring", self.scoring_node)
        workflow.add_node("reporter", self.reporter_node)

        # 设置入口
        workflow.set_entry_point("supervisor")

        # 添加条件边
        workflow.add_conditional_edges(
            "supervisor",
            self._route_next,
            {
                "extract": "extractor",
                "compliance": "compliance",
                "technical": "technical",
                "commercial": "commercial",
                "comparison": "comparison",
                "scoring": "scoring",
                "report": "reporter",
                "finish": END
            }
        )

        # 所有子节点返回supervisor
        for node in ["extractor", "compliance", "technical", "commercial", "comparison", "scoring", "reporter"]:
            workflow.add_edge(node, "supervisor")

        return workflow.compile()

    def supervisor_node(self, state: AgentState) -> dict:
        """Supervisor决策节点"""
        # 决策下一步
        prompt = f"""
        当前评标状态：
        - 阶段：{state.get('current_stage', 'init')}
        - 已完成合规审查：{state.get('compliance_result') is not None}
        - 已完成技术评审：{state.get('technical_result') is not None}
        - 已完成商务评审：{state.get('commercial_result') is not None}
        - 已完成对比分析：{state.get('comparison_result') is not None}
        - 已完成评分：{state.get('objective_scores') is not None}

        请决定下一步操作：
        - extract: 提取投标文件关键信息
        - compliance: 执行合规审查
        - technical: 执行技术评审
        - commercial: 执行商务评审
        - comparison: 执行多投标方对比
        - scoring: 计算评分
        - report: 生成最终报告
        - finish: 完成

        只返回一个单词。
        """

        response = self.llm.invoke(prompt)
        next_action = response.content.strip().lower()

        return {"next_agent": next_action}

    def _route_next(self, state: AgentState) -> str:
        """路由决策"""
        next_agent = state.get("next_agent", "extract")

        # 检查合规审查是否通过
        if state.get("compliance_result"):
            if not state["compliance_result"].get("passed", True):
                # 合规不通过，直接生成报告
                return "report"

        return next_agent
```

#### 3.3.3 合规审查Agent

```python
# src/agents/compliance_agent.py

from langchain.tools import tool
from typing import List, Dict
from pydantic import BaseModel, Field

class ComplianceCheckItem(BaseModel):
    """合规检查项"""
    item_name: str = Field(description="检查项名称")
    requirement: str = Field(description="要求说明")
    bid_response: str = Field(description="投标响应")
    passed: bool = Field(description="是否通过")
    evidence_page: int = Field(description="证据页码")
    confidence: float = Field(description="置信度")

class ComplianceAgent:
    """合规审查Agent"""

    SYSTEM_PROMPT = """
    你是医疗器械招投标合规审查专家。
    你的职责是对照招标文件要求，审查投标文件的合规性。

    审查流程：
    1. 读取招标文件的资格审查要求
    2. 从投标文件中查找对应证明材料
    3. 判断是否符合要求
    4. 记录证据位置（页码）
    5. 给出置信度评分

    注意事项：
    - 资格审查项必须100%符合，否则废标
    - 实质性要求(★号条款)必须响应
    - 所有判断必须有证据支撑
    """

    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever
        self.tools = self._init_tools()

    def _init_tools(self):
        @tool
        def search_regulation(query: str) -> str:
            """检索相关法规条文"""
            results = self.retriever.search(query, k=3)
            return "\n".join([r[0].page_content for r in results])

        @tool
        def find_in_document(doc_id: str, keyword: str) -> List[Dict]:
            """在投标文件中查找关键词"""
            # 实现文档内搜索
            pass

        @tool
        def verify_license(license_no: str, license_type: str) -> Dict:
            """验证资质证书有效性"""
            # 调用外部API验证
            pass

        return [search_regulation, find_in_document, verify_license]

    def review(
        self,
        bid_doc: Dict,
        tender_requirements: Dict
    ) -> Dict:
        """执行合规审查"""

        # 1. 提取资格审查要求
        qualification_reqs = tender_requirements.get('qualification_requirements', [])
        mandatory_reqs = tender_requirements.get('mandatory_requirements', [])

        # 2. 逐项审查
        results = []
        for req in qualification_reqs:
            check_result = self._check_requirement(bid_doc, req)
            results.append(check_result)

        # 3. 汇总结果
        all_passed = all(r['passed'] for r in results)

        return {
            'passed': all_passed,
            'items': results,
            'warnings': [r for r in results if r.get('confidence', 1) < 0.8],
            'confidence': sum(r.get('confidence', 0) for r in results) / len(results)
        }

    def _check_requirement(self, bid_doc: Dict, requirement: Dict) -> Dict:
        """检查单个要求项"""
        # 使用LLM进行判断
        prompt = f"""
        审查要求：{requirement['name']}
        要求说明：{requirement['description']}

        投标文件内容：
        {bid_doc.get('extracted_info', {}).get(requirement['category'], '未找到')}

        请判断：
        1. 是否符合要求？
        2. 证据在哪一页？
        3. 置信度(0-1)？

        以JSON格式返回。
        """

        response = self.llm.invoke(prompt)
        # 解析响应...
        return {"passed": True, "confidence": 0.9}
```

### 3.4 信息提取模块

#### 3.4.1 关键信息提取器

```python
# src/extraction/info_extractor.py

from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional

class CompanyInfo(BaseModel):
    """公司信息"""
    name: str = Field(description="公司名称")
    contact_person: Optional[str] = Field(description="联系人")
    phone: Optional[str] = Field(description="联系电话")
    address: Optional[str] = Field(description="公司地址")

class QualificationInfo(BaseModel):
    """资质信息"""
    license_type: str = Field(description="证书类型")
    license_no: str = Field(description="证书编号")
    valid_until: str = Field(description="有效期至")
    issuing_authority: Optional[str] = Field(description="发证机关")

class PerformanceInfo(BaseModel):
    """业绩信息"""
    project_name: str = Field(description="项目名称")
    client: str = Field(description="采购单位")
    contract_amount: Optional[float] = Field(description="合同金额")
    completion_date: Optional[str] = Field(description="完成日期")
    contact_info: Optional[str] = Field(description="联系方式")

class TechnicalParam(BaseModel):
    """技术参数"""
    param_name: str = Field(description="参数名称")
    required_value: str = Field(description="要求值")
    bid_value: str = Field(description="投标值")
    deviation: str = Field(description="偏离情况：正偏离/负偏离/无偏离")
    is_mandatory: bool = Field(description="是否实质性要求")

class BidInfoExtraction(BaseModel):
    """投标信息提取结果"""
    company: CompanyInfo
    qualifications: List[QualificationInfo]
    performances: List[PerformanceInfo]
    technical_params: List[TechnicalParam]
    quotation: Optional[float] = Field(description="报价金额")

class InfoExtractor:
    """信息提取器"""

    def __init__(self, llm):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=BidInfoExtraction)

    def extract(self, content_list: List[Dict], doc_structure: Dict) -> BidInfoExtraction:
        """从content_list提取关键信息"""

        # 构建提取提示
        prompt = f"""
        请从以下投标文件内容中提取关键信息：

        文档结构：
        {doc_structure}

        文档内容（部分）：
        {self._get_relevant_content(content_list)}

        {self.parser.get_format_instructions()}

        要求：
        1. 准确提取公司信息
        2. 列出所有资质证书
        3. 提取业绩列表
        4. 解析技术参数响应表
        5. 提取报价信息
        """

        response = self.llm.invoke(prompt)
        return self.parser.parse(response.content)

    def _get_relevant_content(self, content_list: List[Dict], max_chars: int = 10000) -> str:
        """获取相关内容"""
        # 优先获取关键章节
        keywords = ['资质', '业绩', '技术参数', '报价', '公司', '营业执照']
        relevant_items = []

        for item in content_list:
            if item.get('type') == 'text':
                text = item.get('text', '')
                if any(kw in text for kw in keywords):
                    relevant_items.append(text)

        content = '\n'.join(relevant_items)
        return content[:max_chars]
```

---

## 四、知识库设计

### 4.1 知识库结构

```
knowledge_base/
├── regulations/                    # 法规库
│   ├── 招标投标法/
│   │   ├── 招标投标法.md
│   │   └── 招标投标法实施条例.md
│   ├── 政府采购/
│   │   ├── 政府采购法.md
│   │   └── 财政部87号令.md
│   └── 医疗器械/
│       ├── 医疗器械监督管理条例.md
│       └── 医疗器械注册管理办法.md
│
├── standards/                      # 标准/模板
│   ├── 资格审查标准检查清单.json
│   ├── 技术参数偏离判定规则.json
│   └── 评分标准模板.json
│
├── historical/                     # 历史案例
│   ├── projects/
│   │   └── {project_id}/
│   │       ├── tender.json         # 招标文件
│   │       ├── bids/               # 投标文件
│   │       └── result.json         # 评审结果
│   └── patterns/                   # 识别模式
│       └── bid_rigging_patterns.json
│
└── vector_index/                   # 向量索引
    └── chroma/
```

### 4.2 法规知识库构建

```python
# src/knowledge/regulation_kb.py

from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class RegulationKnowledgeBase:
    """法规知识库"""

    def __init__(self, persist_directory: str):
        self.persist_directory = persist_directory
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n## ", "\n### ", "\n#### ", "。", "；", "\n"]
        )

    def build_from_markdown(self, md_directory: str):
        """从Markdown文件构建知识库"""
        loader = DirectoryLoader(md_directory, glob="**/*.md")
        documents = loader.load()

        # 分块
        chunks = self.text_splitter.split_documents(documents)

        # 添加元数据
        for chunk in chunks:
            # 从文件路径提取法规类型
            source = chunk.metadata.get('source', '')
            if '招标投标法' in source:
                chunk.metadata['category'] = 'tender_law'
            elif '政府采购' in source:
                chunk.metadata['category'] = 'procurement_law'
            elif '医疗器械' in source:
                chunk.metadata['category'] = 'medical_device_regulation'

        # 存入向量库
        self.vectorstore.add_documents(chunks)

        return len(chunks)
```

---

## 五、API接口设计

### 5.1 FastAPI路由

```python
# src/api/routes.py

from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="辅助评标专家系统API")

class ParseRequest(BaseModel):
    """解析请求"""
    file_url: Optional[str] = None

class ParseResponse(BaseModel):
    """解析响应"""
    doc_id: str
    content_list_path: str
    markdown_path: str
    structure: dict

class ReviewRequest(BaseModel):
    """评审请求"""
    tender_id: str
    bid_doc_ids: List[str]

class ReviewResponse(BaseModel):
    """评审响应"""
    review_id: str
    status: str
    results: Optional[dict] = None

# 文档解析接口
@app.post("/api/v1/parse", response_model=ParseResponse)
async def parse_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks
):
    """上传并解析投标文件"""
    # 保存文件
    file_path = await save_upload_file(file)

    # 调用MinerU解析
    result = await mineru_parser.parse_pdf(file_path, OUTPUT_DIR)

    # 后台处理：分块、向量化
    background_tasks.add_task(process_document, result)

    return ParseResponse(
        doc_id=generate_doc_id(),
        content_list_path=result['content_list_path'],
        markdown_path=result['markdown_path'],
        structure=result['structure']
    )

# 评审接口
@app.post("/api/v1/review", response_model=ReviewResponse)
async def create_review(request: ReviewRequest):
    """创建评审任务"""
    # 获取招标要求和投标文件
    tender = await get_tender(request.tender_id)
    bids = await get_bids(request.bid_doc_ids)

    # 初始化Agent状态
    initial_state = AgentState(
        tender_id=request.tender_id,
        tender_requirements=tender['requirements'],
        bid_documents=bids,
        current_stage='init'
    )

    # 执行工作流
    result = await supervisor_agent.run(initial_state)

    return ReviewResponse(
        review_id=generate_review_id(),
        status='completed',
        results=result
    )

# 获取评审结果
@app.get("/api/v1/review/{review_id}")
async def get_review_result(review_id: str):
    """获取评审结果"""
    return await get_review_from_db(review_id)
```

---

## 六、部署架构

### 6.1 Docker部署

```yaml
# docker-compose.yml

version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MINERU_API_KEY=${MINERU_API_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/bid_evaluation
    depends_on:
      - db
      - chroma
    volumes:
      - ./knowledge_base:/app/knowledge_base
      - ./uploads:/app/uploads

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=bid_evaluation
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  chroma_data:
```

### 6.2 系统配置

```python
# config/settings.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API配置
    OPENAI_API_KEY: str
    MINERU_API_KEY: str
    MINERU_BASE_URL: str = "https://mineru.net/api/v1"

    # 数据库配置
    DATABASE_URL: str
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    REDIS_URL: str = "redis://localhost:6379"

    # 模型配置
    LLM_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # 文档处理配置
    MAX_CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # Agent配置
    MAX_ITERATIONS: int = 10
    CONFIDENCE_THRESHOLD: float = 0.75

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 七、参考资料

### 7.1 GitHub项目

| 项目 | 链接 | 用途 |
|------|------|------|
| MinerU | https://github.com/opendatalab/MinerU | PDF解析 |
| RAGFlow | https://github.com/infiniflow/ragflow | RAG引擎 |
| LangChain | https://github.com/langchain-ai/langchain | LLM框架 |
| LangGraph | https://github.com/langchain-ai/langgraph | 多Agent |
| CrewAI | https://github.com/crewAIInc/crewAI | Agent协作 |
| ChromaDB | https://github.com/chroma-core/chroma | 向量数据库 |

### 7.2 相关文档

- MinerU API文档：https://mineru.net/docs
- LangGraph文档：https://langchain-ai.github.io/langgraph/
- RAG评估(RAGAS)：https://docs.ragas.io/

---

*文档版本：v1.0*
*设计时间：2026年2月20日*
