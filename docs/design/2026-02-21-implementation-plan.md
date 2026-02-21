# 详细实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
>
> 版本：v1.0
> 设计日期：2026-02-21
> 前置文档：`database-schema-design.md`, `rest-api-specification.md`

---

## 概述

**Goal:** 构建一个可运行的辅助评标专家系统 MVP，支持文档上传、智能解析、RAG 检索、自动评估、人工审核的完整流程。

**Architecture:** 模块化单体架构（FastAPI + PostgreSQL + LightRAG + LangGraph），四层领域驱动设计。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, LightRAG, LangGraph, ChromaDB, PostgreSQL, Vue3

---

## Phase 1: 基础架构（Week 1-2）

### Task 1.1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `backend/src/__init__.py`
- Create: `backend/src/core/__init__.py`
- Create: `.env.example`
- Create: `.gitignore`

**Step 1: 创建 pyproject.toml**

```toml
[project]
name = "bid-evaluation-assistant"
version = "0.1.0"
description = "AI-powered bid evaluation assistant system"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.9",
    "aiofiles>=23.0.0",
    "httpx>=0.27.0",
    # RAG & LLM
    "lightrag-hku>=0.1.0",
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "chromadb>=0.5.0",
    # Document parsing
    "magic-pdf[full]>=0.10.0",
    "docling>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
    "mypy>=1.11.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: 创建 .env.example**

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/bid_eval

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini

# Embedding
EMBEDDING_MODEL=BAAI/bge-m3

# Storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=104857600

# LightRAG
LIGHTRAG_WORKING_DIR=./lightrag_storage
```

**Step 3: 创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
.env

# IDE
.vscode/
.idea/

# Project specific
uploads/
lightrag_storage/
*.pdf
*.docx

# Test
.pytest_cache/
.coverage
htmlcov/

# Build
dist/
*.egg-info/
```

**Step 4: 验证**

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"

# 验证安装
python -c "import fastapi; print(fastapi.__version__)"
```

---

### Task 1.2: 数据库配置

**Files:**
- Create: `backend/src/core/database.py`
- Create: `backend/src/core/config.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`

**Step 1: 创建配置模块**

```python
# backend/src/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/bid_eval"

    # Security
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60

    # LLM
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"

    # Storage
    upload_dir: str = "./uploads"
    max_upload_size: int = 104857600  # 100MB

    # LightRAG
    lightrag_working_dir: str = "./lightrag_storage"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
```

**Step 2: 创建数据库连接**

```python
# backend/src/core/database.py
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncAttrs
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from src.core.config import get_settings

settings = get_settings()


class Base(AsyncAttrs, DeclarativeBase):
    """异步支持的基类"""
    pass


# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（FastAPI 依赖注入）"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Step 3: 创建 Alembic 配置**

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

import sys
sys.path.insert(0, ".")

from src.core.database import Base
from src.core.config import get_settings

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

# 从 settings 获取数据库 URL
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 4: 测试数据库连接**

```python
# tests/test_database.py
import pytest
from sqlalchemy import text
from src.core.database import engine


@pytest.mark.asyncio
async def test_database_connection():
    """测试数据库连接"""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

---

### Task 1.3: 用户模型与认证

**Files:**
- Create: `backend/src/modules/user/__init__.py`
- Create: `backend/src/modules/user/infrastructure/__init__.py`
- Create: `backend/src/modules/user/infrastructure/models/user.py`
- Create: `backend/src/core/security.py`

**Step 1: 创建用户模型**

```python
# backend/src/modules/user/infrastructure/models/user.py
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    EVALUATOR = "evaluator"
    AGENT = "agent"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
```

**Step 2: 创建安全模块**

```python
# backend/src/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import get_settings
from src.core.database import async_session_factory
from src.modules.user.infrastructure.models.user import User
from sqlalchemy import select

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        return user
```

**Step 3: 创建认证路由**

```python
# backend/src/modules/auth/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.core.api.response import ApiResponse
from src.core.security import verify_password, create_access_token, get_password_hash
from src.core.database import SessionDep
from src.modules.user.infrastructure.models.user import User, UserRole
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(request: LoginRequest, session: SessionDep):
    # 查找用户
    result = await session.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 创建令牌
    access_token = create_access_token(data={"sub": user.username})

    return ApiResponse(data=LoginResponse(
        access_token=access_token,
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value
        )
    ))
```

---

### Task 1.4: 项目模型与 CRUD

