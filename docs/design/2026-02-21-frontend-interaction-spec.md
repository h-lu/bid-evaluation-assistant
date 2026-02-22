# 前端交互规范（Vue3）

> 版本：v2026.02.21-r3  
> 状态：Active  
> 对齐：`docs/plans/2026-02-21-end-to-end-unified-design.md`

## 1. 目标

1. 用户可沿主链路完成 `上传 -> 评估 -> 复核 -> 报告`。
2. 长任务状态全程可见，可追溯到 `job_id/trace_id`。
3. 每个评分结论可回跳到原文页内高亮位置。
4. 权限边界与租户边界在 UI 层显式可感知。

## 2. 信息架构

### 2.1 路由

```text
/login
/dashboard
/projects
/projects/:project_id
/projects/:project_id/rules
/documents
/documents/:document_id
/evaluations
/evaluations/:evaluation_id
/evaluations/:evaluation_id/report
/jobs
/jobs/:job_id
/dlq
/admin/audit
```

### 2.2 角色可见性

| 页面 | admin | agent | evaluator | viewer |
| --- | --- | --- | --- | --- |
| 项目配置 | 读写 | 读写 | 只读 | 只读 |
| 文档上传 | 是 | 是 | 是 | 否 |
| 发起评估 | 是 | 是 | 是 | 否 |
| 人工复核 | 是 | 是 | 是 | 否 |
| DLQ 处置 | 是 | requeue | 只读 | 否 |
| 审计查询 | 是 | 否 | 否 | 否 |

## 3. 主链路页面设计

### 3.1 文档上传页

必备行为：

1. 批量上传与断点续传提示。
2. 上传后立即展示 `job_id` 与状态入口。
3. 解析状态实时刷新（polling 或 SSE）。
4. 失败项可查看错误码与 trace。

禁用行为：

1. 客户端自行判断“成功”；必须以 `/jobs/{job_id}` 为准。
2. 未完成 `indexed` 前禁止发起正式评估。

### 3.2 评估详情页（核心）

布局（ASCII）：

```text
+--------------------------------------------------------------------+
| 项目信息 | 供应商 | 当前状态 | trace_id | 操作(复核/导出/回滚)        |
+--------------------------------------------------------------------+
| 左侧：点对点评分表（招标要求 vs 投标响应 vs 评分 vs 理由 vs 置信度） |
+--------------------------------------------------------------------+
| 下方：证据面板（按评分项分组，点击可回跳）                         |
+--------------------------------------------------------------------+
| 右侧：PDF 查看器（页码定位 + bbox 高亮 + 上下文片段）               |
+--------------------------------------------------------------------+
```

点对点评分表字段：

1. `criteria_name`
2. `requirement_text`
3. `response_text`
4. `hard_pass`
5. `score/max_score`
6. `reason`
7. `confidence`
8. `citations_count`

### 3.3 人工复核页

1. 展示触发原因（低置信、低覆盖、偏差过高、红线冲突）。
2. 展示建议动作：`approve/reject/edit_scores`。
3. 提交时必须包含 `resume_token + comment`。
4. 提交结果展示新的 `job_id`。

### 3.4 DLQ 管理页

1. 筛选：`status/error_code/job_type/tenant/project`。
2. 操作：`requeue/discard`。
3. discard 必须显示双人复核状态与原因。

## 4. 引用回跳与 PDF 高亮

### 4.1 citation 数据契约

```json
{
  "chunk_id": "ck_xxx",
  "document_id": "doc_xxx",
  "page": 8,
  "bbox": [120.2, 310.0, 520.8, 365.4],
  "quote": "原文片段...",
  "context": "上下文..."
}
```

### 4.2 高亮流程

```text
点击评分项
 -> 拉取 citation
 -> 打开对应 document/page
 -> bbox 转 viewport 坐标
 -> 绘制高亮层
 -> 同步滚动到目标区域
```

### 4.3 坐标规则

1. 输入 bbox 统一 `[x0,y0,x1,y1]`。
2. 由前端根据当前缩放比转换坐标。
3. bbox 缺失时回退到页内文本定位。

## 5. 状态管理

### 5.1 全局状态划分

1. `auth_state`
2. `project_state`
3. `job_state`
4. `evaluation_state`
5. `citation_state`

### 5.2 任务状态同步

优先 SSE，回退 polling：

1. SSE 通道断开后自动切 polling。
2. polling 默认 3 秒，失败后指数退避到 15 秒。
3. 任务结束后停止轮询。

## 6. 前端安全约束

1. 不在 `localStorage/sessionStorage` 保存高敏 token。
2. refresh token 仅 HttpOnly Cookie。
3. 每个请求附带 CSRF token（对需要的端点）。
4. 403/401 自动触发重认证流程。

## 7. 可用性与反馈

1. 每个长任务显示状态、耗时、重试次数。
2. 错误提示包含 `error_code` 与建议动作。
3. 关键操作（复核、discard）使用二次确认弹窗。
4. 导出报告支持“可追溯证据摘要”附录。

## 8. 性能目标

1. 首屏可交互时间 `<= 2.5s`（常规网络）。
2. 评估页切换响应 `<= 1.0s`（缓存命中）。
3. citation 点击到高亮出现 `<= 1.5s`。

## 9. E2E 场景（必须）

1. 上传成功并进入 indexed。
2. 发起评估并生成报告。
3. 触发 HITL 并恢复。
4. citation 回跳与高亮。
5. DLQ requeue 与状态闭环。
6. 跨角色权限限制验证。

## 10. 验收标准

1. 主链路页面全部可用。
2. 证据回跳成功率 >= 98%。
3. 高风险操作前端交互符合审批约束。
4. 无敏感信息泄露到浏览器持久存储。

## 11. 参考来源（核验：2026-02-21）

1. ProposalLLM（点对点结构借鉴）
2. kotaemon（citation 回跳交互借鉴）
3. 历史融合提交：`53e3d92`, `beef3e9`

## 12. 实施更新（2026-02-23）

1. 新增前端最小工程：`frontend/`（Vue3 + Vite + vue-router + pinia）。
2. 已落地路由骨架：`/dashboard /documents /evaluations /jobs /dlq`，其余路由预留占位页。
3. 已接通核心 API：
   - `GET /healthz`
   - `POST /api/v1/documents/upload`
   - `POST /api/v1/evaluations`
   - `GET /api/v1/jobs`
   - `GET /api/v1/jobs/{job_id}`
   - `GET /api/v1/dlq/items`
   - `POST /api/v1/dlq/items/{item_id}/requeue`
   - `POST /api/v1/dlq/items/{item_id}/discard`
4. 前端启动说明见：`frontend/README.md`。
