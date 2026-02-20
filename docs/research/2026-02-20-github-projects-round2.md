# GitHub 相关项目搜索（第二轮）

> 搜索日期：2026-02-20
> 搜索范围：招投标评标、文档解析、RAG框架、Agent工作流

---

## 一、新发现项目汇总

### 1.1 文档解析类

| 项目 | Star | 描述 | 借鉴价值 |
|------|------|------|----------|
| **[Docling](https://github.com/docling-project/docling)** | 42k+ | IBM 开源多模态文档理解框架，支持 30+ 格式 | ⭐⭐⭐⭐⭐ |
| **[MonkeyOCR](https://github.com/Yuliang-Liu/MonkeyOCR)** | - | 轻量级 LMM 文档解析模型 | ⭐⭐⭐⭐ |
| **[PDF-Document-Layout-Analysis](https://github.com/huridocs/pdf-document-layout-analysis)** | - | PDF 版面分析微服务 | ⭐⭐⭐ |
| **[Umi-OCR](https://github.com/hiroi-sora/Umi-OCR)** | 16.9k | 开源 OCR 工具，支持离线 | ⭐⭐⭐ |

**Docling vs MinerU 对比：**

| 维度 | MinerU | Docling |
|------|--------|---------|
| 精度 | ⭐⭐⭐⭐⭐ (95%+) | ⭐⭐⭐⭐ |
| 速度 | 较慢（资源消耗大） | 快 (1-3s/页) |
| 格式支持 | PDF 为主 | 30+ 格式 |
| AI框架集成 | 需手动配置 | LangChain/LlamaIndex 即插即用 |

### 1.2 RAG 框架类

| 项目 | Star | 描述 | 借鉴价值 |
|------|------|------|----------|
| **[RAG-Anything](https://github.com/HKUDS/RAG-Anything)** | 6.8k+ | 港大多模态 RAG 框架，整合 MinerU + Docling | ⭐⭐⭐⭐⭐ |
| **[RAGFlow](https://github.com/infiniflow/ragflow)** | 34.9k | 深度文档理解的 RAG 引擎 | ⭐⭐⭐⭐⭐ |
| **[DSPy](https://github.com/stanfordnlp/dspy)** | 20k+ | 斯坦福 RAG 优化框架，编程式 Prompt | ⭐⭐⭐⭐⭐ |
| **[RAG_Techniques](https://github.com/NirDiamant/RAG_Techniques)** | - | 30+ RAG 技术方案集合 | ⭐⭐⭐⭐ |

### 1.3 法律/合同文档分析类

| 项目 | 描述 | 借鉴价值 |
|------|------|----------|
| **[LawBotics](https://github.com/hasnaintypes/lawbotics)** | AI 合同分析平台，41+ 条款类型识别 | ⭐⭐⭐⭐ |
| **[Legal-AI](https://github.com/topics/legal-ai)** | 法律 AI 项目集合 | ⭐⭐⭐ |
| **[RAG-Anything-Legal](https://github.com/snehitvaddi/RAG-Anything)** | 法律文档查询系统 | ⭐⭐⭐ |

### 1.4 Agent 工作流类

| 项目 | 描述 | 借鉴价值 |
|------|------|----------|
| **[GenAI_Agents](https://gitcode.com/GitHub_Trending/ge/GenAI_Agents)** | LangGraph 多智能体协作框架 | ⭐⭐⭐⭐ |
| **[Agents-Course](https://gitcode.com/GitHub_Trending/ag/agents-course)** | Hugging Face Agents 课程示例 | ⭐⭐⭐ |

---

## 二、重点推荐项目

### 2.1 DSPy - RAG 优化框架（强烈推荐）

**项目地址**: https://github.com/stanfordnlp/dspy

**核心价值**: 编程式构建 AI 系统，自动优化 Prompt

```python
import dspy

# 定义 RAG 模块
class BasicQA(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.Predict("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        return self.generate(context=context, question=question)

# 使用 MIPROv2 自动优化
tp = dspy.MIPROv2(metric=dspy.evaluate.answer_exact_match, auto="light")
optimized_qa = tp.compile(BasicQA(), trainset=trainset)
```

**优化器对比：**

| 优化器 | 效果提升 | 说明 |
|--------|----------|------|
| BootstrapFewShot | 5-10% | 自动生成 few-shot 示例 |
| MIPROv2 | 10-20% | 贝叶斯优化 Prompt |
| GEPA | 15-25% | 反思式 Prompt 演化 |

**应用场景**: 评标系统的评分模型可以自动优化，提升准确率

### 2.2 RAG-Anything - 多模态 RAG 框架

**项目地址**: https://github.com/HKUDS/RAG-Anything

**核心价值**: 整合 MinerU + Docling，自动选择最佳解析器

```
文档输入 → 智能选择器 → 复杂布局? → MinerU
                         ↓
                    标准格式? → Docling
                         ↓
                    统一 Chunk 输出
```

**特点**:
- 支持文本、图像、表格、公式、图表
- 基于 LightRAG 构建
- 港大 DS 实验室出品

### 2.3 Docling - 企业级文档理解

**项目地址**: https://github.com/docling-project/docling

**核心价值**: IBM 开源，30+ 格式支持，与 LangChain 无缝集成

**支持的格式**:
- PDF, DOCX, PPTX, XLSX
- HTML, Markdown, ASCII
- 图片（PNG, JPG）
- 音频（实验性）

**集成方式**:
```python
from langchain_community.document_loaders import DoclingLoader

loader = DoclingLoader(file_path="bid_document.pdf")
docs = loader.load()
```

---

## 三、行业实践案例

### 3.1 国内 AI 招投标实践

| 地区 | 项目 | 特点 |
|------|------|------|
| **郑州** | AI 智能招投标系统 | AI 当评标专家，完成首秀 |
| **贵州** | 公共资源交易 AI 辅助评审 | 房屋建筑技术标主观分智能评审 |
| **深圳** | 区块链 + BIM + AI | 技术标文件智能评审 |
| **武汉** | AI 智慧开评标项目 | 预算 35 万元 |

### 3.2 AI 辅助评标核心功能

根据搜索结果，主流 AI 辅助评标系统包含：

1. **评分标准智能化** - 自动解析评标标准
2. **投标文件结构化** - OCR + 大模型提取关键信息
3. **数据验真便捷化** - 自动核验资质证书
4. **评审过程自动化** - 客观分自动计算
5. **围串标风险分析** - 8 维度异常检测
6. **评标风险审查** - 合规性自动审查

### 3.3 异常行为检测维度

| 维度 | 检测内容 |
|------|----------|
| 企业关联 | 股权关系、高管交叉 |
| 语义相似 | 投标文件内容雷同 |
| 报价规律 | 报价策略异常 |
| 时间规律 | 投标时间异常集中 |
| IP/MAC | 投标设备相同 |
| 历史记录 | 历次投标行为模式 |

---

## 四、技术栈更新建议

基于新发现的项目，建议更新技术选型：

### 4.1 文档解析层

```
当前: MinerU + PaddleOCR
建议: MinerU + Docling + PaddleOCR
      - MinerU: 复杂布局 PDF（技术参数表、图纸）
      - Docling: 标准格式文档（Word、Excel）
      - PaddleOCR: 扫描件、证书
```

### 4.2 RAG 评估层

```
当前: RAGAS + DeepEval
建议: RAGAS + DeepEval + DSPy
      - DSPy: 自动优化评分 Prompt
      - MIPROv2: 提升评分准确率 10-20%
```

### 4.3 多模态支持

```
当前: 纯文本 RAG
建议: 多模态 RAG（RAG-Anything 思路）
      - 支持表格、图表、公式解析
      - 保留原始位置信息
```

---

## 五、下一步行动

### 5.1 立即可用（作为依赖）

```bash
# 添加 Docling
pip install docling

# 添加 DSPy（用于 Prompt 优化）
pip install dspy
```

### 5.2 深入研究

- [ ] 研究 DSPy 在评标评分中的应用
- [ ] 研究 Docling 与 LangChain 的集成方式
- [ ] 研究 RAG-Anything 的解析器选择策略

### 5.3 避免事项

- ❌ 不要重复造轮子（Docling 已有完善的格式支持）
- ❌ 不要手动调优 Prompt（使用 DSPy 自动优化）

---

## 六、参考资料

**文档解析：**
- [Docling 官方文档](https://docling-project.github.io/docling/)
- [MinerU2.5 论文](https://arxiv.org/html/2509.22186v1)
- [PDF 解析基准测试](https://m.blog.csdn.net/star_nwe/article/details/151416464)

**RAG 框架：**
- [RAGFlow GitHub](https://github.com/infiniflow/ragflow)
- [RAG-Anything GitHub](https://github.com/HKUDS/RAG-Anything)
- [DSPy 官方文档](https://dspy.ai)
- [RAG_Techniques GitHub](https://github.com/NirDiamant/RAG_Techniques)

**行业案例：**
- [郑州智能招投标系统](https://finance.sina.cn/2026-01-28/detail-inhivfcf7628926.d.html)
- [贵州公共资源交易 AI](http://dsj.guizhou.gov.cn/zwgk/zdlyxx/sjyytg/202512/t20251215_89049729.html)
- [广东人工智能+招标投标](https://drc.gd.gov.cn/gzyw5618/content/post_4858145.html)

---

*文档版本：v1.0*
*创建日期：2026-02-20*
