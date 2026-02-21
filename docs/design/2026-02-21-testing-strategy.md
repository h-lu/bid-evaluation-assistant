# 测试策略

> 版本：v1.0
> 设计日期：2026-02-21

---

## 一、测试金字塔

```
                    ┌───────────┐
                   │    E2E    │    5%
                  │   Tests   │
                 └───────────┘
                ┌─────────────────┐
               │  Integration    │    15%
              │     Tests        │
             └─────────────────┘
            ┌───────────────────────┐
           │      Unit Tests        │    80%
          │                         │
         └───────────────────────────┘
```

---

## 二、测试覆盖目标

| 测试类型 | 覆盖目标 | 工具 |
|----------|----------|------|
| **单元测试** | ≥ 80% | pytest + pytest-cov |
| **集成测试** | 核心流程 100% | pytest + httpx |
| **E2E 测试** | 主业务流程 | Playwright |
| **RAG 评估** | RAGAS ≥ 0.8 | ragas + deepeval |

---

## 三、单元测试

### 3.1 测试配置

```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from src.main import create_app
from src.core.database import Base

# 使用内存数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session(test_engine):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(test_engine):
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
async def auth_client(client, session):
    """带认证的客户端"""
    from src.modules.user.infrastructure.models.user import User, UserRole
    from src.core.security import get_password_hash

    # 创建测试用户
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        role=UserRole.EVALUATOR
    )
    session.add(user)
    await session.commit()

    # 登录获取 token
    response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "password123"
    })
    token = response.json()["data"]["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"
    yield client
```

### 3.2 单元测试示例

```python
# tests/unit/test_security.py
import pytest
from src.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)


class TestPasswordSecurity:
    """密码安全测试"""

    def test_hash_password_success(self):
        """测试密码哈希成功"""
        password = "Test1234!"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """测试密码验证成功"""
        password = "Test1234!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_wrong(self):
        """测试密码验证失败"""
        password = "Test1234!"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False

    def test_password_too_short(self):
        """测试密码过短"""
        with pytest.raises(ValueError, match="密码长度至少8位"):
            hash_password("short")


class TestJWTToken:
    """JWT Token 测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        assert token is not None
        assert isinstance(token, str)
```

```python
# tests/unit/test_services.py
import pytest
from unittest.mock import AsyncMock, patch
from src.modules.evaluation.services.evaluator import EvaluationService


class TestEvaluationService:
    """评估服务测试"""

    @pytest.mark.asyncio
    async def test_calculate_weighted_score(self):
        """测试加权评分计算"""
        service = EvaluationService()
        result = service.calculate_weighted_score(
            technical_score=80,
            commercial_score=90,
            qualification_score=100,
            weights={"technical": 0.5, "commercial": 0.3, "qualification": 0.2}
        )
        assert result == 87.0

    @pytest.mark.asyncio
    async def test_get_recommendation_approved(self):
        """测试推荐结果 - 通过"""
        service = EvaluationService()
        recommendation = service.get_recommendation(85)
        assert recommendation == "approved"

    @pytest.mark.asyncio
    async def test_get_recommendation_review(self):
        """测试推荐结果 - 需审核"""
        service = EvaluationService()
        recommendation = service.get_recommendation(55)
        assert recommendation == "review"

    @pytest.mark.asyncio
    async def test_get_recommendation_rejected(self):
        """测试推荐结果 - 不通过"""
        service = EvaluationService()
        recommendation = service.get_recommendation(40)
        assert recommendation == "rejected"
```

---

## 四、集成测试

### 4.1 API 集成测试

```python
# tests/integration/test_projects.py
import pytest
from httpx import AsyncClient


class TestProjectAPI:
    """项目 API 集成测试"""

    @pytest.mark.asyncio
    async def test_create_project(self, auth_client: AsyncClient):
        """测试创建项目"""
        response = await auth_client.post("/api/v1/projects", json={
            "project_name": "测试项目",
            "tender_type": "公开招标",
            "budget": 1000000
        })

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["project_name"] == "测试项目"
        assert data["data"]["project_code"].startswith("PRJ-")

    @pytest.mark.asyncio
    async def test_list_projects(self, auth_client: AsyncClient):
        """测试获取项目列表"""
        # 先创建项目
        await auth_client.post("/api/v1/projects", json={
            "project_name": "测试项目1",
            "tender_type": "公开招标"
        })

        # 获取列表
        response = await auth_client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, auth_client: AsyncClient):
        """测试获取不存在的项目"""
        response = await auth_client.get("/api/v1/projects/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """测试未授权访问"""
        response = await client.get("/api/v1/projects")

        assert response.status_code == 401
```

### 4.2 数据库集成测试

