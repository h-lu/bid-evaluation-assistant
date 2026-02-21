# REST API 规范

> 版本：v1.0
> 设计日期：2026-02-21
> 来源参考：FastAPI 官方文档、OpenAPI 3.0 规范

---

## 一、设计原则

### 1.1 RESTful 设计规范

| 原则 | 说明 |
|------|------|
| **资源导向** | URL 表示资源，HTTP 方法表示操作 |
| **版本控制** | URL 路径版本控制 `/api/v1/` |
| **统一响应** | 标准化的响应格式 |
| **错误处理** | 统一的错误码和错误消息 |
| **分页支持** | 列表接口支持分页 |

### 1.2 URL 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| **资源名** | 复数名词 | `/projects`, `/suppliers` |
| **资源ID** | 路径参数 | `/projects/{project_id}` |
| **子资源** | 嵌套路径 | `/projects/{id}/documents` |
| **动作** | POST + 动词 | `POST /evaluations/{id}/start` |
| **查询参数** | snake_case | `?page_size=10&sort_by=created_at` |

### 1.3 HTTP 方法映射

| HTTP 方法 | 用途 | 幂等性 |
|-----------|------|--------|
| **GET** | 获取资源 | 是 |
| **POST** | 创建资源 | 否 |
| **PUT** | 全量更新 | 是 |
| **PATCH** | 部分更新 | 否 |
| **DELETE** | 删除资源 | 是 |

---

## 二、统一响应格式

### 2.1 成功响应

```python
# backend/src/core/api/response.py
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """分页元数据"""
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total: int = Field(..., description="总数量")
    total_pages: int = Field(..., description="总页数")


class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool = Field(True, description="是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="消息")
    meta: Optional[dict] = Field(None, description="元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "示例"},
                "message": "操作成功",
                "meta": None
            }
        }


class PagedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    success: bool = Field(True, description="是否成功")
    data: List[T] = Field(default_factory=list, description="数据列表")
    message: Optional[str] = Field(None, description="消息")
    pagination: PaginationMeta = Field(..., description="分页信息")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [{"id": 1}, {"id": 2}],
                "message": None,
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total": 100,
                    "total_pages": 5
                }
            }
        }
```

### 2.2 错误响应

```python
# backend/src/core/api/errors.py
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 通用错误 (1xxx)
    UNKNOWN_ERROR = "E1000"
    INVALID_REQUEST = "E1001"
    VALIDATION_ERROR = "E1002"
    UNAUTHORIZED = "E1003"
    FORBIDDEN = "E1004"
    NOT_FOUND = "E1005"
    CONFLICT = "E1006"
    RATE_LIMITED = "E1007"

    # 项目相关 (2xxx)
    PROJECT_NOT_FOUND = "E2001"
    PROJECT_ALREADY_EXISTS = "E2002"
    PROJECT_STATUS_INVALID = "E2003"

    # 文档相关 (3xxx)
    DOCUMENT_NOT_FOUND = "E3001"
    DOCUMENT_PARSE_FAILED = "E3002"
    DOCUMENT_UPLOAD_FAILED = "E3003"
    DOCUMENT_TYPE_INVALID = "E3004"

    # 评估相关 (4xxx)
    EVALUATION_NOT_FOUND = "E4001"
    EVALUATION_ALREADY_RUNNING = "E4002"
    EVALUATION_NOT_READY = "E4003"
    SUPPLIER_NOT_IN_PROJECT = "E4004"

    # RAG 相关 (5xxx)
    RETRIEVAL_FAILED = "E5001"
    INDEXING_FAILED = "E5002"
    QUERY_TIMEOUT = "E5003"


class ErrorDetail(BaseModel):
    """错误详情"""
    code: ErrorCode = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    field: Optional[str] = Field(None, description="错误字段")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class ErrorResponse(BaseModel):
    """错误响应格式"""
    success: bool = Field(False, description="是否成功")
    error: ErrorDetail = Field(..., description="错误详情")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "E1002",
                    "message": "参数验证失败",
                    "field": "project_name",
                    "details": {"expected": "string", "received": "null"}
                }
            }
        }
```