**Files:**
- Create: `backend/src/modules/project/__init__.py`
- Create: `backend/src/modules/project/infrastructure/models/project.py`
- Create: `backend/src/modules/project/api/schemas.py`
- Create: `backend/src/modules/project/api/routes.py`

**Step 1: 创建项目模型**

```python
# backend/src/modules/project/infrastructure/models/project.py
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class BidProject(Base):
    __tablename__ = "bid_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(50), unique=True)
    project_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    tender_type: Mapped[str] = mapped_column(String(50))
    budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    publish_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus), default=ProjectStatus.DRAFT
    )
    scoring_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
```

**Step 2: 创建项目 Schema**

```python
# backend/src/modules/project/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from src.modules.project.infrastructure.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    project_name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    tender_type: str
    budget: Optional[Decimal] = Field(None, ge=0)
    deadline: Optional[datetime] = None
    scoring_config: Optional[dict] = None


class ProjectListItem(BaseModel):
    id: int
    project_code: str
    project_name: str
    tender_type: str
    status: ProjectStatus
    budget: Optional[Decimal]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectDetail(ProjectListItem):
    description: Optional[str]
    currency: str = "CNY"
    deadline: Optional[datetime]
    scoring_config: Optional[dict]
    updated_at: datetime
```

**Step 3: 创建项目路由**

```python
# backend/src/modules/project/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.api.response import ApiResponse, PagedResponse, PaginationMeta
from src.core.database import SessionDep, CurrentUser
from src.modules.project.infrastructure.models.project import BidProject, ProjectStatus
from src.modules.project.api.schemas import ProjectCreate, ProjectListItem, ProjectDetail

router = APIRouter(prefix="/projects", tags=["项目管理"])


def generate_project_code() -> str:
    from datetime import datetime
    import random
    date_str = datetime.now().strftime("%Y%m%d")
    rand_str = "".join([str(random.randint(0, 9)) for _ in range(4)])
    return f"PRJ-{date_str}-{rand_str}"


@router.get("", response_model=PagedResponse[ProjectListItem])
async def list_projects(
    session: SessionDep,
    page: int = 1,
    page_size: int = 20,
    status: Optional[ProjectStatus] = None,
    keyword: Optional[str] = None,
):
    """获取项目列表"""
    query = select(BidProject).where(BidProject.is_deleted == False)

    if status:
        query = query.where(BidProject.status == status)
    if keyword:
        query = query.where(BidProject.project_name.ilike(f"%{keyword}%"))

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(BidProject.created_at.desc())
    result = await session.execute(query)
    projects = result.scalars().all()

    return PagedResponse(
        data=[ProjectListItem.model_validate(p) for p in projects],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size
        )
    )


@router.post("", response_model=ApiResponse[ProjectListItem], status_code=201)
async def create_project(
    data: ProjectCreate,
    session: SessionDep,
    current_user: CurrentUser
):
    """创建项目"""
    project = BidProject(
        project_code=generate_project_code(),
        project_name=data.project_name,
        description=data.description,
        tender_type=data.tender_type,
        budget=data.budget,
        deadline=data.deadline,
        scoring_config=data.scoring_config,
        created_by=current_user.id
    )
    session.add(project)
    await session.flush()
    await session.refresh(project)

    return ApiResponse(
        data=ProjectListItem.model_validate(project),
        message="项目创建成功"
    )


@router.get("/{project_id}", response_model=ApiResponse[ProjectDetail])
async def get_project(project_id: int, session: SessionDep):
    """获取项目详情"""
    result = await session.execute(
        select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == False)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return ApiResponse(data=ProjectDetail.model_validate(project))


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, session: SessionDep):
    """删除项目（软删除）"""
    result = await session.execute(
        select(BidProject).where(BidProject.id == project_id, BidProject.is_deleted == False)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
```

---

### Task 1.5: 文档上传与解析

**Files:**
- Create: `backend/src/modules/document/__init__.py`
- Create: `backend/src/modules/document/infrastructure/models/document.py`
- Create: `backend/src/modules/document/api/routes.py`
- Create: `backend/src/modules/document/services/parser.py`

**Step 1: 创建文档模型**

```python
# backend/src/modules/document/infrastructure/models/document.py
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class DocumentType(str, Enum):
    TENDER = "tender"
    BID = "bid"
    TECHNICAL = "technical"
    COMMERCIAL = "commercial"
    OTHER = "other"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"
    INDEXED = "indexed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bid_projects.id", ondelete="SET NULL"))
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"))
    file_name: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_size: Mapped[int] = mapped_column(Integer)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    doc_type: Mapped[DocumentType] = mapped_column(SQLEnum(DocumentType))
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus), default=DocumentStatus.PENDING
    )
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    parse_method: Mapped[Optional[str]] = mapped_column(String(50))
    parse_error: Mapped[Optional[str]] = mapped_column(Text)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
```

