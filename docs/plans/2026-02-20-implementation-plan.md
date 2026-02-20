# 辅助评标专家系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个基于 Agentic RAG 的医疗器械招投标辅助评标系统，实现投标文件智能解析、合规性自动审查、智能评分建议。

**Architecture:** 分层单体架构，后端 FastAPI + 前端 Vue3，使用 LangGraph 构建 Agent 工作流，ChromaDB 作为向量数据库，支持 LLM 多 Provider 切换。

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, LangGraph, LangChain, ChromaDB, BGE-M3, Vue3, Element Plus

---

## 阶段一：项目初始化与基础RAG（Week 1-2）

### Task 1: 创建项目目录结构

**Files:**
- Create: `backend/`
- Create: `backend/src/`
- Create: `backend/src/__init__.py`
- Create: `backend/src/core/`
- Create: `backend/src/core/__init__.py`
- Create: `backend/tests/`
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`

**Step 1: 创建目录结构**

```bash
mkdir -p backend/src/{core,api,services,agents,rag,document,models}
mkdir -p backend/tests/{unit,integration}
mkdir -p backend/config/agents
mkdir -p data/{uploads,parsed,knowledge_base}
touch backend/src/__init__.py
touch backend/src/core/__init__.py
touch backend/src/api/__init__.py
touch backend/src/services/__init__.py
touch backend/src/agents/__init__.py
touch backend/src/rag/__init__.py
touch backend/src/document/__init__.py
touch backend/src/models/__init__.py
```

**Step 2: 创建 pyproject.toml**

```toml
# backend/pyproject.toml
[project]
name = "bid-evaluation-assistant"
version = "1.0.0"
description = "辅助评标专家系统 - 基于Agentic RAG的智能评标助手"
requires-python = ">=3.11"
readme = "README.md"

