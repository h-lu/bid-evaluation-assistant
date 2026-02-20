# MinerU API JSON输出处理技术实现指南

> 目标：详细说明如何使用MinerU API解析PDF，并处理其JSON输出以提取结构化数据  
> 整理时间：2026年2月20日

---

## 一、MinerU概述

### 1.1 项目简介

**MinerU**是由上海人工智能实验室OpenDataLab团队开发的开源高质量PDF解析工具，能够将包含图片、公式、表格的复杂PDF转换为Markdown和JSON等机器可读格式。

**核心能力**：
- 精准识别并保留标题、段落、列表、表格、公式和图像等复杂版式结构
- 有效去除页眉页脚、脚注等干扰元素
- 支持多语言（中文、英文、日文、韩文等）
- 输出接近人工编辑质量的Markdown或JSON

**版本说明**：
- v1.0：基础版本
- v2.0（2025年6月）：架构重构，性能大幅提升
- v2.5（2025年9月）：VLM后端升级，JSON格式有变化

### 1.2 输出格式

MinerU支持以下输出格式：

| 格式 | 文件扩展名 | 用途 |
|-----|-----------|-----|
| **Markdown** | `.md` | 人类可读，快速预览 |
| **Content List JSON** | `_content_list.json` | 简化版结构化数据 |
| **Middle JSON** | `_middle.json` | 完整中间结果 |
| **Model JSON** | `_model.json` | 模型原始输出 |
| **HTML** | `.html` | 网页展示（可选） |
| **Docx** | `.docx` | Word文档（可选） |

---

## 二、MinerU JSON输出结构详解

### 2.1 Content List JSON（推荐使用）

**文件命名**：`{filename}_content_list.json`

**特点**：
- middle.json的简化版本
- 扁平化结构，按阅读顺序存储内容块
- 移除了复杂布局信息，便于直接使用
- 适合大多数应用场景

**数据结构**：

```json
[
  {
    "type": "text",
    "text": "段落文本内容",
    "page_idx": 0
  },
  {
    "type": "table",
    "img_path": "images/table_001.png",
    "page_idx": 1
  },
  {
    "type": "image",
    "img_path": "images/figure_001.png",
    "page_idx": 1
  },
  {
    "type": "title",
    "text": "章节标题",
    "level": 1,
    "page_idx": 2
  }
]
```

**字段说明**：

| 字段 | 类型 | 说明 |
|-----|-----|-----|
| `type` | string | 内容类型：text/table/image/title/interline_equation |
| `text` | string | 文本内容（type为text/title时） |
| `img_path` | string | 图片路径（type为table/image时） |
| `level` | int | 标题级别（type为title时） |
| `page_idx` | int | 页码（从0开始） |

### 2.2 Middle JSON（完整信息）

**文件命名**：`{filename}_middle.json`

**特点**：
- 包含完整的解析中间结果
- 保留详细的布局信息和层级结构
- 包含 discarded_blocks（被丢弃的页眉页脚等）
- 适合需要深度分析的场景

**顶层结构**：

```json
{
  "pdf_info": [
    {
      "page_idx": 0,
      "page_size": [612.0, 792.0],
      "preproc_blocks": [...],
      "para_blocks": [...],
      "layout_bboxes": [...],
      "images": [...],
      "tables": [...],
      "discarded_blocks": [...]
    }
  ]
}
```

#### 2.2.1 Page Information结构

```json
{
  "page_idx": 0,
  "page_size": [612.0, 792.0],
  "preproc_blocks": [...],
  "para_blocks": [...],
  "layout_bboxes": [...],
  "images": [],
  "tables": [],
  "interline_equations": [],
  "discarded_blocks": []
}
```

#### 2.2.2 Block结构（核心）

**层级关系**：
```
Level 1 Block (table | image | text)
└── Level 2 Block
    └── Lines
        └── Spans
```

**Level 1 Block字段**：

```json
{
  "type": "text",
  "bbox": [52, 61.95, 294, 82.99],
  "lines": [...]
}
```

| 字段 | 类型 | 说明 |
|-----|-----|-----|
| `type` | string | block类型：text/table/image/interline_equation |
| `bbox` | array | 边界框坐标 [x1, y1, x2, y2] |
| `lines` | array | 包含的文本行 |

**Line结构**：

```json
{
  "bbox": [52, 61.95, 294, 72.0],
  "spans": [...]
}
```

**Span结构（最细粒度）**：

```json
{
  "bbox": [54.0, 61.95, 296.22, 72.0],
  "content": "文本内容",
  "type": "text",
  "score": 1.0
}
```