### 2.3 HTTP 状态码映射

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| **200** | OK | 成功获取/更新资源 |
| **201** | Created | 成功创建资源 |
| **204** | No Content | 成功删除资源 |
| **400** | Bad Request | 请求参数错误 |
| **401** | Unauthorized | 未认证 |
| **403** | Forbidden | 无权限 |
| **404** | Not Found | 资源不存在 |
| **409** | Conflict | 资源冲突 |
| **422** | Unprocessable Entity | 验证失败 |
| **500** | Internal Server Error | 服务器错误 |

---

## 三、API 模块划分

### 3.1 模块结构

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              API 模块架构                                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   /api/v1/                                                                          │
│   ├── /auth                    # 认证模块                                            │
│   │   ├── POST /login          # 登录                                               │
│   │   ├── POST /logout         # 登出                                               │
│   │   └── POST /refresh        # 刷新令牌                                           │
│   │                                                                                 │
│   ├── /projects                # 项目管理                                            │
│   │   ├── GET /                # 项目列表                                            │
│   │   ├── POST /               # 创建项目                                            │
│   │   ├── GET /{id}            # 项目详情                                            │
│   │   ├── PUT /{id}            # 更新项目                                            │
│   │   ├── DELETE /{id}         # 删除项目                                            │
│   │   └── /{id}/...            # 子资源                                              │
│   │                                                                                 │
│   ├── /documents               # 文档管理                                            │
│   │   ├── GET /                # 文档列表                                            │
│   │   ├── POST /upload         # 上传文档                                            │
│   │   ├── GET /{id}            # 文档详情                                            │
│   │   ├── POST /{id}/parse     # 解析文档                                            │
│   │   └── GET /{id}/chunks     # 文档分块                                            │
│   │                                                                                 │
│   ├── /suppliers               # 供应商管理                                          │
│   │   ├── GET /                # 供应商列表                                          │
│   │   ├── POST /               # 创建供应商                                          │
│   │   ├── GET /{id}            # 供应商详情                                          │
│   │   └── PUT /{id}            # 更新供应商                                          │
│   │                                                                                 │
│   ├── /evaluations             # 评估管理                                            │
│   │   ├── GET /                # 评估列表                                            │
│   │   ├── POST /               # 创建评估                                            │
│   │   ├── GET /{id}            # 评估详情                                            │
│   │   ├── POST /{id}/start     # 开始评估                                            │
│   │   ├── POST /{id}/review    # 人工审核                                            │
│   │   ├── GET /{id}/results    # 评估结果                                            │
│   │   └── GET /{id}/report     # 评估报告                                            │
│   │                                                                                 │
│   ├── /retrieval               # 检索服务                                            │
│   │   ├── POST /query          # 知识库查询                                          │
│   │   └── POST /index          # 索引文档                                            │
│   │                                                                                 │
│   └── /health                  # 健康检查                                            │
│       └── GET /                # 服务状态                                            │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 四、认证模块 API

### 4.1 POST /api/v1/auth/login

**描述**: 用户登录

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

**Pydantic 模型**:
```python
# backend/src/modules/auth/api/schemas.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=3, max_length=100, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserInfo(BaseModel):
    """用户信息"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, description="姓名")
    role: str = Field(..., description="角色")
    is_active: bool = Field(True, description="是否活跃")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间(秒)")
    user: UserInfo = Field(..., description="用户信息")
```

**路由实现**:
```python
# backend/src/modules/auth/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.core.api.response import ApiResponse
from src.modules.auth.api.schemas import LoginRequest, LoginResponse, UserInfo
from src.modules.auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/login",
    response_model=ApiResponse[LoginResponse],
    summary="用户登录",
    description="使用用户名密码登录，返回 JWT 令牌",
    responses={
        401: {"description": "用户名或密码错误"},
        422: {"description": "参数验证失败"}
    }
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends()
) -> ApiResponse[LoginResponse]:
    """用户登录"""
    result = await auth_service.authenticate(request.username, request.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E1003", "message": "用户名或密码错误"}
        )
    return ApiResponse(data=result)
```

