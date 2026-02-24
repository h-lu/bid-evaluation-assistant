# 贡献指南

## 分支策略

⚠️ **禁止直接提交到 main 分支**

### 正确的工作流程

1. **创建功能分支**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/your-feature-name
   ```

2. **提交修改**
   ```bash
   git add .
   git commit -m "feat: 描述你的改动"
   ```

3. **推送到远程**
   ```bash
   git push -u origin feat/your-feature-name
   ```

4. **创建 Pull Request**
   ```bash
   gh pr create --title "feat: 描述" --body "详细说明"
   ```

5. **等待 Code Review 通过后合并**

### 禁止的操作

❌ 直接 `git push origin main`
❌ `--force` 推送到 main
❌ 未经审查直接合并