**Step 2: 创建文档路由**

```python
# backend/src/modules/document/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import Optional
import hashlib
import os
from datetime import datetime

from src.core.api.response import ApiResponse
from src.core.config import get_settings
from src.core.database import SessionDep, CurrentUser
from src.modules.document.infrastructure.models.document import Document, DocumentType, DocumentStatus

router = APIRouter(prefix="/documents", tags=["文档管理"])
settings = get_settings()


@router.post("/upload", response_model=ApiResponse, status_code=201)
async def upload_document(
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(None),
    supplier_id: Optional[int] = Form(None),
    doc_type: str = Form(...),
):
    """上传文档"""
    # 检查文件大小
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > settings.max_upload_size:
        raise HTTPException(status_code=413, detail="文件过大")

    # 计算文件哈希
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # 保存文件
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, f"{file_hash}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(content)

    # 创建文档记录
    document = Document(
        project_id=project_id,
        supplier_id=supplier_id,
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_hash=file_hash,
        mime_type=file.content_type,
        doc_type=DocumentType(doc_type),
        created_by=current_user.id
    )
    session.add(document)
    await session.flush()
    await session.refresh(document)

    return ApiResponse(
        data={"id": document.id, "file_name": document.file_name, "status": document.status.value},
        message="文档上传成功"
    )
```

---

## Phase 2: RAG 能力（Week 3-4）

### Task 2.1: LightRAG 集成

**Files:**
- Create: `backend/src/modules/retrieval/__init__.py`
- Create: `backend/src/modules/retrieval/services/lightrag_service.py`
- Create: `backend/src/modules/retrieval/api/routes.py`

**Step 1: 创建 LightRAG 服务**

```python
# backend/src/modules/retrieval/services/lightrag_service.py
import os
from typing import Optional, List, Dict, Any
from lightrag import LightRAG, QueryParam
from lightrag.llm import openai_complete_if_cache, openai_embedding

from src.core.config import get_settings

settings = get_settings()


class LightRAGService:
    """LightRAG 检索服务"""

    _instance: Optional["LightRAGService"] = None
    _rag: Optional[LightRAG] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._rag is None:
            os.makedirs(settings.lightrag_working_dir, exist_ok=True)
            self._rag = LightRAG(
                working_dir=settings.lightrag_working_dir,
                llm_model_func=lambda *args, **kwargs: openai_complete_if_cache(
                    settings.openai_model,
                    *args,
                    api_key=settings.openai_api_key,
                    **kwargs
                ),
                embedding_func=lambda texts: openai_embedding(
                    texts,
                    model=settings.embedding_model,
                    api_key=settings.openai_api_key
                )
            )

    async def insert_document(self, content: str, metadata: Optional[Dict] = None) -> None:
        """插入文档到知识库"""
        await self._rag.ainsert(content, metadata=metadata)

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        include_references: bool = True,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """查询知识库"""
        result = await self._rag.aquery(
            query,
            param=QueryParam(
                mode=mode,
                include_references=include_references,
                top_k=top_k,
                enable_rerank=True
            )
        )
        return result

    async def delete_document(self, doc_id: str) -> None:
        """从知识库删除文档"""
        # LightRAG 暂不支持直接删除，需要重建索引
        pass
```

**Step 2: 创建检索路由**

```python
# backend/src/modules/retrieval/api/routes.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.core.api.response import ApiResponse
from src.modules.retrieval.services.lightrag_service import LightRAGService

router = APIRouter(prefix="/retrieval", tags=["检索服务"])


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    mode: str = Field("hybrid", description="查询模式: local/global/hybrid/mix")
    include_references: bool = Field(True)
    top_k: int = Field(10, ge=1, le=50)


class Reference(BaseModel):
    document_id: Optional[int] = None
    document_name: str
    page: int
    text: str
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    references: List[Reference] = []
    entities: List[str] = []
    confidence: float


@router.post("/query", response_model=ApiResponse[QueryResponse])
async def query_knowledge_base(request: QueryRequest):
    """知识库查询"""
    service = LightRAGService()
    result = await service.query(
        query=request.query,
        mode=request.mode,
        include_references=request.include_references,
        top_k=request.top_k
    )

    return ApiResponse(data=QueryResponse(
        answer=result.response if hasattr(result, 'response') else str(result),
        references=[
            Reference(
                document_name=ref.get("doc_name", "unknown"),
                page=ref.get("page", 0),
                text=ref.get("text", ""),
                relevance_score=ref.get("score", 0.8)
            )
            for ref in (result.references if hasattr(result, 'references') else [])
        ],
        entities=result.entities if hasattr(result, 'entities') else [],
        confidence=0.9
    ))
```