```python
# tests/integration/test_repositories.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.project.infrastructure.repositories import ProjectRepository
from src.modules.project.infrastructure.models.project import BidProject, ProjectStatus


class TestProjectRepository:
    """项目仓库测试"""

    @pytest.mark.asyncio
    async def test_create_project(self, session: AsyncSession):
        """测试创建项目"""
        repo = ProjectRepository(session)

        project = await repo.create({
            "project_code": "PRJ-TEST-001",
            "project_name": "测试项目",
            "tender_type": "公开招标",
            "status": ProjectStatus.DRAFT,
            "created_by": 1
        })

        assert project.id is not None
        assert project.project_name == "测试项目"

    @pytest.mark.asyncio
    async def test_get_by_id(self, session: AsyncSession):
        """测试根据 ID 获取"""
        repo = ProjectRepository(session)

        # 创建项目
        created = await repo.create({
            "project_code": "PRJ-TEST-002",
            "project_name": "测试项目2",
            "tender_type": "公开招标",
            "status": ProjectStatus.DRAFT,
            "created_by": 1
        })

        # 获取项目
        found = await repo.get_by_id(created.id)

        assert found is not None
        assert found.project_name == "测试项目2"

    @pytest.mark.asyncio
    async def test_soft_delete(self, session: AsyncSession):
        """测试软删除"""
        repo = ProjectRepository(session)

        # 创建项目
        created = await repo.create({
            "project_code": "PRJ-TEST-003",
            "project_name": "测试项目3",
            "tender_type": "公开招标",
            "status": ProjectStatus.DRAFT,
            "created_by": 1
        })

        # 软删除
        await repo.soft_delete(created.id)

        # 确认已删除
        found = await repo.get_by_id(created.id, include_deleted=False)
        assert found is None

        # 包含已删除的查询
        found_with_deleted = await repo.get_by_id(created.id, include_deleted=True)
        assert found_with_deleted is not None
        assert found_with_deleted.is_deleted is True
```

---

## 五、RAG 评估测试

### 5.1 RAGAS 评估

```python
# tests/evaluation/test_ragas.py
import pytest
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset


class TestRAGEvaluation:
    """RAG 评估测试"""

    @pytest.fixture
    def eval_dataset(self):
        """评估数据集"""
        return Dataset.from_dict({
            "question": [
                "供应商A的注册资金是多少？",
                "哪家供应商的技术评分最高？",
                "供应商B的资质证书有哪些？"
            ],
            "answer": [
                "供应商A的注册资金为5000万元人民币。",
                "供应商C的技术评分最高，得分为95分。",
                "供应商B持有ISO9001、ISO14001认证证书。"
            ],
            "contexts": [
                ["投标文件-供应商A.pdf 第12页：注册资本5000万元"],
                ["评估结果汇总：供应商C技术分95，供应商A技术分85"],
                ["供应商B资质文件：ISO9001认证有效至2027年，ISO14001认证有效至2027年"]
            ],
            "ground_truth": [
                "5000万元",
                "供应商C",
                "ISO9001, ISO14001"
            ]
        })

    @pytest.mark.asyncio
    async def test_ragas_evaluation(self, eval_dataset):
        """测试 RAGAS 评估指标"""
        result = evaluate(
            eval_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall
            ]
        )

        # 验证各指标达到阈值
        assert result["faithfulness"] >= 0.8
        assert result["answer_relevancy"] >= 0.8
        assert result["context_precision"] >= 0.7
        assert result["context_recall"] >= 0.7
```

### 5.2 DeepEval 幻觉检测

```python
# tests/evaluation/test_hallucination.py
import pytest
from deepeval import assert_test
from deepeval.metrics import HallucinationMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase


class TestHallucination:
    """幻觉检测测试"""

    @pytest.mark.asyncio
    async def test_no_hallucination(self):
        """测试无幻觉"""
        test_case = LLMTestCase(
            input="供应商A的注册资金是多少？",
            actual_output="供应商A的注册资金为5000万元人民币。",
            context=[
                "投标文件-供应商A.pdf 第12页：注册资本5000万元人民币",
                "供应商信息表：注册资金5000万"
            ]
        )

        metric = HallucinationMetric(threshold=0.9)
        assert_test(test_case, [metric])

    @pytest.mark.asyncio
    async def test_faithfulness(self):
        """测试忠实度"""
        test_case = LLMTestCase(
            input="评估供应商A的综合实力",
            actual_output="供应商A技术评分85分，商务评分90分，综合评分87.5分，建议通过。",
            context=[
                "技术评分：85分",
                "商务评分：90分",
                "权重配置：技术50%，商务30%，资质20%"
            ]
        )

        metric = FaithfulnessMetric(threshold=0.8)
        assert_test(test_case, [metric])
```

---

## 六、E2E 测试

### 6.1 Playwright 测试

```typescript
// e2e/evaluation.spec.ts
import { test, expect } from '@playwright/test';

test.describe('评估流程', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('[name="username"]', 'testuser');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('完整的评估流程', async ({ page }) => {
    // 1. 创建项目
    await page.goto('/projects/create');
    await page.fill('[name="projectName"]', 'E2E测试项目');
    await page.selectOption('[name="tenderType"]', '公开招标');
    await page.click('button:has-text("创建")');
    await expect(page.locator('.el-message--success')).toBeVisible();

    // 2. 上传文档
    await page.goto('/documents');
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles('./tests/fixtures/test_document.pdf');
    await page.selectOption('[name="docType"]', 'bid');
    await page.click('button:has-text("上传")');
    await expect(page.locator('.document-status:has-text("已上传")')).toBeVisible();

    // 3. 创建评估
    await page.goto('/evaluations');
    await page.click('button:has-text("新建评估")');
    await page.selectOption('[name="projectId"]', { label: 'E2E测试项目' });
    await page.click('button:has-text("开始评估")');

    // 4. 等待评估完成
    await expect(page.locator('.evaluation-status:has-text("已完成")')).toBeVisible({
      timeout: 60000
    });

    // 5. 查看报告
    await page.click('button:has-text("查看报告")');
    await expect(page.locator('.report-header:has-text("评估报告")')).toBeVisible();
  });
});
```

---

## 七、测试命令

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit -v

# 运行集成测试
pytest tests/integration -v

# 运行 RAG 评估测试
pytest tests/evaluation -v -m "not slow"

# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 运行 E2E 测试
npx playwright test
```

---

## 八、CI/CD 测试配置

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit -v --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test
```

---

*文档版本：v1.0*
*创建日期：2026-02-21*
