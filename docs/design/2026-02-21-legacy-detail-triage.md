# 历史细节融合判定表（Git 历史 -> 现行规范）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`  
> 目的：把历史文档中的可用细节纳入现行方案，并明确不采纳项与原因

## 1. 判定规则

1. `保留`：可直接落地到现行设计。
2. `修正后保留`：思路可用，但字段/流程/边界需纠偏。
3. `废弃`：与现行目标、风险控制或维护成本冲突。

## 2. 核心判定

| 历史细节 | 判定 | 处理说明 | 现行落点 |
| --- | --- | --- | --- |
| `content_list.json` 作为定位真值 | 保留 | 保留 page/bbox 追踪能力 | `mineru-ingestion-spec` |
| `context_list.json` 命名 | 修正后保留 | 仅兼容读取，不作为 canonical 名称 | `mineru-ingestion-spec` |
| `full.md` 提供结构语义 | 保留 | 只补 heading_path，不做定位真值 | `mineru-ingestion-spec` |
| bbox 可能 `xyxy/xywh` 混用 | 修正后保留 | 统一归一化为 `[x0,y0,x1,y1]` | `mineru-ingestion-spec` |
| 编码回退策略 | 修正后保留 | `utf-8 -> gb18030`，失败显式错误码 | `mineru-ingestion-spec` |
| 解析器注册表模式 | 保留 | 采用 `mineru -> docling -> ocr` 路由链 | `mineru-ingestion-spec` |
| RGSG 工作流拆解 | 修正后保留 | 借鉴拆解思想，执行以固定状态机为准 | `langgraph-agent-workflow-spec` |
| TypedDict + 累积字段 | 保留 | 明确状态字段与可累积字段 | `langgraph-agent-workflow-spec` |
| interrupt/resume + checkpointer | 保留 | 采用持久化 checkpoint + `thread_id` | `langgraph-agent-workflow-spec` |
| 查询模式自动选择器 | 保留 | `local/global/hybrid/mix` 固化为 selector | `retrieval-and-scoring-spec` |
| include_references 引用返回 | 保留 | 评分链路默认开启 | `retrieval-and-scoring-spec` |
| SQL 检索支路 | 修正后保留 | 仅白名单字段，禁止自由 SQL | `retrieval-and-scoring-spec` |
| context optimizer/token budget | 保留 | 固化为 evidence packing 预算规则 | `retrieval-and-scoring-spec` |
| 评分可解释性（点对点表） | 保留 | 前端与报告统一结构 | `frontend-interaction-spec` |
| citation 回跳 + bbox 高亮 | 保留 | 作为前端必备能力 | `frontend-interaction-spec` |
| RAGAS + DeepEval 组合 | 保留 | 作为发布门禁 | `testing-strategy` |
| RAGChecker 三层诊断 | 修正后保留 | 作为 P1 诊断增强，不阻断 MVP | `testing-strategy` |
| DeepEval Synthesizer 自动样本 | 修正后保留 | 自动生成 + 人工抽检 | `datasets/eval-dataset-governance` |
| 按周里程碑（Week 1-8） | 废弃 | 改为 Gate 证据推进 | `implementation-plan` |
| 纯 LLM 判定红线 | 废弃 | 改为规则引擎优先 | `retrieval-and-scoring-spec` |
| Neo4j/Milvus 早期方案 | 废弃（MVP） | 成本高、收益不足，留作后续演进 | SSOT |
| RAPTOR/GraphRAG 直接上 MVP | 废弃（MVP） | 复杂度过高，先保证主链路稳定 | SSOT |

## 3. 历史来源（提交级）

以下历史提交已用于细节提取与融合：

1. `7f05f7e`（架构设计 v5.3）
2. `7f07ad6`（架构验证报告）
3. `53e3d92`（点对点应答/溯源引用/RAGChecker）
4. `184a6ac`（GitHub 项目详细分析）
5. `72a64da`（Agentic-Procure-Audit-AI 分析）
6. `a21fa09`（MinerU 相关项目研究）
7. `76f898d`（MinerU 输出处理研究）
8. `beef3e9`（旧版设计文档集合）

## 4. 使用规则

1. 开发执行只以 SSOT 与 `docs/design/` 现行文档为准。
2. 任何新细节先写入现行文档，再更新本判定表。
3. 不再维护历史目录作为并行规范源。

## 5. Gate A-3 验收结论

1. 历史细节已按“保留/修正后保留/废弃”完成归类。
2. 所有“修正后保留”均已明确现行落点文档。
3. 后续若新增历史融合项，必须同步更新本表与落点文档。