---

## 五、项目管理 API

### 5.1 GET /api/v1/projects

**描述**: 获取项目列表（分页）

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码，默认 1 |
| `page_size` | int | 否 | 每页数量，默认 20 |
| `status` | string | 否 | 状态筛选 |
| `keyword` | string | 否 | 关键词搜索 |
| `sort_by` | string | 否 | 排序字段 |
| `sort_order` | string | 否 | 排序方向 asc/desc |

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "project_code": "PRJ-2026-001",
      "project_name": "医疗器械采购项目",
      "tender_type": "公开招标",
      "status": "in_progress",
      "budget": 1000000.00,
      "supplier_count": 5,
      "document_count": 12,
      "created_at": "2026-02-20T10:00:00Z",
      "created_by_name": "张三"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

**Pydantic 模型**:
```python
# backend/src/modules/project/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class ProjectStatus(str, Enum):
    """项目状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectListFilter(BaseModel):
    """项目列表筛选"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    status: Optional[ProjectStatus] = Field(None, description="状态筛选")
    keyword: Optional[str] = Field(None, max_length=100, description="关键词")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序方向")


class ProjectListItem(BaseModel):
    """项目列表项"""
    id: int = Field(..., description="项目ID")
    project_code: str = Field(..., description="项目编号")
    project_name: str = Field(..., description="项目名称")
    tender_type: str = Field(..., description="招标类型")
    status: ProjectStatus = Field(..., description="项目状态")
    budget: Optional[Decimal] = Field(None, description="预算金额")
    supplier_count: int = Field(0, description="供应商数量")
    document_count: int = Field(0, description="文档数量")
    created_at: datetime = Field(..., description="创建时间")
    created_by_name: Optional[str] = Field(None, description="创建人姓名")


class ProjectCreate(BaseModel):
    """创建项目请求"""
    project_name: str = Field(..., min_length=2, max_length=255, description="项目名称")
    description: Optional[str] = Field(None, max_length=2000, description="项目描述")
    tender_type: str = Field(..., description="招标类型")
    budget: Optional[Decimal] = Field(None, ge=0, description="预算金额")
    currency: str = Field("CNY", description="币种")
    publish_date: Optional[datetime] = Field(None, description="发布日期")
    deadline: Optional[datetime] = Field(None, description="截止日期")
    scoring_config: Optional[dict] = Field(None, description="评分配置")


class ProjectDetail(ProjectListItem):
    """项目详情"""
    description: Optional[str] = Field(None, description="项目描述")
    currency: str = Field("CNY", description="币种")
    publish_date: Optional[datetime] = Field(None, description="发布日期")
    deadline: Optional[datetime] = Field(None, description="截止日期")
    open_date: Optional[datetime] = Field(None, description="开标日期")
    scoring_config: Optional[dict] = Field(None, description="评分配置")
    updated_at: datetime = Field(..., description="更新时间")

    # 关联信息
    suppliers: List["SupplierBrief"] = Field(default_factory=list, description="供应商列表")
    documents: List["DocumentBrief"] = Field(default_factory=list, description="文档列表")
    criteria_count: int = Field(0, description="评分标准数量")


class SupplierBrief(BaseModel):
    """供应商简要信息"""
    id: int
    supplier_code: str
    supplier_name: str


class DocumentBrief(BaseModel):
    """文档简要信息"""
    id: int
    file_name: str
    doc_type: str
    status: str
    created_at: datetime
```

### 5.2 POST /api/v1/projects

**描述**: 创建新项目

**请求体**:
```json
{
  "project_name": "医疗器械采购项目",
  "description": "采购医疗影像设备",
  "tender_type": "公开招标",
  "budget": 1000000.00,
  "currency": "CNY",
  "deadline": "2026-03-01T18:00:00Z",
  "scoring_config": {
    "technical_weight": 0.5,
    "commercial_weight": 0.3,
    "qualification_weight": 0.2,
    "passing_score": 60
  }
}
```

