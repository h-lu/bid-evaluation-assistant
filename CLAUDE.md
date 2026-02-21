# CLAUDE.md

本文件定义 Claude Code 在本项目中的协作记忆与执行约束。

## 1. 项目上下文速记

1. 当前仓库是“端到端方案与实施规范仓库”，不是业务代码仓库。
2. 主目标是指导实现：上传 -> 解析 -> 检索评分 -> HITL -> 报告归档。
3. 关键基线：`v2026.02.21-r3`。

## 2. 先读文档（顺序）

1. `README.md`
2. `docs/plans/2026-02-21-end-to-end-unified-design.md`
3. `docs/design/2026-02-21-implementation-plan.md`
4. 与任务对应的专项规范

## 3. 固定工程约束

1. 多租户隔离是 MVP 必选项，不后置。
2. `failed` 是 DLQ 子流程终态，不与 DLQ 并行。
3. 评分结论必须有可回跳 citation（`chunk_id/page/bbox`）。
4. 图示仅使用 ASCII。
5. 长任务统一异步（`202 + job_id`）。

## 4. Claude 协作方式

1. 先基于现有文档给出“是否缺口”的判断。
2. 发现缺口后一次性补齐，不做碎片化改动。
3. 修改后必须做一致性检查（引用、术语、状态机、错误码）。
4. 输出结果时给出可执行下一步，而不是抽象建议。

## 5. 官方最佳实践映射（核验后）

1. Claude Code memory：
   - `CLAUDE.md` 用于项目级持久上下文，不写临时推理过程。
   - 内容应包含常用命令、架构约束、代码风格、测试方式。
2. 多代理协作：
   - 优先拆分为独立子任务并并行，再统一回归。
3. 可靠性：
   - 明确何时需要人工审批与恢复点。
   - 高风险动作必须记录可审计证据。

## 6. 文档修改风格

1. 面向执行：给字段、流程、阈值、验收标准。
2. 版本清晰：保持 `版本/状态/对齐` 头部一致。
3. 避免空话：每节至少包含可落地条目。

## 7. 提交前最小核查命令

```bash
rg -n 'recovered|TODO|TBD|mermaid' README.md docs -g '*.md'
refs=$(rg -o --no-filename '`docs[^`]+\\.md`' README.md docs -g '*.md' | tr -d '`' | sort -u)
while IFS= read -r p; do [ -z "$p" ] || [ -f "$p" ] || echo "MISSING $p"; done <<< "$refs"
git status --short
```

## 8. 参考来源

1. Claude Code docs（memory / CLAUDE.md）：
   - `https://docs.anthropic.com/en/docs/claude-code/memory`
2. Claude Code best practices：
   - `https://www.anthropic.com/engineering/claude-code-best-practices`