---

### Task 2.2: 文档解析管道

**Files:**
- Create: `backend/src/modules/document/services/parser.py`
- Create: `backend/src/modules/document/services/chunker.py`

**Step 1: 创建解析器服务**

```python
# backend/src/modules/document/services/parser.py
import subprocess
import json
import os
from typing import Dict, List, Any
from abc import ABC, abstractmethod


class DocumentParser(ABC):
    """文档解析器基类"""

    @abstractmethod
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """解析文档，返回结构化内容"""
        pass


class MinerUParser(DocumentParser):
    """MinerU PDF 解析器"""

    async def parse(self, file_path: str, output_dir: str = "./output") -> Dict[str, Any]:
        """使用 MinerU 解析 PDF"""
        # 调用 magic-pdf CLI
        result = subprocess.run([
            "magic-pdf",
            "-p", file_path,
            "-o", output_dir,
            "-m", "auto"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"MinerU 解析失败: {result.stderr}")

        # 读取 content_list.json
        filename = os.path.basename(file_path).replace(".pdf", "")
        content_list_path = os.path.join(output_dir, filename, "content_list.json")

        with open(content_list_path, 'r', encoding='utf-8') as f:
            items = json.load(f)

        return {
            "page_count": max(item.get("page_idx", 0) for item in items) + 1 if items else 0,
            "content_items": items,
            "parse_method": "mineru"
        }


class DoclingParser(DocumentParser):
    """Docling 文档解析器"""

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """使用 Docling 解析文档"""
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(file_path)

        # 导出为 markdown
        markdown_content = result.document.export_to_markdown()

        return {
            "page_count": len(result.pages) if hasattr(result, 'pages') else 1,
            "content": markdown_content,
            "parse_method": "docling"
        }


class ParserFactory:
    """解析器工厂"""

    @staticmethod
    def get_parser(file_path: str) -> DocumentParser:
        """根据文件类型选择解析器"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return MinerUParser()
        elif ext in [".docx", ".doc", ".xlsx", ".xls"]:
            return DoclingParser()
        else:
            raise ValueError(f"不支持的文件类型: {ext}")
```

---

## Phase 3: Agent 能力（Week 5-6）

### Task 3.1: LangGraph 工作流

**Files:**
- Create: `backend/src/modules/evaluation/__init__.py`
- Create: `backend/src/modules/evaluation/services/workflow.py`
- Create: `backend/src/modules/evaluation/services/agents.py`

**Step 1: 创建评估工作流**