**响应**: 201 Created
```json
{
  "success": true,
  "data": {
    "id": 1,
    "project_code": "PRJ-2026-001",
    "project_name": "医疗器械采购项目",
    "status": "draft",
    "created_at": "2026-02-20T10:00:00Z"
  },
  "message": "项目创建成功"
}
```

### 5.3 GET /api/v1/projects/{project_id}

**描述**: 获取项目详情

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project_id` | int | 是 | 项目ID |

**响应**: 200 OK

### 5.4 PUT /api/v1/projects/{project_id}

**描述**: 更新项目信息

### 5.5 DELETE /api/v1/projects/{project_id}

**描述**: 删除项目（软删除）

**响应**: 204 No Content

---

## 六、文档管理 API

### 6.1 POST /api/v1/documents/upload

**描述**: 上传文档

**请求**: multipart/form-data
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 文档文件 |
| `project_id` | int | 否 | 项目ID |
| `supplier_id` | int | 否 | 供应商ID |
| `doc_type` | string | 是 | 文档类型 |

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "file_name": "投标文件-供应商A.pdf",
    "file_size": 10485760,
    "doc_type": "bid",
    "status": "pending",
    "upload_url": "/api/v1/documents/1/download"
  },
  "message": "文档上传成功"
}
```

**Pydantic 模型**:
```python
# backend/src/modules/document/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    """文档类型"""
    TENDER = "tender"
    BID = "bid"
    CONTRACT = "contract"
    QUALIFICATION = "qualification"
    TECHNICAL = "technical"
    COMMERCIAL = "commercial"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """文档状态"""
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"
    INDEXED = "indexed"


class DocumentUpload(BaseModel):
    """文档上传响应"""
    id: int = Field(..., description="文档ID")
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小")
    file_hash: str = Field(..., description="文件哈希")
    doc_type: DocumentType = Field(..., description="文档类型")
    status: DocumentStatus = Field(..., description="文档状态")
    created_at: datetime = Field(..., description="上传时间")


class DocumentDetail(DocumentUpload):
    """文档详情"""
    project_id: Optional[int] = Field(None, description="项目ID")
    supplier_id: Optional[int] = Field(None, description="供应商ID")
    mime_type: str = Field(..., description="MIME类型")
    page_count: Optional[int] = Field(None, description="页数")
    parse_method: Optional[str] = Field(None, description="解析方法")
    parse_error: Optional[str] = Field(None, description="解析错误")
    parsed_at: Optional[datetime] = Field(None, description="解析时间")
    is_indexed: bool = Field(False, description="是否已索引")
    chunk_count: int = Field(0, description="分块数量")
    metadata: Optional[dict] = Field(None, description="元数据")


class ChunkInfo(BaseModel):
    """分块信息"""
    id: int = Field(..., description="分块ID")
    chunk_index: int = Field(..., description="分块序号")
    content: str = Field(..., description="分块内容")
    token_count: int = Field(..., description="Token数量")
    page: int = Field(..., description="页码")
    section_title: Optional[str] = Field(None, description="章节标题")
```

### 6.2 POST /api/v1/documents/{document_id}/parse

**描述**: 解析文档

**请求体**:
```json
{
  "parse_method": "auto",
  "options": {
    "extract_images": true,
    "extract_tables": true
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "document_id": 1,
    "status": "parsing",
    "task_id": "task_abc123"
  },
  "message": "解析任务已启动"
}
```

### 6.3 GET /api/v1/documents/{document_id}/chunks

**描述**: 获取文档分块列表

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页数量 |
| `content_type` | string | 否 | 内容类型筛选 |

---

## 七、评估管理 API

### 7.1 POST /api/v1/evaluations

**描述**: 创建评估会话

**请求体**:
```json
{
  "project_id": 1,
  "supplier_ids": [1, 2, 3],
  "config": {
    "auto_approve_threshold": 0.9,
    "require_human_review": true
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "session_code": "EVAL-2026-001",
    "project_id": 1,
    "status": "pending",
    "total_suppliers": 3,
    "created_at": "2026-02-20T10:00:00Z"
  },
  "message": "评估会话创建成功"
}
```

