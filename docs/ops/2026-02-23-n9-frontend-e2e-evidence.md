# N9 前端 E2E 与引用真实化证据

> 日期：2026-02-23  
> 分支：`codex/n6-n10-implementation`

## 1. 目标

1. 上传->评估->HITL->报告全流程 E2E 自动化。
2. citation 回跳与 bbox 高亮对接真实坐标。
3. 权限门控与双人复核交互可验证。

## 1.1 SSOT 对齐要点

1. 主链路必须覆盖 `上传 -> 解析建库 -> 检索评分 -> HITL -> 报告归档`。
2. 高风险动作双人复核流程需前端可见并阻断。
3. 引用回跳必须基于解析定位字段（`page/bbox`）。

## 2. 变更点

1. 新增 Playwright E2E 脚本（`frontend/scripts/e2e-smoke.mjs`）。
2. 前端报告页补齐 `report_uri/score_deviation/redline_conflict/unsupported_claims` 展示。
3. HITL 触发原因前端可视化。
4. E2E 脚本通过 API 完成上传/解析/评估并验证报告页。
5. 引用回跳使用 PDF.js 渲染与 bbox 真实坐标映射。

## 3. 测试命令与结果（已执行）

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8010
cd frontend
npm install
npx playwright install chromium
VITE_API_BASE_URL=http://127.0.0.1:8010 npm run dev -- --host 127.0.0.1 --port 5173
E2E_BASE_URL=http://127.0.0.1:5173 E2E_API_BASE_URL=http://127.0.0.1:8010 E2E_TENANT_ID=tenant_demo npm run test:e2e
```

结果：通过（全链路包含上传->解析->评估->报告页渲染，`VITE_API_BASE_URL` 指向 `8010`）。

## 4. 结论

E2E 脚本已执行通过。