| 字段 | 类型 | 说明 |
|-----|-----|-----|
| `bbox` | array | 边界框坐标 |
| `content` | string | 文本内容 |
| `type` | string | span类型：text/image/table/inline_equation/interline_equation |
| `score` | float | 置信度分数 |

### 2.3 Model JSON（模型原始输出）

**文件命名**：`{filename}_model.json`

**用途**：
- 调试用，查看模型原始识别结果
- 可视化layout.pdf和span.pdf的数据来源

**数据结构**：

```json
[
  {
    "layout_dets": [
      {
        "category_id": 5,
        "poly": [x0, y0, x1, y1, x2, y2, x3, y3],
        "score": 0.999
      }
    ],
    "page_info": {
      "page_no": 0,
      "height": 2339,
      "width": 1654
    }
  }
]
```

**Category Type枚举**：

| ID | 名称 | 说明 |
|----|-----|-----|
| 0 | title | 标题 |
| 1 | plain_text | 正文文本 |
| 2 | abandon | 页眉页脚页码等（应丢弃） |
| 3 | figure | 图片 |
| 4 | figure_caption | 图片标题 |
| 5 | table | 表格 |
| 6 | table_caption | 表格标题 |
| 7 | table_footnote | 表格脚注 |
| 8 | isolate_formula | 行间公式 |
| 9 | formula_caption | 公式编号 |
| 13 | embedding | 行内公式（旧版） |
| 14 | isolated | 行间公式（旧版） |
| 15 | text | OCR识别结果 |

---

## 三、API调用与JSON获取

### 3.1 本地部署方式

#### 安装

```bash
# 创建虚拟环境
conda create -n mineru python=3.11
conda activate mineru

# 安装MinerU
pip install --upgrade pip
pip install -U "mineru[core]"

# 下载模型
export MINERU_MODEL_SOURCE=modelscope  # 国内用户使用modelscope
mineru-models-download
```

#### 配置文件

创建`magic-pdf.json`：

```json
{
  "models-dir": "/path/to/models",
  "config_version": "1.3.1"
}
```

#### Python API调用

```python
import json
from pathlib import Path
from mineru.cli.common import prepare_env
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.backend.pipeline.pipeline_analyze import doc_analyze
from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make

def parse_pdf(pdf_path: str, output_dir: str):
    """
    解析PDF并获取所有JSON输出
    """
    # 准备环境
    pdf_name = Path(pdf_path).stem
    local_image_dir, local_md_dir = prepare_env(output_dir, pdf_name, "auto")
    
    # 创建writer
    image_writer = FileBasedDataWriter(local_image_dir)
    md_writer = FileBasedDataWriter(local_md_dir)
    
    # 读取PDF
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    # 执行解析（pipeline后端）
    infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = doc_analyze(
        [pdf_bytes], 
        ['ch'],  # 语言：中文
        parse_method='auto',
        formula_enable=True,  # 启用公式识别
        table_enable=True     # 启用表格识别
    )
    
    # 处理结果
    for idx, model_list in enumerate(infer_results):
        model_json = json.loads(json.dumps(model_list))
        
        # 转换为middle.json
        middle_json = result_to_middle_json(
            model_list, 
            all_image_lists[idx], 
            all_pdf_docs[idx], 
            image_writer, 
            lang_list[idx], 
            ocr_enabled_list[idx], 
            formula_enable=True
        )
        
        # 生成content_list
        content_list = union_make(middle_json, parse_method='auto')
        
        # 保存JSON文件
        with open(f"{output_dir}/{pdf_name}_model.json", 'w', encoding='utf-8') as f:
            json.dump(model_json, f, ensure_ascii=False, indent=2)
        
        with open(f"{output_dir}/{pdf_name}_middle.json", 'w', encoding='utf-8') as f:
            json.dump(middle_json, f, ensure_ascii=False, indent=2)
        
        with open(f"{output_dir}/{pdf_name}_content_list.json", 'w', encoding='utf-8') as f:
            json.dump(content_list, f, ensure_ascii=False, indent=2)
        
        return {
            'model_json': model_json,
            'middle_json': middle_json,
            'content_list': content_list,
            'image_dir': local_image_dir
        }
```

### 3.2 在线API方式

```python
import requests
import json

API_KEY = "your_api_key"
BASE_URL = "https://mineru.net/api/v1"

def parse_pdf_api(pdf_path: str):
    """
    使用在线API解析PDF
    """
    url = f"{BASE_URL}/extract"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    with open(pdf_path, 'rb') as f:
        files = {'file': f}
        data = {
            'parse_method': 'auto',
            'formula_enable': 'true',
            'table_enable': 'true'
        }
        
        response = requests.post(url, headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            # result包含content_list和其他信息
            return result
        else:
            raise Exception(f"API调用失败: {response.text}")
```

