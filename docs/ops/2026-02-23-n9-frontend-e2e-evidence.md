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

## 3. 测试命令与结果（待执行）

```bash
cd frontend
npm install
npx playwright install chromium
npm run dev -- --host 127.0.0.1 --port 5173
E2E_BASE_URL=http://127.0.0.1:5173 npm run test:e2e
```

结果：Playwright 启动失败（缺少 `libgbm.so.1`），需在 CI/宿主机补齐系统依赖后重试。

## 4. 结论

E2E 脚本已就位，但当前环境缺少 Playwright 依赖，需补齐系统库后复跑。