**Pydantic 模型**:
```python
# backend/src/modules/evaluation/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
from enum import Enum


class SessionStatus(str, Enum):
    """评估会话状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    HUMAN_REVIEW = "human_review"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationCreate(BaseModel):
    """创建评估请求"""
    project_id: int = Field(..., description="项目ID")
    supplier_ids: List[int] = Field(..., min_length=1, description="供应商ID列表")
    config: Optional[dict] = Field(None, description="评估配置")


class EvaluationSession(BaseModel):
    """评估会话"""
    id: int = Field(..., description="会话ID")
    session_code: str = Field(..., description="会话编号")
    project_id: int = Field(..., description="项目ID")
    project_name: str = Field(..., description="项目名称")
    status: SessionStatus = Field(..., description="会话状态")
    total_suppliers: int = Field(..., description="供应商总数")
    completed_suppliers: int = Field(0, description="已完成数量")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    created_at: datetime = Field(..., description="创建时间")


class EvalResultSummary(BaseModel):
    """评估结果摘要"""
    id: int = Field(..., description="结果ID")
    supplier_id: int = Field(..., description="供应商ID")
    supplier_name: str = Field(..., description="供应商名称")
    is_completed: bool = Field(False, description="是否完成")
    qualification_passed: Optional[bool] = Field(None, description="资格审查通过")
    compliance_passed: Optional[bool] = Field(None, description="符合性审查通过")
    technical_score: Optional[Decimal] = Field(None, description="技术分")
    commercial_score: Optional[Decimal] = Field(None, description="商务分")
    total_score: Optional[Decimal] = Field(None, description="总分")
    recommendation: Optional[str] = Field(None, description="推荐结果")
    needs_review: bool = Field(False, description="需要人工审核")


class EvalItemDetail(BaseModel):
    """评估项详情（点对点格式）"""
    id: int = Field(..., description="评估项ID")
    criteria_code: str = Field(..., description="评分项编号")
    criteria_name: str = Field(..., description="评分项名称")
    criteria_type: str = Field(..., description="评分项类型")

    # 点对点应答
    requirement: str = Field(..., description="招标要求")
    requirement_source: str = Field(..., description="要求来源")
    response: str = Field(..., description="投标响应")
    response_source: str = Field(..., description="响应来源")

    # 符合度
    compliance_status: str = Field(..., description="符合度(full/partial/none)")

    # 评分
    score: Decimal = Field(..., description="得分")
    max_score: Decimal = Field(..., description="满分")
    reasoning: str = Field(..., description="评分理由")

    # 证据
    evidence: List[dict] = Field(default_factory=list, description="证据列表")
    confidence: float = Field(..., description="置信度")

    # 人工审核
    needs_review: bool = Field(False, description="需要人工审核")
    reviewed: bool = Field(False, description="是否已审核")
    review_comment: Optional[str] = Field(None, description="审核意见")
    manual_score: Optional[Decimal] = Field(None, description="人工修正分数")


class EvalResultDetail(EvalResultSummary):
    """评估结果详情"""
    overall_assessment: Optional[str] = Field(None, description="综合评价")
    key_findings: List[str] = Field(default_factory=list, description="关键发现")
    risk_alerts: List[str] = Field(default_factory=list, description="风险提示")
    items: List[EvalItemDetail] = Field(default_factory=list, description="评估项列表")


class ReviewRequest(BaseModel):
    """人工审核请求"""
    item_ids: List[int] = Field(..., description="评估项ID列表")
    action: str = Field(..., description="操作(approve/reject/modify)")
    comment: Optional[str] = Field(None, description="审核意见")
    modifications: Optional[Dict[int, Decimal]] = Field(None, description="分数修改")


class ReviewResponse(BaseModel):
    """人工审核响应"""
    reviewed_count: int = Field(..., description="已审核数量")
    updated_results: List[EvalResultSummary] = Field(..., description="更新结果")
```

### 7.2 POST /api/v1/evaluations/{evaluation_id}/start

**描述**: 启动评估

**响应**:
```json
{
  "success": true,
  "data": {
    "evaluation_id": 1,
    "status": "in_progress",
    "task_id": "task_xyz789"
  },
  "message": "评估已启动"
}
```