---

## 四、JSON数据处理实战

### 4.1 提取纯文本内容

```python
def extract_text_from_content_list(content_list: list) -> str:
    """
    从content_list中提取所有文本内容
    """
    texts = []
    for item in content_list:
        if item['type'] == 'text':
            texts.append(item['text'])
        elif item['type'] == 'title':
            texts.append(f"\n## {item['text']}\n")  # 标题加标记
    return '\n'.join(texts)
```

### 4.2 提取结构化标题

```python
def extract_titles(content_list: list) -> list:
    """
    提取所有标题及其层级
    """
    titles = []
    for item in content_list:
        if item['type'] == 'title':
            titles.append({
                'text': item['text'],
                'level': item.get('level', 1),
                'page': item.get('page_idx', 0)
            })
    return titles

# 构建目录结构
def build_toc(titles: list) -> dict:
    """
    根据标题构建目录树
    """
    toc = {'children': []}
    stack = [toc]
    
    for title in titles:
        level = title['level']
        node = {
            'text': title['text'],
            'page': title['page'],
            'children': []
        }
        
        # 根据层级调整栈
        while len(stack) > level:
            stack.pop()
        
        stack[-1]['children'].append(node)
        stack.append(node)
    
    return toc
```

### 4.3 提取表格信息

```python
def extract_tables(content_list: list, image_dir: str) -> list:
    """
    提取所有表格及其位置
    """
    tables = []
    for idx, item in enumerate(content_list):
        if item['type'] == 'table':
            table_info = {
                'index': idx,
                'page': item.get('page_idx', 0),
                'image_path': f"{image_dir}/{item['img_path']}",
                'caption': None  # 需要关联查找表格标题
            }
            
            # 查找表格标题（通常在表格前）
            if idx > 0 and content_list[idx-1]['type'] == 'text':
                prev_text = content_list[idx-1]['text']
                if '表' in prev_text or 'Table' in prev_text:
                    table_info['caption'] = prev_text
            
            tables.append(table_info)
    
    return tables
```

### 4.4 段落与阅读顺序

```python
def get_paragraphs_in_order(middle_json: dict) -> list:
    """
    从middle.json中提取按阅读顺序排列的段落
    """
    paragraphs = []
    
    for page in middle_json.get('pdf_info', []):
        page_idx = page['page_idx']
        
        # 处理para_blocks（主内容块）
        for block in page.get('para_blocks', []):
            if block['type'] == 'text':
                # 合并所有行的文本
                text_lines = []
                for line in block.get('lines', []):
                    line_text = ''.join([
                        span.get('content', '') 
                        for span in line.get('spans', [])
                    ])
                    text_lines.append(line_text)
                
                paragraphs.append({
                    'text': '\n'.join(text_lines),
                    'page': page_idx,
                    'bbox': block.get('bbox')
                })
    
    return paragraphs
```

### 4.5 过滤页眉页脚

```python
def remove_headers_footers(middle_json: dict) -> dict:
    """
    移除middle.json中的页眉页脚信息
    """
    cleaned = json.loads(json.dumps(middle_json))  # 深拷贝
    
    for page in cleaned.get('pdf_info', []):
        # discarded_blocks中包含页眉页脚
        discarded = page.get('discarded_blocks', [])
        print(f"Page {page['page_idx']}: 丢弃 {len(discarded)} 个块")
        
        # 清空discarded_blocks
        page['discarded_blocks'] = []
    
    return cleaned
```

### 4.6 表格内容结构化提取（使用OCR）

```python
import pandas as pd
from paddleocr import PaddleOCR

def table_image_to_dataframe(table_image_path: str) -> pd.DataFrame:
    """
    使用OCR将表格图片转换为DataFrame
    注意：这是简化版，实际应用中可能需要更复杂的表格结构识别
    """
    ocr = PaddleOCR(use_angle_cls=True, lang='ch')
    
    # OCR识别
    result = ocr.ocr(table_image_path, cls=True)
    
    # 提取文本和坐标
    texts = []
    for line in result[0]:
        bbox = line[0]  # 边界框坐标
        text = line[1][0]  # 识别文本
        confidence = line[1][1]  # 置信度
        
        # 计算中心点y坐标用于行分组
        center_y = (bbox[0][1] + bbox[2][1]) / 2
        center_x = (bbox[0][0] + bbox[2][0]) / 2
        
        texts.append({
            'text': text,
            'x': center_x,
            'y': center_y,
            'confidence': confidence
        })
    
    # 按y坐标分组（简单行识别）
    texts.sort(key=lambda x: x['y'])
    
    # 这里需要根据实际表格结构调整逻辑
    # 简化处理：假设已知列数
    
    return pd.DataFrame(texts)
```