```python
# backend/src/modules/evaluation/services/workflow.py
from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

from src.modules.retrieval.services.lightrag_service import LightRAGService


class EvaluationState(TypedDict):
    """评估状态"""
    project_id: int
    supplier_id: int
    criteria: List[Dict]
    documents: List[str]

    # 中间结果
    retrieved_context: str
    qualification_result: Dict
    technical_result: Dict
    commercial_result: Dict

    # 最终结果
    eval_items: Annotated[List[Dict], "add"]
    total_score: float
    recommendation: str

    # 人工审核
    needs_review: bool
    review_feedback: str


async def retrieve_context(state: EvaluationState) -> Dict:
    """检索相关上下文"""
    service = LightRAGService()

    # 检索资质信息
    qual_result = await service.query(
        f"供应商{state['supplier_id']}的资质证书有哪些？",
        mode="local"
    )

    # 检索技术方案
    tech_result = await service.query(
        f"供应商{state['supplier_id']}的技术方案是什么？",
        mode="hybrid"
    )

    return {
        "retrieved_context": f"{qual_result}\n\n{tech_result}"
    }


async def evaluate_qualification(state: EvaluationState) -> Dict:
    """评估资格审查"""
    # 使用 LLM 评估资质
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini")
    prompt = f"""
    根据以下上下文，评估供应商的资格是否符合要求。

    评分标准: {state['criteria']}

    上下文: {state['retrieved_context']}

    请返回 JSON 格式的评估结果，包含:
    - passed: bool
    - score: float
    - reasoning: str
    """

    result = await llm.ainvoke([HumanMessage(content=prompt)])
    # 解析结果
    return {"qualification_result": {"passed": True, "score": 100, "reasoning": "符合要求"}}


async def evaluate_technical(state: EvaluationState) -> Dict:
    """评估技术评分"""
    # 类似实现
    return {"technical_result": {"score": 85}}


async def evaluate_commercial(state: EvaluationState) -> Dict:
    """评估商务评分"""
    # 类似实现
    return {"commercial_result": {"score": 90}}


async def calculate_total(state: EvaluationState) -> Dict:
    """计算总分"""
    qual_score = state["qualification_result"].get("score", 0)
    tech_score = state["technical_result"].get("score", 0)
    comm_score = state["commercial_result"].get("score", 0)

    # 加权计算
    total = tech_score * 0.5 + comm_score * 0.3 + qual_score * 0.2

    recommendation = "approved" if total >= 70 else "review" if total >= 50 else "rejected"

    return {
        "total_score": total,
        "recommendation": recommendation,
        "needs_review": total < 80
    }


async def human_review(state: EvaluationState) -> Dict:
    """人工审核节点"""
    if state["needs_review"]:
        feedback = interrupt({
            "action_request": {
                "type": "review",
                "message": f"供应商{state['supplier_id']}评分{state['total_score']}，需要人工审核"
            },
            "config": {
                "allow_respond": True,
                "allow_ignore": True
            }
        })

        if feedback.get("type") == "response":
            return {"review_feedback": feedback.get("content", "")}

    return {}


def create_evaluation_graph():
    """创建评估工作流图"""
    workflow = StateGraph(EvaluationState)

    # 添加节点
    workflow.add_node("retrieve", retrieve_context)
    workflow.add_node("eval_qualification", evaluate_qualification)
    workflow.add_node("eval_technical", evaluate_technical)
    workflow.add_node("eval_commercial", evaluate_commercial)
    workflow.add_node("calculate", calculate_total)
    workflow.add_node("review", human_review)

    # 定义边
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "eval_qualification")
    workflow.add_edge("eval_qualification", "eval_technical")
    workflow.add_edge("eval_technical", "eval_commercial")
    workflow.add_edge("eval_commercial", "calculate")
    workflow.add_edge("calculate", "review")
    workflow.add_edge("review", END)

    # 编译图
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)
```

---

## Phase 4: 集成与部署（Week 7-8）

### Task 4.1: 主应用集成

**Files:**
- Create: `backend/src/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_api.py`

**Step 1: 创建主应用**

```python
# backend/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.auth.api.routes import router as auth_router
from src.modules.project.api.routes import router as project_router
from src.modules.document.api.routes import router as document_router
from src.modules.retrieval.api.routes import router as retrieval_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="辅助评标专家系统",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(project_router, prefix="/api/v1")
    app.include_router(document_router, prefix="/api/v1")
    app.include_router(retrieval_router, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 2: 创建测试配置**

```python
# backend/tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from src.main import create_app
from src.core.database import Base


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(test_engine):
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

---

### Task 4.2: Docker 部署

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

**Step 1: 创建 Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# 复制代码
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

# 创建必要目录
RUN mkdir -p uploads lightrag_storage

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: 创建 docker-compose.yml**

```yaml
# docker-compose.yml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/bid_eval
      - SECRET_KEY=${SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./uploads:/app/uploads
      - ./lightrag_storage:/app/lightrag_storage
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=bid_eval
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## 任务清单汇总

| Phase | Task | 预估工时 | 依赖 |
|-------|------|----------|------|
| **Phase 1** | 1.1 项目初始化 | 0.5天 | - |
| | 1.2 数据库配置 | 1天 | 1.1 |
| | 1.3 用户模型与认证 | 1天 | 1.2 |
| | 1.4 项目模型与CRUD | 1天 | 1.3 |
| | 1.5 文档上传与解析 | 1.5天 | 1.4 |
| **Phase 2** | 2.1 LightRAG集成 | 2天 | 1.5 |
| | 2.2 文档解析管道 | 2天 | 2.1 |
| **Phase 3** | 3.1 LangGraph工作流 | 3天 | 2.2 |
| | 3.2 评估Agent实现 | 3天 | 3.1 |
| **Phase 4** | 4.1 主应用集成 | 1天 | 3.2 |
| | 4.2 Docker部署 | 1天 | 4.1 |

**总计: 18天 ≈ 3.5周**

---

*文档版本：v1.0*
*创建日期：2026-02-21*