### 7.3 GET /api/v1/evaluations/{evaluation_id}/results

**描述**: 获取评估结果列表

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `supplier_id` | int | 否 | 供应商ID筛选 |
| `needs_review` | bool | 否 | 仅显示需要审核的 |

### 7.4 GET /api/v1/evaluations/{evaluation_id}/results/{result_id}

**描述**: 获取单个供应商评估结果详情（包含点对点应答）

### 7.5 POST /api/v1/evaluations/{evaluation_id}/review

**描述**: 提交人工审核

**请求体**:
```json
{
  "item_ids": [1, 2, 3],
  "action": "approve",
  "comment": "经核实，评分合理"
}
```

### 7.6 GET /api/v1/evaluations/{evaluation_id}/report

**描述**: 获取评估报告（点对点应答格式）

**响应**:
```json
{
  "success": true,
  "data": {
    "session_id": 1,
    "project_name": "医疗器械采购项目",
    "evaluation_date": "2026-02-20",
    "results": [
      {
        "supplier_name": "供应商A",
        "total_score": 92.5,
        "recommendation": "approved",
        "qualification_items": [...],
        "technical_items": [...],
        "commercial_items": [...]
      }
    ]
  }
}
```

---

## 八、检索服务 API

### 8.1 POST /api/v1/retrieval/query

**描述**: 知识库查询

**请求体**:
```json
{
  "query": "供应商A的注册资金是多少？",
  "project_id": 1,
  "options": {
    "mode": "hybrid",
    "top_k": 10,
    "include_references": true,
    "doc_types": ["bid", "tender"]
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "answer": "供应商A的注册资金为5000万元人民币。",
    "context": "根据投标文件第12页显示，供应商A的注册资本为...",
    "references": [
      {
        "document_id": 1,
        "document_name": "投标文件-供应商A.pdf",
        "page": 12,
        "bbox": [50, 100, 400, 200],
        "text": "注册资本：5000万元人民币",
        "relevance_score": 0.95
      }
    ],
    "entities": ["供应商A", "注册资金"],
    "confidence": 0.92
  }
}
```

**Pydantic 模型**:
```python
# backend/src/modules/retrieval/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class QueryMode(str, Enum):
    """查询模式"""
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    MIX = "mix"
    NAIVE = "naive"


class QueryRequest(BaseModel):
    """查询请求"""
    query: str = Field(..., min_length=1, max_length=1000, description="查询内容")
    project_id: Optional[int] = Field(None, description="项目ID")
    supplier_id: Optional[int] = Field(None, description="供应商ID")
    options: Optional[Dict[str, Any]] = Field(None, description="查询选项")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "供应商A的注册资金是多少？",
                "project_id": 1,
                "options": {
                    "mode": "hybrid",
                    "top_k": 10,
                    "include_references": True
                }
            }
        }


class Reference(BaseModel):
    """引用来源"""
    document_id: int = Field(..., description="文档ID")
    document_name: str = Field(..., description="文档名称")
    page: int = Field(..., description="页码")
    bbox: Optional[List[int]] = Field(None, description="边界框[x1,y1,x2,y2]")
    text: str = Field(..., description="引用文本")
    relevance_score: float = Field(..., description="相关度分数")


class QueryResponse(BaseModel):
    """查询响应"""
    answer: str = Field(..., description="生成的回答")
    context: Optional[str] = Field(None, description="检索上下文")
    references: List[Reference] = Field(default_factory=list, description="引用来源")
    entities: List[str] = Field(default_factory=list, description="识别的实体")
    relations: List[Dict[str, Any]] = Field(default_factory=list, description="实体关系")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    query_mode: QueryMode = Field(..., description="使用的查询模式")
```

### 8.2 POST /api/v1/retrieval/index

**描述**: 索引文档到知识库

**请求体**:
```json
{
  "document_ids": [1, 2, 3],
  "options": {
    "reindex": false
  }
}
```

---

## 九、健康检查 API

### 9.1 GET /api/v1/health