---

## 五、RAG Chunking策略

### 5.1 基于MinerU的Chunking

```python
from typing import List, Dict

class MinerUChunker:
    """
    基于MinerU输出的智能分块器
    """
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def chunk_by_paragraph(self, content_list: List[Dict]) -> List[Dict]:
        """
        按段落分块，保留标题上下文
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        for item in content_list:
            if item['type'] == 'title':
                # 标题开启新块
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk))
                current_chunk = [item]
                current_size = len(item.get('text', ''))
            
            elif item['type'] == 'text':
                text_len = len(item.get('text', ''))
                
                if current_size + text_len > self.max_chunk_size:
                    # 当前块已满，保存并开启新块
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk))
                    
                    # 保留重叠内容
                    current_chunk = self._get_overlap_items(current_chunk)
                    current_size = sum(len(i.get('text', '')) for i in current_chunk)
                
                current_chunk.append(item)
                current_size += text_len
        
        # 保存最后一个块
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk))
        
        return chunks
    
    def _create_chunk(self, items: List[Dict]) -> Dict:
        """创建块"""
        texts = []
        for item in items:
            if item['type'] == 'title':
                texts.append(f"# {item['text']}")
            elif item['type'] == 'text':
                texts.append(item['text'])
        
        return {
            'content': '\n\n'.join(texts),
            'metadata': {
                'start_page': items[0].get('page_idx', 0),
                'end_page': items[-1].get('page_idx', 0),
                'types': [i['type'] for i in items]
            }
        }
    
    def _get_overlap_items(self, items: List[Dict]) -> List[Dict]:
        """获取重叠的内容项"""
        # 保留最后一个标题和所有文本的一部分
        overlap_items = []
        
        for item in reversed(items):
            if item['type'] == 'title':
                overlap_items.insert(0, item)
                break
        
        return overlap_items

    def chunk_by_section(self, content_list: List[Dict]) -> List[Dict]:
        """
        按章节分块（基于标题层级）
        """
        sections = []
        current_section = []
        current_level = 0
        
        for item in content_list:
            if item['type'] == 'title':
                level = item.get('level', 1)
                
                if level <= current_level and current_section:
                    # 同级或更高级标题，保存当前章节
                    sections.append(self._create_section(current_section))
                    current_section = []
                
                current_level = level
            
            current_section.append(item)
        
        # 保存最后一个章节
        if current_section:
            sections.append(self._create_section(current_section))
        
        return sections
    
    def _create_section(self, items: List[Dict]) -> Dict:
        """创建章节块"""
        title = ''
        contents = []
        
        for item in items:
            if item['type'] == 'title' and not title:
                title = item['text']
            elif item['type'] == 'text':
                contents.append(item['text'])
        
        return {
            'title': title,
            'content': '\n\n'.join(contents),
            'metadata': {
                'page_start': items[0].get('page_idx', 0),
                'page_end': items[-1].get('page_idx', 0),
                'item_count': len(items)
            }
        }
```

### 5.2 表格单独处理

```python
def process_tables_for_rag(content_list: List[Dict], image_dir: str) -> List[Dict]:
    """
    单独处理表格，生成描述性文本
    """
    table_chunks = []
    
    for idx, item in enumerate(content_list):
        if item['type'] == 'table':
            # 查找表格上下文
            context = []
            if idx > 0:
                context.append(content_list[idx-1].get('text', ''))
            if idx < len(content_list) - 1:
                context.append(content_list[idx+1].get('text', ''))
            
            table_chunk = {
                'type': 'table',
                'content': f"表格内容（见图片: {item['img_path']}）",
                'context': '\n'.join(context),
                'image_path': f"{image_dir}/{item['img_path']}",
                'page': item.get('page_idx', 0),
                'metadata': {
                    'is_table': True,
                    'requires_vision': True
                }
            }
            table_chunks.append(table_chunk)
    
    return table_chunks
```

---

## 六、完整处理Pipeline