dependencies = [
    # Web框架
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",

    # 数据库
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",

    # 向量数据库
    "chromadb>=0.5.0",

    # LLM框架
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langchain-community>=0.3.0",
    "langgraph>=0.2.0",

    # Embedding
    "sentence-transformers>=3.0.0",

    # 工具
    "httpx>=0.27.0",
    "tenacity>=9.0.0",
    "orjson>=3.10.0",
    "pyyaml>=6.0",
    "python-multipart>=0.0.17",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",

    # 文档处理
    "pypdf>=5.0.0",

    # 可观测性
    "langfuse>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.6.0",
    "mypy>=1.11.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

**Step 3: 创建 .env.example**

```env
# backend/.env.example
# 应用配置
APP_NAME=bid-evaluation-assistant
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/bid_eval

# ChromaDB配置
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_PERSIST_DIR=./data/chroma

# Redis配置
REDIS_URL=redis://localhost:6379/0

# LLM配置 - DeepSeek
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# LLM配置 - Qwen
QWEN_API_KEY=your-qwen-api-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Langfuse配置（可观测性）
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
LANGFUSE_HOST=http://localhost:3000

# 文件存储
UPLOAD_DIR=./data/uploads
PARSED_DIR=./data/parsed
```

**Step 4: Commit**

```bash
git add backend/ data/
git commit -m "feat: 初始化后端项目结构

- 创建项目目录结构
- 添加 pyproject.toml 依赖配置
- 添加 .env.example 环境变量模板"
```

---

### Task 2: 实现核心配置模块

**Files:**
- Create: `backend/src/core/config.py`
- Create: `backend/tests/unit/test_config.py`

**Step 1: 写失败的测试**

```python
# backend/tests/unit/test_config.py
import os
import pytest
from pydantic import ValidationError


def test_settings_default_values():
    """测试默认配置值"""
    from src.core.config import Settings

    # 设置必要的环境变量
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"

    settings = Settings()

    assert settings.APP_NAME == "bid-evaluation-assistant"
    assert settings.APP_ENV == "development"
    assert settings.DEBUG is True


def test_settings_requires_secret_key():
    """测试 SECRET_KEY 是必需的"""
    # 清除环境变量
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]

    with pytest.raises(ValidationError):
        from src.core.config import Settings
        Settings()


def test_llm_config():
    """测试 LLM 配置"""
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
    os.environ["DEEPSEEK_API_KEY"] = "test-deepseek-key"

    from src.core.config import Settings

    settings = Settings()

    assert settings.DEEPSEEK_API_KEY == "test-deepseek-key"
    assert settings.DEEPSEEK_BASE_URL == "https://api.deepseek.com"
```

**Step 2: 运行测试确认失败**

```bash
cd backend && python -m pytest tests/unit/test_config.py -v
```

Expected: FAIL (ModuleNotFoundError)

**Step 3: 实现配置模块**

```python
# backend/src/core/config.py
"""
核心配置模块
使用 pydantic-settings 管理环境变量和配置
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 应用配置
    APP_NAME: str = "bid-evaluation-assistant"
    APP_ENV: str = Field(default="development", pattern="^(development|staging|production)$")
    DEBUG: bool = True
    SECRET_KEY: str  # 必需，无默认值

    # API配置
    API_PREFIX: str = "/api/v1"

    # 数据库配置
    DATABASE_URL: str  # 必需

    # ChromaDB配置
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM配置 - DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # LLM配置 - Qwen (通义千问)
    QWEN_API_KEY: Optional[str] = None
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # LLM配置 - OpenAI兼容
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None

    # Langfuse配置（可观测性）
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "http://localhost:3000"

    # 文件存储
    UPLOAD_DIR: str = "./data/uploads"
    PARSED_DIR: str = "./data/parsed"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # JWT配置
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # Agent配置
    DEFAULT_LLM_PROVIDER: str = "deepseek"
    CONFIDENCE_THRESHOLD: float = 0.75
    MAX_ITERATIONS: int = 5

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: str | bool) -> bool:
        if isinstance(v, bool):
            return v
        return v.lower() in ("true", "1", "yes")


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 导出便捷访问
settings = get_settings()
```

**Step 4: 运行测试确认通过**

```bash
cd backend && python -m pytest tests/unit/test_config.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/core/config.py backend/tests/unit/test_config.py
git commit -m "feat: 实现核心配置模块

- 使用 pydantic-settings 管理环境变量
- 支持 DeepSeek、Qwen、OpenAI 多 LLM 配置
- 添加配置单元测试"
```

---

### Task 3: 实现 LLM 服务抽象层

**Files:**
- Create: `backend/src/services/llm/`
- Create: `backend/src/services/llm/__init__.py`
- Create: `backend/src/services/llm/base.py`
- Create: `backend/src/services/llm/providers.py`
- Create: `backend/src/services/llm/gateway.py`
- Create: `backend/tests/unit/test_llm_gateway.py`

**Step 1: 写失败的测试**

```python
# backend/tests/unit/test_llm_gateway.py
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_llm_gateway_get_provider():
    """测试获取 Provider"""
    from src.services.llm.gateway import LLMGateway

    gateway = LLMGateway()
    provider = gateway.get_provider("deepseek")

    assert provider is not None
    assert provider.name == "deepseek"


@pytest.mark.asyncio
async def test_llm_gateway_chat():
    """测试聊天接口"""
    from src.services.llm.gateway import LLMGateway

    gateway = LLMGateway()

    # Mock LLM 响应
    with patch.object(gateway, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "这是一个测试响应"

        response = await gateway.chat(
            provider="deepseek",
            model="deepseek-chat",
            messages=[{"role": "user", "content": "你好"}]
        )

        assert response == "这是一个测试响应"


@pytest.mark.asyncio
async def test_llm_provider_not_found():
    """测试 Provider 不存在"""
    from src.services.llm.gateway import LLMGateway

    gateway = LLMGateway()

    with pytest.raises(ValueError, match="Provider not found"):
        gateway.get_provider("nonexistent")
```

**Step 2: 运行测试确认失败**

```bash
cd backend && python -m pytest tests/unit/test_llm_gateway.py -v
```

Expected: FAIL (ModuleNotFoundError)

**Step 3: 实现 LLM 抽象层基类**

```python
# backend/src/services/llm/base.py
"""
LLM Provider 抽象基类
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    def __init__(
        self,
        name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def chat(
        self,
        messages: List[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """同步聊天接口"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式聊天接口"""
        pass

    def is_available(self) -> bool:
        """检查 Provider 是否可用"""
        return self.api_key is not None
```

**Step 4: 实现 Provider 实现**

```python
# backend/src/services/llm/providers.py
"""
具体的 LLM Provider 实现
"""
import os
from typing import AsyncIterator, List, Optional

from langchain_openai import ChatOpenAI

from .base import BaseLLMProvider


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI 兼容的 Provider（支持 DeepSeek、Qwen、OpenAI）"""

    def __init__(
        self,
        name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o-mini",
    ):
        super().__init__(name, api_key, base_url)
        self.default_model = default_model
        self._client: Optional[ChatOpenAI] = None

    def _get_client(self, model: str, temperature: float, max_tokens: int) -> ChatOpenAI:
        """获取或创建 LangChain ChatOpenAI 客户端"""
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def chat(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """同步聊天接口"""
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not available: missing API key")

        model = model or self.default_model
        client = self._get_client(model, temperature, max_tokens)

        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        response = await client.ainvoke(lc_messages)
        return response.content

    async def stream(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式聊天接口"""
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not available: missing API key")

        model = model or self.default_model
        client = self._get_client(model, temperature, max_tokens)

        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        async for chunk in client.astream(lc_messages):
            if chunk.content:
                yield chunk.content


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek Provider"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(
            name="deepseek",
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com",
            default_model="deepseek-chat",
        )


class QwenProvider(OpenAICompatibleProvider):
    """Qwen (通义千问) Provider"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(
            name="qwen",
            api_key=api_key,
            base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            default_model="qwen-turbo",
        )


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI Provider"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(
            name="openai",
            api_key=api_key,
            base_url=base_url,
            default_model="gpt-4o-mini",
        )
```

**Step 5: 实现 LLM Gateway**

```python
# backend/src/services/llm/gateway.py
"""
LLM Gateway - 统一的 LLM 访问入口
支持多 Provider 切换、负载均衡、故障转移
"""
from typing import AsyncIterator, Dict, List, Optional

from src.core.config import settings

from .base import BaseLLMProvider
from .providers import DeepSeekProvider, OpenAIProvider, QwenProvider


class LLMGateway:
    """
    LLM Gateway

    统一的 LLM 访问入口，支持：
    - 多 Provider 管理
    - 动态 Provider 切换
    - 按需创建 Provider 实例
    """

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """初始化所有可用的 Provider"""
        # DeepSeek
        if settings.DEEPSEEK_API_KEY:
            self._providers["deepseek"] = DeepSeekProvider(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
            )

        # Qwen
        if settings.QWEN_API_KEY:
            self._providers["qwen"] = QwenProvider(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
            )

        # OpenAI
        if settings.OPENAI_API_KEY:
            self._providers["openai"] = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )

    def get_provider(self, name: str) -> BaseLLMProvider:
        """获取指定 Provider"""
        if name not in self._providers:
            raise ValueError(f"Provider not found: {name}")
        return self._providers[name]

    def list_providers(self) -> List[str]:
        """列出所有可用的 Provider"""
        return list(self._providers.keys())

    async def chat(
        self,
        messages: List[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """
        聊天接口

        Args:
            messages: 消息列表
            provider: Provider 名称，默认使用 DEFAULT_LLM_PROVIDER
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            模型响应文本
        """
        provider_name = provider or settings.DEFAULT_LLM_PROVIDER
        provider_instance = self.get_provider(provider_name)

        return await provider_instance.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def stream(
        self,
        messages: List[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        流式聊天接口
        """
        provider_name = provider or settings.DEFAULT_LLM_PROVIDER
        provider_instance = self.get_provider(provider_name)

        async for chunk in provider_instance.stream(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk


# 全局单例
_gateway: Optional[LLMGateway] = None


def get_gateway() -> LLMGateway:
    """获取 LLM Gateway 单例"""
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
```

**Step 6: 创建 __init__.py**

```python
# backend/src/services/llm/__init__.py
"""
LLM 服务模块
"""
from .base import BaseLLMProvider
from .gateway import LLMGateway, get_gateway
from .providers import DeepSeekProvider, OpenAIProvider, QwenProvider

__all__ = [
    "BaseLLMProvider",
    "LLMGateway",
    "get_gateway",
    "DeepSeekProvider",
    "OpenAIProvider",
    "QwenProvider",
]
```

**Step 7: 运行测试确认通过**

```bash
cd backend && python -m pytest tests/unit/test_llm_gateway.py -v
```

Expected: PASS

**Step 8: Commit**

```bash
git add backend/src/services/llm/ backend/tests/unit/test_llm_gateway.py
git commit -m "feat: 实现 LLM 服务抽象层

- 添加 BaseLLMProvider 抽象基类
- 实现 DeepSeek、Qwen、OpenAI Provider
- 实现 LLMGateway 统一访问入口
- 支持同步和流式响应"
```

---

### Task 4: 实现 FastAPI 应用入口

**Files:**
- Create: `backend/src/main.py`
- Create: `backend/src/api/__init__.py`
- Create: `backend/src/api/health.py`
- Create: `backend/tests/unit/test_api.py`

**Step 1: 写失败的测试**

```python
# backend/tests/unit/test_api.py
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查接口"""
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_openapi_docs():
    """测试 OpenAPI 文档可访问"""
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/docs")

    assert response.status_code == 200
```

**Step 2: 运行测试确认失败**

```bash
cd backend && python -m pytest tests/unit/test_api.py -v
```

Expected: FAIL

**Step 3: 实现健康检查 API**

```python
# backend/src/api/health.py
"""
健康检查 API
"""
from fastapi import APIRouter

from src.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }
```

**Step 4: 实现主应用入口**

```python
# backend/src/main.py
"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.health import router as health_router
from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"🚀 {settings.APP_NAME} starting...")
    yield
    # 关闭时
    print(f"👋 {settings.APP_NAME} shutting down...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        description="辅助评标专家系统 - 基于Agentic RAG的智能评标助手",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境需要配置具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(health_router, prefix=settings.API_PREFIX)

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
```

**Step 5: 运行测试确认通过**

```bash
cd backend && python -m pytest tests/unit/test_api.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add backend/src/main.py backend/src/api/ backend/tests/unit/test_api.py
git commit -m "feat: 实现 FastAPI 应用入口

- 添加健康检查 API
- 配置 CORS 中间件
- 支持开发模式热重载"
```

---

### Task 5: 实现向量存储服务

**Files:**
- Create: `backend/src/rag/__init__.py`
- Create: `backend/src/rag/embeddings.py`
- Create: `backend/src/rag/vectorstore.py`
- Create: `backend/tests/unit/test_vectorstore.py`

**Step 1: 写失败的测试**

```python
# backend/tests/unit/test_vectorstore.py
import pytest
from unittest.mock import Mock, patch


def test_embedding_model_initialization():
    """测试 Embedding 模型初始化"""
    from src.rag.embeddings import EmbeddingService

    with patch("src.rag.embeddings.SentenceTransformer") as mock_transformer:
        mock_transformer.return_value = Mock()

        service = EmbeddingService()

        assert service.model is not None


def test_embedding_encode():
    """测试文本编码"""
    from src.rag.embeddings import EmbeddingService

    with patch("src.rag.embeddings.SentenceTransformer") as mock_transformer:
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        embeddings = service.encode(["测试文本"])

        assert len(embeddings) == 1
        assert len(embeddings[0]) == 3


@pytest.mark.asyncio
async def test_vectorstore_add_documents():
    """测试添加文档到向量库"""
    from src.rag.vectorstore import VectorStoreService

    with patch("src.rag.vectorstore.Chroma") as mock_chroma:
        mock_collection = Mock()
        mock_chroma.return_value = mock_collection

        service = VectorStoreService()

        # 这个测试验证接口存在
        assert service is not None
```

**Step 2: 运行测试确认失败**

```bash
cd backend && python -m pytest tests/unit/test_vectorstore.py -v
```

Expected: FAIL

**Step 3: 实现 Embedding 服务**

```python
# backend/src/rag/embeddings.py
"""
Embedding 服务
使用 sentence-transformers 提供文本向量化能力
"""
from typing import List, Optional

from sentence_transformers import SentenceTransformer

from src.core.config import settings


class EmbeddingService:
    """
    Embedding 服务

    使用 BGE 系列模型进行文本向量化
    """

    # 默认使用 BGE-small-zh（轻量级中文模型）
    DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"

    def __init__(self, model_name: Optional[str] = None):
        """
        初始化 Embedding 服务

        Args:
            model_name: 模型名称，默认使用 BGE-small-zh
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """延迟加载模型"""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(
        self,
        texts: List[str],
        normalize_embeddings: bool = True,
    ) -> List[List[float]]:
        """
        将文本编码为向量

        Args:
            texts: 文本列表
            normalize_embeddings: 是否归一化向量

        Returns:
            向量列表
        """
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize_embeddings,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def encode_single(self, text: str) -> List[float]:
        """编码单个文本"""
        return self.encode([text])[0]

    @property
    def dimension(self) -> int:
        """获取向量维度"""
        return self.model.get_sentence_embedding_dimension()


# 全局单例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取 Embedding 服务单例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
```

**Step 4: 实现向量存储服务**

```python
# backend/src/rag/vectorstore.py
"""
向量存储服务
使用 ChromaDB 作为向量数据库
"""
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.core.config import settings

from .embeddings import EmbeddingService, get_embedding_service


class VectorStoreService:
    """
    向量存储服务

    封装 ChromaDB，提供文档存储和检索能力
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        persist_directory: Optional[str] = None,
    ):
        """
        初始化向量存储服务

        Args:
            embedding_service: Embedding 服务
            persist_directory: 持久化目录
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR

        self._client: Optional[chromadb.Client] = None
        self._collections: Dict[str, chromadb.Collection] = {}

    @property
    def client(self) -> chromadb.Client:
        """获取 ChromaDB 客户端"""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def get_collection(self, name: str) -> chromadb.Collection:
        """获取或创建集合"""
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        """
        添加文档到向量库

        Args:
            collection_name: 集合名称
            documents: 文档列表
            metadatas: 元数据列表
            ids: 文档 ID 列表
        """
        collection = self.get_collection(collection_name)

        # 生成 embeddings
        embeddings = self.embedding_service.encode(documents)

        # 生成 ID
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]

        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        查询相似文档

        Args:
            collection_name: 集合名称
            query_text: 查询文本
            n_results: 返回结果数量
            where: 过滤条件

        Returns:
            查询结果
        """
        collection = self.get_collection(collection_name)

        # 编码查询
        query_embedding = self.embedding_service.encode_single(query_text)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        return results

    def delete_collection(self, name: str) -> None:
        """删除集合"""
        self.client.delete_collection(name)
        if name in self._collections:
            del self._collections[name]

    def count(self, collection_name: str) -> int:
        """获取集合中的文档数量"""
        collection = self.get_collection(collection_name)
        return collection.count()


# 全局单例
_vectorstore: Optional[VectorStoreService] = None


def get_vectorstore() -> VectorStoreService:
    """获取向量存储服务单例"""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = VectorStoreService()
    return _vectorstore
```

**Step 5: 创建 __init__.py**

```python
# backend/src/rag/__init__.py
"""
RAG 模块
"""
from .embeddings import EmbeddingService, get_embedding_service
from .vectorstore import VectorStoreService, get_vectorstore

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "VectorStoreService",
    "get_vectorstore",
]
```

**Step 6: 运行测试确认通过**

```bash
cd backend && python -m pytest tests/unit/test_vectorstore.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add backend/src/rag/ backend/tests/unit/test_vectorstore.py
git commit -m "feat: 实现向量存储服务

- 添加 EmbeddingService 使用 BGE 模型
- 添加 VectorStoreService 封装 ChromaDB
- 支持文档添加、查询、删除操作"
```

---

## 阶段二总结检查点

完成以上任务后，你应该有：

```
backend/
├── src/
│   ├── core/
│   │   └── config.py          ✅ 配置管理
│   ├── services/
│   │   └── llm/               ✅ LLM 抽象层
│   ├── api/
│   │   └── health.py          ✅ 健康检查 API
│   ├── rag/
│   │   ├── embeddings.py      ✅ Embedding 服务
│   │   └── vectorstore.py     ✅ 向量存储服务
│   └── main.py                ✅ 应用入口
└── tests/
    └── unit/                  ✅ 单元测试
```

**运行验证：**

```bash
cd backend
pip install -e ".[dev]"
python -m pytest tests/ -v --cov=src
```

---

## 阶段二：Agent 能力（Week 3-4）

### Task 6: 实现 Agent 基础架构

**Files:**
- Create: `backend/src/agents/base.py`
- Create: `backend/src/agents/state.py`
- Create: `backend/src/agents/registry.py`
- Create: `backend/tests/unit/test_agents.py`

**Step 1: 写失败的测试**

```python
# backend/tests/unit/test_agents.py
import pytest
from src.agents.state import BidEvaluationState


def test_bid_evaluation_state_defaults():
    """测试评标状态默认值"""
    state = BidEvaluationState()

    assert state.tender_id == ""
    assert state.bid_documents == []
    assert state.current_stage == "init"


def test_bid_evaluation_state_with_data():
    """测试评标状态带数据"""
    state = BidEvaluationState(
        tender_id="T001",
        bid_documents=[{"doc_id": "B001"}],
        current_stage="parsing",
    )

    assert state.tender_id == "T001"
    assert len(state.bid_documents) == 1


def test_agent_registry():
    """测试 Agent 注册表"""
    from src.agents.registry import AgentRegistry

    registry = AgentRegistry()

    # 注册一个 Agent
    @registry.register("test_agent")
    class TestAgent:
        pass

    assert "test_agent" in registry.list_agents()
    assert registry.get_agent("test_agent") == TestAgent
```

**Step 2: 运行测试确认失败**

```bash
cd backend && python -m pytest tests/unit/test_agents.py -v
```

**Step 3: 实现 Agent 状态定义**

```python
# backend/src/agents/state.py
"""
Agent 状态定义
使用 TypedDict 定义 LangGraph 状态
"""
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import add_messages


class BidDocument(TypedDict):
    """投标文档结构"""
    doc_id: str
    company_name: str
    file_path: str
    content: str
    extracted_info: Dict[str, Any]


class ReviewResult(TypedDict):
    """审查结果"""
    passed: bool
    items: List[Dict[str, Any]]
    warnings: List[str]
    confidence: float


class BidEvaluationState(TypedDict, total=False):
    """
    评标状态

    用于 LangGraph 状态机，跟踪评标流程中的所有数据
    """
    # 输入
    tender_id: str
    tender_requirements: Dict[str, Any]
    bid_documents: List[BidDocument]

    # 消息历史（用于 LangGraph）
    messages: Annotated[list, add_messages]

    # 当前阶段
    current_stage: str

    # 提取的结构化数据
    extracted_data: Dict[str, Any]

    # 各 Agent 输出
    compliance_result: Optional[ReviewResult]
    technical_result: Optional[ReviewResult]
    commercial_result: Optional[ReviewResult]

    # 评分
    technical_score: Optional[float]
    commercial_score: Optional[float]
    price_score: Optional[float]
    total_score: Optional[float]

    # 异常检测
    anomaly_alerts: List[Dict[str, Any]]

    # 人工审核
    requires_human_review: bool
    human_review_reason: Optional[str]

    # 最终报告
    final_report: Optional[Dict[str, Any]]

    # 错误
    errors: List[str]


def create_initial_state(
    tender_id: str,
    tender_requirements: Dict[str, Any],
    bid_documents: List[BidDocument],
) -> BidEvaluationState:
    """创建初始状态"""
    return BidEvaluationState(
        tender_id=tender_id,
        tender_requirements=tender_requirements,
        bid_documents=bid_documents,
        messages=[],
        current_stage="init",
        extracted_data={},
        compliance_result=None,
        technical_result=None,
        commercial_result=None,
        technical_score=None,
        commercial_score=None,
        price_score=None,
        total_score=None,
        anomaly_alerts=[],
        requires_human_review=False,
        human_review_reason=None,
        final_report=None,
        errors=[],
    )
```

**Step 4: 实现 Agent 注册表**

```python
# backend/src/agents/registry.py
"""
Agent 注册表
支持动态注册和获取 Agent
"""
from typing import Any, Callable, Dict, Optional, Type


class AgentRegistry:
    """
    Agent 注册表

    用于动态注册、发现和管理 Agent
    """

    _instance: Optional["AgentRegistry"] = None

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: Dict[str, Type[Any]] = {}
            cls._instance._factories: Dict[str, Callable] = {}
        return cls._instance

    def register(self, name: str) -> Callable:
        """
        注册 Agent 装饰器

        Usage:
            @registry.register("my_agent")
            class MyAgent:
                pass
        """
        def decorator(cls: Type[Any]) -> Type[Any]:
            self._agents[name] = cls
            return cls
        return decorator

    def register_factory(self, name: str, factory: Callable) -> None:
        """注册 Agent 工厂函数"""
        self._factories[name] = factory

    def get_agent(self, name: str) -> Optional[Type[Any]]:
        """获取已注册的 Agent 类"""
        return self._agents.get(name)

    def get_factory(self, name: str) -> Optional[Callable]:
        """获取 Agent 工厂函数"""
        return self._factories.get(name)

    def list_agents(self) -> List[str]:
        """列出所有已注册的 Agent"""
        return list(self._agents.keys())

    def create_agent(self, name: str, *args, **kwargs) -> Any:
        """创建 Agent 实例"""
        if name in self._factories:
            return self._factories[name](*args, **kwargs)

        agent_cls = self._agents.get(name)
        if agent_cls is None:
            raise ValueError(f"Agent not found: {name}")

        return agent_cls(*args, **kwargs)


# 全局注册表实例
registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """获取全局注册表"""
    return registry
```

**Step 5: 实现 Agent 基类**

```python
# backend/src/agents/base.py
"""
Agent 基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.services.llm import LLMGateway, get_gateway

from .state import BidEvaluationState


class BaseAgent(ABC):
    """
    Agent 抽象基类

    所有评标 Agent 都应该继承此类
    """

    def __init__(
        self,
        name: str,
        llm_gateway: Optional[LLMGateway] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.name = name
        self.llm_gateway = llm_gateway or get_gateway()
        self.model = model
        self.provider = provider

    @abstractmethod
    async def run(self, state: BidEvaluationState) -> BidEvaluationState:
        """
        执行 Agent 逻辑

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        pass

    async def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """调用 LLM 进行对话"""
        return await self.llm_gateway.chat(
            messages=messages,
            provider=self.provider,
            model=self.model,
            temperature=temperature,
            **kwargs,
        )

    def update_state(
        self,
        state: BidEvaluationState,
        updates: Dict[str, Any],
    ) -> BidEvaluationState:
        """更新状态"""
        new_state = dict(state)
        new_state.update(updates)
        return BidEvaluationState(**new_state)
```

**Step 6: 创建 __init__.py**

```python
# backend/src/agents/__init__.py
"""
Agent 模块
"""
from .base import BaseAgent
from .registry import AgentRegistry, get_registry, registry
from .state import BidEvaluationState, create_initial_state

__all__ = [
    "BaseAgent",
    "AgentRegistry",
    "get_registry",
    "registry",
    "BidEvaluationState",
    "create_initial_state",
]
```

**Step 7: 运行测试确认通过**

```bash
cd backend && python -m pytest tests/unit/test_agents.py -v
```

**Step 8: Commit**

```bash
git add backend/src/agents/ backend/tests/unit/test_agents.py
git commit -m "feat: 实现 Agent 基础架构

- 添加 BidEvaluationState 状态定义
- 添加 AgentRegistry 动态注册机制
- 添加 BaseAgent 抽象基类"
```

---

## 阶段一&二 完成检查

```bash
# 运行所有测试
cd backend && python -m pytest tests/ -v --cov=src

# 启动服务测试
cd backend && python -m uvicorn src.main:app --reload
```

---

## 后续阶段预览

### 阶段三：多智能体协作（Week 5-6）

- Task 7: 实现合规审查 Agent
- Task 8: 实现技术评审 Agent
- Task 9: 实现 LangGraph 工作流编排
- Task 10: 实现 Self-Reflective RAG

### 阶段四：生产部署（Week 7-8）

- Task 11: 实现数据库模型
- Task 12: 实现用户认证
- Task 13: 添加 RAGAS 评估
- Task 14: Docker 部署配置
- Task 15: 前端初始化

---

*实现计划版本：v1.0*
*创建日期：2026-02-20*