**描述**: 服务健康检查

**响应**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-20T10:00:00Z",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "lightrag": "healthy",
    "llm": "healthy"
  }
}
```

---

## 十、路由注册

### 10.1 主应用配置

```python
# backend/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.api.response import ApiResponse
from src.modules.auth.api.routes import router as auth_router
from src.modules.project.api.routes import router as project_router
from src.modules.document.api.routes import router as document_router
from src.modules.supplier.api.routes import router as supplier_router
from src.modules.evaluation.api.routes import router as evaluation_router
from src.modules.retrieval.api.routes import router as retrieval_router
from src.modules.health.api.routes import router as health_router


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="辅助评标专家系统 API",
        description="基于 Agentic RAG 的医疗器械招投标智能助手",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境需要限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(project_router, prefix="/api/v1")
    app.include_router(document_router, prefix="/api/v1")
    app.include_router(supplier_router, prefix="/api/v1")
    app.include_router(evaluation_router, prefix="/api/v1")
    app.include_router(retrieval_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        return ApiResponse(
            success=False,
            error={"code": "E1000", "message": str(exc)}
        )

    return app


app = create_app()
```

### 10.2 依赖注入

```python
# backend/src/core/dependencies.py
from typing import AsyncGenerator, Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory
from src.core.security import get_current_user
from src.modules.user.infrastructure.models import User


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# 类型别名，简化依赖注入
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
```

---

## 十一、API 端点汇总

| 模块 | 端点 | 方法 | 说明 |
|------|------|------|------|
| **认证** | `/api/v1/auth/login` | POST | 用户登录 |
| | `/api/v1/auth/logout` | POST | 用户登出 |
| | `/api/v1/auth/refresh` | POST | 刷新令牌 |
| **项目** | `/api/v1/projects` | GET | 项目列表 |
| | `/api/v1/projects` | POST | 创建项目 |
| | `/api/v1/projects/{id}` | GET | 项目详情 |
| | `/api/v1/projects/{id}` | PUT | 更新项目 |
| | `/api/v1/projects/{id}` | DELETE | 删除项目 |
| | `/api/v1/projects/{id}/criteria` | GET | 评分标准 |
| | `/api/v1/projects/{id}/criteria` | POST | 添加评分标准 |
| **文档** | `/api/v1/documents` | GET | 文档列表 |
| | `/api/v1/documents/upload` | POST | 上传文档 |
| | `/api/v1/documents/{id}` | GET | 文档详情 |
| | `/api/v1/documents/{id}` | DELETE | 删除文档 |
| | `/api/v1/documents/{id}/parse` | POST | 解析文档 |
| | `/api/v1/documents/{id}/chunks` | GET | 文档分块 |
| | `/api/v1/documents/{id}/download` | GET | 下载文档 |
| **供应商** | `/api/v1/suppliers` | GET | 供应商列表 |
| | `/api/v1/suppliers` | POST | 创建供应商 |
| | `/api/v1/suppliers/{id}` | GET | 供应商详情 |
| | `/api/v1/suppliers/{id}` | PUT | 更新供应商 |
| **评估** | `/api/v1/evaluations` | GET | 评估列表 |
| | `/api/v1/evaluations` | POST | 创建评估 |
| | `/api/v1/evaluations/{id}` | GET | 评估详情 |
| | `/api/v1/evaluations/{id}/start` | POST | 启动评估 |
| | `/api/v1/evaluations/{id}/results` | GET | 评估结果 |
| | `/api/v1/evaluations/{id}/results/{rid}` | GET | 结果详情 |
| | `/api/v1/evaluations/{id}/review` | POST | 人工审核 |
| | `/api/v1/evaluations/{id}/report` | GET | 评估报告 |
| **检索** | `/api/v1/retrieval/query` | POST | 知识库查询 |
| | `/api/v1/retrieval/index` | POST | 索引文档 |
| **健康** | `/api/v1/health` | GET | 健康检查 |

---

*文档版本：v1.0*
*创建日期：2026-02-21*
*参考来源：FastAPI 官方文档、OpenAPI 3.0 规范*