```python
class PDFProcessor:
    """
    PDF处理Pipeline
    """
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.chunker = MinerUChunker(max_chunk_size=512, overlap=50)
    
    def process(self, pdf_path: str) -> Dict:
        """
        完整处理流程
        """
        # 1. 解析PDF
        parse_result = self._parse_pdf(pdf_path)
        
        # 2. 提取结构化信息
        content_list = parse_result['content_list']
        middle_json = parse_result['middle_json']
        image_dir = parse_result['image_dir']
        
        # 3. 提取元数据
        metadata = {
            'titles': extract_titles(content_list),
            'tables': extract_tables(content_list, image_dir),
            'total_pages': len(middle_json.get('pdf_info', []))
        }
        
        # 4. 分块
        text_chunks = self.chunker.chunk_by_section(content_list)
        table_chunks = process_tables_for_rag(content_list, image_dir)
        
        # 5. 合并所有chunks
        all_chunks = text_chunks + table_chunks
        
        # 6. 生成向量嵌入（示例）
        # chunks_with_embeddings = self._generate_embeddings(all_chunks)
        
        return {
            'metadata': metadata,
            'chunks': all_chunks,
            'raw_content_list': content_list,
            'image_dir': image_dir
        }
    
    def _parse_pdf(self, pdf_path: str) -> Dict:
        """调用MinerU解析"""
        # 使用前面定义的parse_pdf函数
        return parse_pdf(pdf_path, self.output_dir)
    
    def _generate_embeddings(self, chunks: List[Dict]) -> List[Dict]:
        """生成向量嵌入（需要接入embedding模型）"""
        # 示例：使用OpenAI或其他embedding服务
        for chunk in chunks:
            # chunk['embedding'] = get_embedding(chunk['content'])
            pass
        return chunks

# 使用示例
if __name__ == "__main__":
    processor = PDFProcessor(output_dir="./output")
    result = processor.process("投标书.pdf")
    
    print(f"共提取 {len(result['chunks'])} 个chunks")
    print(f"标题数量: {len(result['metadata']['titles'])}")
    print(f"表格数量: {len(result['metadata']['tables'])}")
```

---

## 七、最佳实践与注意事项

### 7.1 版本兼容性

⚠️ **重要**：MinerU v2.5版本（VLM后端）的JSON格式与v2.0及以下版本不兼容。

| 版本 | 后端 | JSON格式 | 兼容性 |
|-----|-----|---------|-------|
| v1.x | Pipeline | middle.json格式A | - |
| v2.0-2.4 | Pipeline | middle.json格式A | ✅ 兼容v1.x |
| v2.5+ | VLM | middle.json格式B | ❌ 不兼容 |

**建议**：
- 新项目直接使用v2.5+版本
- 旧项目升级需要修改数据处理代码

### 7.2 性能优化

```python
# 批量处理
from multiprocessing import Pool

def batch_process(pdf_paths: List[str], output_dir: str, num_workers: int = 4):
    """
    批量处理多个PDF
    """
    with Pool(num_workers) as pool:
        results = pool.starmap(
            process_single_pdf,
            [(path, output_dir) for path in pdf_paths]
        )
    return results
```

### 7.3 错误处理

```python
def safe_parse_pdf(pdf_path: str, output_dir: str) -> Dict:
    """
    安全的PDF解析，带错误处理
    """
    try:
        result = parse_pdf(pdf_path, output_dir)
        
        # 验证结果
        if not result.get('content_list'):
            raise ValueError("解析结果为空")
        
        return result
    
    except Exception as e:
        # 记录错误
        print(f"解析失败 {pdf_path}: {str(e)}")
        
        # 返回空结果
        return {
            'content_list': [],
            'middle_json': {},
            'error': str(e)
        }
```

### 7.4 数据验证

```python
from pydantic import BaseModel, ValidationError
from typing import List, Optional

class ContentItem(BaseModel):
    """Content List Item的数据验证模型"""
    type: str
    text: Optional[str] = None
    img_path: Optional[str] = None
    level: Optional[int] = None
    page_idx: int

class MinerUOutput(BaseModel):
    """MinerU输出的验证模型"""
    content_list: List[ContentItem]
    
    @classmethod
    def validate_output(cls, data: list) -> bool:
        try:
            cls(content_list=data)
            return True
        except ValidationError as e:
            print(f"数据验证失败: {e}")
            return False
```

---

## 八、参考资料

1. **MinerU官方文档**: https://opendatalab.github.io/MinerU/
2. **MinerU GitHub**: https://github.com/opendatalab/MinerU
3. **MinerU在线API**: https://mineru.net/apiManage/docs
4. **PDF-Extract-Kit**: https://github.com/opendatalab/PDF-Extract-Kit

---

*文档整理时间：2026年2月20日*  
*MinerU版本：v2.5+*  
*Python版本：3.10+*