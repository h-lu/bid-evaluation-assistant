# 数据库 Schema 设计

> 版本：v1.0
> 设计日期：2026-02-21
> 来源参考：SQLAlchemy 2.0 官方文档、FastAPI 数据库最佳实践

---

## 一、设计原则

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **异步优先** | 使用 SQLAlchemy 2.0 AsyncSession，支持高并发 |
| **类型安全** | 使用 `Mapped[type]` 类型注解，IDE 友好 |
| **审计追踪** | 所有核心表包含 `created_at`、`updated_at`、`created_by` |
| **软删除** | 核心业务表使用 `is_deleted` 软删除标记 |
| **引用完整性** | 使用外键约束确保数据一致性 |

### 1.2 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| **表名** | snake_case 复数 | `bid_projects`, `suppliers` |
| **字段名** | snake_case | `created_at`, `supplier_name` |
| **主键** | `id` | `id BIGSERIAL PRIMARY KEY` |
| **外键** | `{table}_id` | `supplier_id`, `project_id` |
| **索引** | `idx_{table}_{columns}` | `idx_documents_project_id` |

---

## 二、数据库架构概览

### 2.1 ER 图

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              数据库架构                                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   ┌───────────────┐       ┌───────────────┐       ┌───────────────┐               │
│   │  bid_projects │       │   suppliers   │       │     users     │               │
│   │  (招标项目)    │       │   (供应商)    │       │    (用户)     │               │
│   └───────┬───────┘       └───────┬───────┘       └───────┬───────┘               │
│           │                       │                       │                        │
│           │                       │                       │                        │
│           ▼                       ▼                       │                        │
│   ┌───────────────────────────────────────────┐           │                        │
│   │                documents                   │           │                        │
│   │              (文档表)                      │◄──────────┤ created_by             │
│   └───────────────────┬───────────────────────┘           │                        │
│                       │                                   │                        │
│           ┌───────────┼───────────┐                       │                        │
│           ▼           ▼           ▼                       │                        │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐               │                        │
│   │doc_chunks │ │  images   │ │  tables   │               │                        │
│   │ (分块表)   │ │  (图片)   │ │  (表格)   │               │                        │
│   └───────────┘ └───────────┘ └───────────┘               │                        │
│                                                           │                        │
│   ┌───────────────────────────────────────────┐           │                        │
│   │             evaluation_sessions            │◄──────────┤                        │
│   │             (评估会话)                     │           │                        │
│   └───────────────────┬───────────────────────┘           │                        │
│                       │                                   │                        │
│           ┌───────────┼───────────┐                       │                        │
│           ▼           ▼           ▼                       │                        │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐               │                        │
│   │eval_items │ │eval_results│ │ citations │               │                        │
│   │(评估项)    │ │(评估结果)  │ │ (引用)    │               │                        │
│   └───────────┘ └───────────┘ └───────────┘               │                        │
│                                                           │                        │
│   ┌───────────────┐                                       │                        │
│   │  audit_logs   │◄──────────────────────────────────────┘                        │
│   │  (审计日志)   │                                                                │
│   └───────────────┘                                                                │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 表清单

| 模块 | 表名 | 说明 | 预估数据量 |
|------|------|------|------------|
| **项目管理** | `bid_projects` | 招标项目 | 1k-10k/年 |
| **供应商** | `suppliers` | 供应商信息 | 10k-100k |
| **文档管理** | `documents` | 文档元数据 | 100k-1M |
| | `doc_chunks` | 文档分块 | 1M-10M |
| **评估** | `evaluation_sessions` | 评估会话 | 10k-100k |
| | `eval_criteria` | 评分标准 | 10k-100k |
| | `eval_items` | 点对点评估项 | 100k-1M |
| | `eval_results` | 评估结果 | 10k-100k |
| **溯源** | `citations` | 引用记录 | 1M-10M |
| **用户** | `users` | 用户信息 | 1k-10k |
| **审计** | `audit_logs` | 审计日志 | 10M+ |

---

## 三、核心表定义

### 3.1 招标项目表 (bid_projects)

```python
# backend/src/modules/project/infrastructure/models/project.py
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
import enum
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Numeric, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class ProjectStatus(str, enum.Enum):
    """项目状态"""
    DRAFT = "draft"              # 草稿
    PUBLISHED = "published"      # 已发布
    IN_PROGRESS = "in_progress"  # 评标中
    COMPLETED = "completed"      # 已完成
    ARCHIVED = "archived"        # 已归档


class BidProject(Base):
    """招标项目表"""
    __tablename__ = "bid_projects"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 基本信息
    project_code: Mapped[str] = mapped_column(String(50), unique=True, comment="项目编号")
    project_name: Mapped[str] = mapped_column(String(255), comment="项目名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="项目描述")

    # 招标信息
    tender_type: Mapped[str] = mapped_column(String(50), comment="招标类型")
    budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), comment="预算金额")
    currency: Mapped[str] = mapped_column(String(10), default="CNY", comment="币种")

    # 时间信息
    publish_date: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="发布日期")
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="截止日期")
    open_date: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="开标日期")

    # 状态
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.DRAFT,
        comment="项目状态"
    )

    # 评分配置 (JSONB 存储评分标准)
    scoring_config: Mapped[Optional[dict]] = mapped_column(JSONB, comment="评分配置")
    # 示例:
    # {
    #   "technical_weight": 0.5,
    #   "commercial_weight": 0.3,
    #   "qualification_weight": 0.2,
    #   "passing_score": 60
    # }

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), comment="创建人")

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否删除")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="删除时间")

    # 关系
    documents: Mapped[List["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    evaluation_sessions: Mapped[List["EvaluationSession"]] = relationship(back_populates="project")
    criteria: Mapped[List["EvalCriteria"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"BidProject(id={self.id}, code={self.project_code}, name={self.project_name})"
```

**索引设计：**

```sql
-- 项目编号唯一索引
CREATE UNIQUE INDEX idx_bid_projects_code ON bid_projects(project_code) WHERE is_deleted = FALSE;

-- 状态索引（常用于筛选）
CREATE INDEX idx_bid_projects_status ON bid_projects(status) WHERE is_deleted = FALSE;

-- 创建时间索引（用于排序）
CREATE INDEX idx_bid_projects_created_at ON bid_projects(created_at DESC);

-- 创建人索引
CREATE INDEX idx_bid_projects_created_by ON bid_projects(created_by);
```

### 3.2 供应商表 (suppliers)

```python
# backend/src/modules/supplier/infrastructure/models/supplier.py
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, Text, DateTime, Boolean, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class Supplier(Base):
    """供应商表"""
    __tablename__ = "suppliers"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 基本信息
    supplier_code: Mapped[str] = mapped_column(String(50), unique=True, comment="供应商编号")
    supplier_name: Mapped[str] = mapped_column(String(255), index=True, comment="供应商名称")
    unified_social_credit_code: Mapped[Optional[str]] = mapped_column(
        String(18), unique=True, comment="统一社会信用代码"
    )

    # 注册信息
    registered_capital: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), comment="注册资本")
    establishment_date: Mapped[Optional[date]] = mapped_column(Date, comment="成立日期")
    legal_representative: Mapped[Optional[str]] = mapped_column(String(100), comment="法定代表人")

    # 联系信息
    address: Mapped[Optional[str]] = mapped_column(String(500), comment="地址")
    contact_person: Mapped[Optional[str]] = mapped_column(String(100), comment="联系人")
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), comment="联系电话")
    email: Mapped[Optional[str]] = mapped_column(String(255), comment="邮箱")

    # 资质信息 (JSONB 存储资质列表)
    qualifications: Mapped[Optional[dict]] = mapped_column(JSONB, comment="资质信息")
    # 示例:
    # {
    #   "iso9001": {"valid": True, "expiry": "2027-01-01"},
    #   "iso14001": {"valid": True, "expiry": "2027-01-01"},
    #   "medical_device_license": {"valid": True, "number": "..."}
    # }

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否活跃")
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否黑名单")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # 关系
    documents: Mapped[List["Document"]] = relationship(back_populates="supplier")
    evaluation_results: Mapped[List["EvalResult"]] = relationship(back_populates="supplier")

    def __repr__(self) -> str:
        return f"Supplier(id={self.id}, name={self.supplier_name})"
```

**索引设计：**

```sql
-- 供应商名称模糊搜索
CREATE INDEX idx_suppliers_name ON suppliers USING gin(to_tsvector('simple', supplier_name));

-- 统一社会信用代码唯一索引
CREATE UNIQUE INDEX idx_suppliers_credit_code ON suppliers(unified_social_credit_code)
WHERE unified_social_credit_code IS NOT NULL AND is_deleted = FALSE;

-- 活跃状态索引
CREATE INDEX idx_suppliers_active ON suppliers(is_active) WHERE is_deleted = FALSE;
```

### 3.3 文档表 (documents)

```python
# backend/src/modules/document/infrastructure/models/document.py
from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class DocumentType(str, Enum):
    """文档类型"""
    TENDER = "tender"              # 招标文件
    BID = "bid"                    # 投标文件
    CONTRACT = "contract"          # 合同
    QUALIFICATION = "qualification"  # 资质文件
    TECHNICAL = "technical"        # 技术文档
    COMMERCIAL = "commercial"      # 商务文档
    OTHER = "other"                # 其他


class DocumentStatus(str, Enum):
    """文档状态"""
    PENDING = "pending"            # 待处理
    PARSING = "parsing"            # 解析中
    PARSED = "parsed"              # 已解析
    FAILED = "failed"              # 解析失败
    INDEXED = "indexed"            # 已索引


class Document(Base):
    """文档表"""
    __tablename__ = "documents"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bid_projects.id", ondelete="SET NULL"), comment="项目ID"
    )
    supplier_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), comment="供应商ID"
    )

    # 文件信息
    file_name: Mapped[str] = mapped_column(String(500), comment="文件名")
    file_path: Mapped[str] = mapped_column(String(1000), comment="存储路径")
    file_size: Mapped[int] = mapped_column(Integer, comment="文件大小(bytes)")
    file_hash: Mapped[str] = mapped_column(String(64), index=True, comment="文件SHA256")
    mime_type: Mapped[str] = mapped_column(String(100), comment="MIME类型")

    # 文档信息
    doc_type: Mapped[DocumentType] = mapped_column(SQLEnum(DocumentType), comment="文档类型")
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, comment="文档状态"
    )

    # 解析信息
    page_count: Mapped[Optional[int]] = mapped_column(Integer, comment="页数")
    parse_method: Mapped[Optional[str]] = mapped_column(String(50), comment="解析方法(mineru/docling)")
    parse_error: Mapped[Optional[str]] = mapped_column(Text, comment="解析错误信息")
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="解析完成时间")

    # LightRAG 索引信息
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已索引")
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="索引时间")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="分块数量")

    # 元数据 (JSONB 存储扩展信息)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, comment="文档元数据")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # 关系
    project: Mapped[Optional["BidProject"]] = relationship(back_populates="documents")
    supplier: Mapped[Optional["Supplier"]] = relationship(back_populates="documents")
    chunks: Mapped[List["DocChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Document(id={self.id}, name={self.file_name}, type={self.doc_type})"
```

### 3.4 文档分块表 (doc_chunks)

```python
# backend/src/modules/document/infrastructure/models/doc_chunk.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class DocChunk(Base):
    """文档分块表"""
    __tablename__ = "doc_chunks"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, comment="文档ID"
    )

    # 分块信息
    chunk_index: Mapped[int] = mapped_column(Integer, comment="分块序号")
    content: Mapped[str] = mapped_column(Text, comment="分块内容")
    token_count: Mapped[int] = mapped_column(Integer, comment="Token数量")

    # 位置信息 (用于溯源)
    positions: Mapped[dict] = mapped_column(JSONB, comment="位置信息")
    # 示例:
    # [
    #   {"page": 5, "bbox": [50, 100, 400, 200], "start_offset": 0, "end_offset": 100},
    #   {"page": 6, "bbox": [50, 100, 400, 200], "start_offset": 100, "end_offset": 200}
    # ]

    # 上下文信息
    section_title: Mapped[Optional[str]] = mapped_column(String(500), comment="所属章节标题")
    section_path: Mapped[Optional[str]] = mapped_column(String(1000), comment="章节路径(如: 1.2.3)")

    # 内容类型
    content_type: Mapped[str] = mapped_column(String(50), default="text", comment="内容类型")

    # LightRAG 向量ID（关联到 ChromaDB）
    vector_id: Mapped[Optional[str]] = mapped_column(String(100), comment="向量ID")

    # 元数据
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, comment="扩展元数据")

    # 关系
    document: Mapped["Document"] = relationship(back_populates="chunks")

    def __repr__(self) -> str:
        return f"DocChunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index})"
```

### 3.5 评估会话表 (evaluation_sessions)

```python
# backend/src/modules/evaluation/infrastructure/models/evaluation_session.py
from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class SessionStatus(str, Enum):
    """评估会话状态"""
    PENDING = "pending"          # 待评估
    IN_PROGRESS = "in_progress"  # 评估中
    HUMAN_REVIEW = "human_review"  # 人工审核
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


class EvaluationSession(Base):
    """评估会话表"""
    __tablename__ = "evaluation_sessions"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联
    project_id: Mapped[int] = mapped_column(
        ForeignKey("bid_projects.id"), index=True, comment="项目ID"
    )

    # 会话信息
    session_code: Mapped[str] = mapped_column(String(50), unique=True, comment="会话编号")
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus), default=SessionStatus.PENDING, comment="会话状态"
    )

    # LangGraph 状态 (存储工作流状态)
    graph_state: Mapped[Optional[dict]] = mapped_column(JSONB, comment="LangGraph 工作流状态")
    checkpoint_id: Mapped[Optional[str]] = mapped_column(String(100), comment="LangGraph checkpoint ID")

    # 统计信息
    total_suppliers: Mapped[int] = mapped_column(Integer, default=0, comment="供应商数量")
    completed_suppliers: Mapped[int] = mapped_column(Integer, default=0, comment="已评估数量")

    # 审计字段
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="完成时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # 关系
    project: Mapped["BidProject"] = relationship(back_populates="evaluation_sessions")
    results: Mapped[List["EvalResult"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"EvaluationSession(id={self.id}, code={self.session_code})"
```

### 3.6 评分标准表 (eval_criteria)

```python
# backend/src/modules/evaluation/infrastructure/models/eval_criteria.py
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class CriteriaType(str, Enum):
    """评分项类型"""
    QUALIFICATION = "qualification"  # 资格审查
    COMPLIANCE = "compliance"        # 符合性审查
    TECHNICAL = "technical"          # 技术评分
    COMMERCIAL = "commercial"        # 商务评分
    RISK = "risk"                    # 风险因素


class EvalCriteria(Base):
    """评分标准表"""
    __tablename__ = "eval_criteria"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联
    project_id: Mapped[int] = mapped_column(
        ForeignKey("bid_projects.id", ondelete="CASCADE"), index=True, comment="项目ID"
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("eval_criteria.id", ondelete="SET NULL"), comment="父级ID(用于层级结构)"
    )

    # 评分项信息
    criteria_code: Mapped[str] = mapped_column(String(50), comment="评分项编号")
    criteria_name: Mapped[str] = mapped_column(String(500), comment="评分项名称")
    criteria_type: Mapped[CriteriaType] = mapped_column(SQLEnum(CriteriaType), comment="评分项类型")

    # 评分规则
    max_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), comment="满分")
    is_pass_fail: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否通过/不通过")
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否必填")

    # 要求描述
    requirement: Mapped[str] = mapped_column(Text, comment="招标要求")
    requirement_source: Mapped[Optional[str]] = mapped_column(
        String(500), comment="要求来源(如: 招标文件第5页)"
    )

    # 评分方法描述
    scoring_method: Mapped[Optional[str]] = mapped_column(Text, comment="评分方法")

    # 排序
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关系
    project: Mapped["BidProject"] = relationship(back_populates="criteria")
    parent: Mapped[Optional["EvalCriteria"]] = relationship(
        back_populates="children", remote_side=[id]
    )
    children: Mapped[List["EvalCriteria"]] = relationship(back_populates="parent")
    eval_items: Mapped[List["EvalItem"]] = relationship(back_populates="criteria")

    def __repr__(self) -> str:
        return f"EvalCriteria(id={self.id}, code={self.criteria_code}, name={self.criteria_name})"
```

### 3.7 点对点评估项表 (eval_items)

```python
# backend/src/modules/evaluation/infrastructure/models/eval_item.py
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class ComplianceStatus(str, Enum):
    """符合度状态"""
    FULL = "full"        # 完全符合
    PARTIAL = "partial"  # 部分符合
    NONE = "none"        # 不符合


class EvalItem(Base):
    """点对点评估项表（核心输出）"""
    __tablename__ = "eval_items"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联
    result_id: Mapped[int] = mapped_column(
        ForeignKey("eval_results.id", ondelete="CASCADE"), index=True, comment="评估结果ID"
    )
    criteria_id: Mapped[int] = mapped_column(
        ForeignKey("eval_criteria.id"), index=True, comment="评分标准ID"
    )

    # 招标要求
    requirement: Mapped[str] = mapped_column(Text, comment="招标要求")
    requirement_source: Mapped[str] = mapped_column(String(500), comment="要求来源(招标文件第X页)")

    # 投标响应
    response: Mapped[str] = mapped_column(Text, comment="投标响应")
    response_source: Mapped[str] = mapped_column(String(500), comment="响应来源(投标文件第X页)")

    # 符合度
    compliance_status: Mapped[ComplianceStatus] = mapped_column(
        SQLEnum(ComplianceStatus), comment="符合度"
    )

    # 评分
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), comment="得分")
    max_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), comment="满分")

    # 评分理由
    reasoning: Mapped[str] = mapped_column(Text, comment="评分理由")

    # 证据
    evidence: Mapped[dict] = mapped_column(JSONB, comment="证据列表")
    # 示例:
    # [
    #   {"text": "注册资本5000万元", "source": "投标文件第12页", "bbox": [50, 100, 400, 200]},
    #   {"text": "营业执照有效至2030年", "source": "投标文件第10页"}
    # ]

    # 置信度
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=0.8, comment="AI 置信度")

    # 人工审核
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, comment="需要人工审核")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="审核时间")
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), comment="审核人")
    review_comment: Mapped[Optional[str]] = mapped_column(Text, comment="审核意见")
    manual_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="人工修正分数")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关系
    result: Mapped["EvalResult"] = relationship(back_populates="items")
    criteria: Mapped["EvalCriteria"] = relationship(back_populates="eval_items")
    citations: Mapped[List["Citation"]] = relationship(back_populates="eval_item")

    def __repr__(self) -> str:
        return f"EvalItem(id={self.id}, criteria_id={self.criteria_id}, score={self.score})"
```

### 3.8 评估结果表 (eval_results)

```python
# backend/src/modules/evaluation/infrastructure/models/eval_result.py
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum
from sqlalchemy import String, Text, DateTime, Boolean, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class Recommendation(str, Enum):
    """推荐结果"""
    APPROVED = "approved"    # 推荐中标
    REVIEW = "review"        # 需要审查
    REJECTED = "rejected"    # 不推荐


class EvalResult(Base):
    """评估结果表"""
    __tablename__ = "eval_results"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联
    session_id: Mapped[int] = mapped_column(
        ForeignKey("evaluation_sessions.id", ondelete="CASCADE"), index=True, comment="评估会话ID"
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"), index=True, comment="供应商ID"
    )

    # 状态
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否完成")

    # 各维度分数
    qualification_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="资格审查分")
    qualification_passed: Mapped[Optional[bool]] = mapped_column(Boolean, comment="资格审查是否通过")

    compliance_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="符合性审查分")
    compliance_passed: Mapped[Optional[bool]] = mapped_column(Boolean, comment="符合性审查是否通过")

    technical_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="技术分")
    technical_max: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100, comment="技术满分")

    commercial_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="商务分")
    commercial_max: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100, comment="商务满分")

    risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="风险分")

    # 总分
    total_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="总分(加权后)")

    # 推荐
    recommendation: Mapped[Optional[Recommendation]] = mapped_column(
        SQLEnum(Recommendation), comment="推荐结果"
    )

    # 综合评价
    overall_assessment: Mapped[Optional[str]] = mapped_column(Text, comment="综合评价")
    key_findings: Mapped[Optional[dict]] = mapped_column(JSONB, comment="关键发现")
    risk_alerts: Mapped[Optional[dict]] = mapped_column(JSONB, comment="风险提示")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="完成时间")

    # 关系
    session: Mapped["EvaluationSession"] = relationship(back_populates="results")
    supplier: Mapped["Supplier"] = relationship(back_populates="evaluation_results")
    items: Mapped[List["EvalItem"]] = relationship(back_populates="result", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"EvalResult(id={self.id}, supplier_id={self.supplier_id}, total={self.total_score})"
```

### 3.9 引用表 (citations)

```python
# backend/src/modules/evaluation/infrastructure/models/citation.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class Citation(Base):
    """引用表（溯源记录）"""
    __tablename__ = "citations"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 关联
    eval_item_id: Mapped[int] = mapped_column(
        ForeignKey("eval_items.id", ondelete="CASCADE"), index=True, comment="评估项ID"
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"), index=True, comment="文档ID"
    )
    chunk_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("doc_chunks.id", ondelete="SET NULL"), comment="分块ID"
    )

    # 引用内容
    cited_text: Mapped[str] = mapped_column(Text, comment="引用文本")

    # 位置信息
    page: Mapped[int] = mapped_column(Integer, comment="页码")
    bbox: Mapped[Optional[dict]] = mapped_column(JSONB, comment="边界框坐标")
    # 示例: {"x1": 50, "y1": 100, "x2": 400, "y2": 200}

    # 置信度
    relevance_score: Mapped[float] = mapped_column(default=0.8, comment="相关度分数")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    eval_item: Mapped["EvalItem"] = relationship(back_populates="citations")
    document: Mapped["Document"] = relationship()

    def __repr__(self) -> str:
        return f"Citation(id={self.id}, doc_id={self.document_id}, page={self.page})"
```

### 3.10 用户表 (users)

```python
# backend/src/modules/user/infrastructure/models/user.py
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"            # 管理员
    EVALUATOR = "evaluator"    # 评标专家
    AGENT = "agent"            # 招标代理
    VIEWER = "viewer"          # 只读用户


class User(Base):
    """用户表"""
    __tablename__ = "users"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 基本信息
    username: Mapped[str] = mapped_column(String(100), unique=True, comment="用户名")
    email: Mapped[str] = mapped_column(String(255), unique=True, comment="邮箱")
    hashed_password: Mapped[str] = mapped_column(String(255), comment="密码哈希")
    full_name: Mapped[Optional[str]] = mapped_column(String(100), comment="姓名")

    # 角色
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER, comment="角色")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否活跃")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否超级管理员")

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="最后登录时间")

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username})"
```

### 3.11 审计日志表 (audit_logs)

```python
# backend/src/core/infrastructure/models/audit_log.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from src.core.database import Base


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"

    # 主键
    id: Mapped[int] = mapped_column(primary_key=True)

    # 操作信息
    action: Mapped[str] = mapped_column(String(100), comment="操作类型")
    resource_type: Mapped[str] = mapped_column(String(100), comment="资源类型")
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, comment="资源ID")

    # 操作详情
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB, comment="旧值")
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB, comment="新值")
    changes: Mapped[Optional[dict]] = mapped_column(JSONB, comment="变更详情")

    # 操作人
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), comment="操作人ID"
    )
    username: Mapped[Optional[str]] = mapped_column(String(100), comment="操作人用户名")

    # 请求信息
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), comment="IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), comment="User Agent")
    request_path: Mapped[Optional[str]] = mapped_column(String(500), comment="请求路径")
    request_method: Mapped[Optional[str]] = mapped_column(String(10), comment="请求方法")

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="操作时间")

    def __repr__(self) -> str:
        return f"AuditLog(id={self.id}, action={self.action})"
```

---

## 四、数据库配置

### 4.1 异步引擎配置

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


class Base(AsyncAttrs, DeclarativeBase):
    """异步支持的基类"""
    pass


# 数据库连接配置
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/bid_eval"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 生产环境关闭 SQL 日志
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 连接健康检查
)

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不过期，允许访问属性
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
        finally:
            await session.close()
```

---

## 五、SQL DDL 汇总

### 5.1 建表语句

```sql
-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索

-- 1. 用户表
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP
);

-- 2. 招标项目表
CREATE TABLE bid_projects (
    id BIGSERIAL PRIMARY KEY,
    project_code VARCHAR(50) NOT NULL UNIQUE,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    tender_type VARCHAR(50) NOT NULL,
    budget NUMERIC(15, 2),
    currency VARCHAR(10) NOT NULL DEFAULT 'CNY',
    publish_date TIMESTAMP,
    deadline TIMESTAMP,
    open_date TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    scoring_config JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT NOT NULL REFERENCES users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP
);

-- 3. 供应商表
CREATE TABLE suppliers (
    id BIGSERIAL PRIMARY KEY,
    supplier_code VARCHAR(50) NOT NULL UNIQUE,
    supplier_name VARCHAR(255) NOT NULL,
    unified_social_credit_code VARCHAR(18) UNIQUE,
    registered_capital NUMERIC(15, 2),
    establishment_date DATE,
    legal_representative VARCHAR(100),
    address VARCHAR(500),
    contact_person VARCHAR(100),
    contact_phone VARCHAR(50),
    email VARCHAR(255),
    qualifications JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_blacklisted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP
);

-- 4. 文档表
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES bid_projects(id) ON DELETE SET NULL,
    supplier_id BIGINT REFERENCES suppliers(id) ON DELETE SET NULL,
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    page_count INTEGER,
    parse_method VARCHAR(50),
    parse_error TEXT,
    parsed_at TIMESTAMP,
    is_indexed BOOLEAN NOT NULL DEFAULT FALSE,
    indexed_at TIMESTAMP,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT NOT NULL REFERENCES users(id),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 5. 文档分块表
CREATE TABLE doc_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    positions JSONB NOT NULL,
    section_title VARCHAR(500),
    section_path VARCHAR(1000),
    content_type VARCHAR(50) NOT NULL DEFAULT 'text',
    vector_id VARCHAR(100),
    metadata JSONB
);

-- 6. 评估会话表
CREATE TABLE evaluation_sessions (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES bid_projects(id),
    session_code VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    graph_state JSONB,
    checkpoint_id VARCHAR(100),
    total_suppliers INTEGER NOT NULL DEFAULT 0,
    completed_suppliers INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by BIGINT NOT NULL REFERENCES users(id)
);

-- 7. 评分标准表
CREATE TABLE eval_criteria (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES bid_projects(id) ON DELETE CASCADE,
    parent_id BIGINT REFERENCES eval_criteria(id) ON DELETE SET NULL,
    criteria_code VARCHAR(50) NOT NULL,
    criteria_name VARCHAR(500) NOT NULL,
    criteria_type VARCHAR(50) NOT NULL,
    max_score NUMERIC(5, 2) NOT NULL,
    is_pass_fail BOOLEAN NOT NULL DEFAULT FALSE,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    requirement TEXT NOT NULL,
    requirement_source VARCHAR(500),
    scoring_method TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 8. 评估结果表
CREATE TABLE eval_results (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    supplier_id BIGINT NOT NULL REFERENCES suppliers(id),
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    qualification_score NUMERIC(5, 2),
    qualification_passed BOOLEAN,
    compliance_score NUMERIC(5, 2),
    compliance_passed BOOLEAN,
    technical_score NUMERIC(5, 2),
    technical_max NUMERIC(5, 2) NOT NULL DEFAULT 100,
    commercial_score NUMERIC(5, 2),
    commercial_max NUMERIC(5, 2) NOT NULL DEFAULT 100,
    risk_score NUMERIC(5, 2),
    total_score NUMERIC(5, 2),
    recommendation VARCHAR(50),
    overall_assessment TEXT,
    key_findings JSONB,
    risk_alerts JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 9. 点对点评估项表
CREATE TABLE eval_items (
    id BIGSERIAL PRIMARY KEY,
    result_id BIGINT NOT NULL REFERENCES eval_results(id) ON DELETE CASCADE,
    criteria_id BIGINT NOT NULL REFERENCES eval_criteria(id),
    requirement TEXT NOT NULL,
    requirement_source VARCHAR(500) NOT NULL,
    response TEXT NOT NULL,
    response_source VARCHAR(500) NOT NULL,
    compliance_status VARCHAR(50) NOT NULL,
    score NUMERIC(5, 2) NOT NULL,
    max_score NUMERIC(5, 2) NOT NULL,
    reasoning TEXT NOT NULL,
    evidence JSONB NOT NULL,
    confidence NUMERIC(3, 2) NOT NULL DEFAULT 0.8,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at TIMESTAMP,
    reviewed_by BIGINT REFERENCES users(id),
    review_comment TEXT,
    manual_score NUMERIC(5, 2),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 10. 引用表
CREATE TABLE citations (
    id BIGSERIAL PRIMARY KEY,
    eval_item_id BIGINT NOT NULL REFERENCES eval_items(id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL REFERENCES documents(id),
    chunk_id BIGINT REFERENCES doc_chunks(id) ON DELETE SET NULL,
    cited_text TEXT NOT NULL,
    page INTEGER NOT NULL,
    bbox JSONB,
    relevance_score REAL NOT NULL DEFAULT 0.8,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 11. 审计日志表
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id BIGINT,
    old_values JSONB,
    new_values JSONB,
    changes JSONB,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(100),
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    request_path VARCHAR(500),
    request_method VARCHAR(10),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5.2 索引创建

```sql
-- 用户表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- 项目表索引
CREATE UNIQUE INDEX idx_bid_projects_code ON bid_projects(project_code) WHERE is_deleted = FALSE;
CREATE INDEX idx_bid_projects_status ON bid_projects(status) WHERE is_deleted = FALSE;
CREATE INDEX idx_bid_projects_created_at ON bid_projects(created_at DESC);
CREATE INDEX idx_bid_projects_created_by ON bid_projects(created_by);

-- 供应商表索引
CREATE INDEX idx_suppliers_name ON suppliers USING gin(to_tsvector('simple', supplier_name));
CREATE UNIQUE INDEX idx_suppliers_credit_code ON suppliers(unified_social_credit_code)
    WHERE unified_social_credit_code IS NOT NULL AND is_deleted = FALSE;
CREATE INDEX idx_suppliers_active ON suppliers(is_active) WHERE is_deleted = FALSE;

-- 文档表索引
CREATE INDEX idx_documents_project ON documents(project_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_documents_supplier ON documents(supplier_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_documents_type_status ON documents(doc_type, status) WHERE is_deleted = FALSE;
CREATE INDEX idx_documents_hash ON documents(file_hash);
CREATE INDEX idx_documents_content_search ON documents USING gin(to_tsvector('simple', file_name));

-- 分块表索引
CREATE INDEX idx_doc_chunks_document ON doc_chunks(document_id);
CREATE INDEX idx_doc_chunks_vector_id ON doc_chunks(vector_id) WHERE vector_id IS NOT NULL;
CREATE INDEX idx_doc_chunks_content_search ON doc_chunks USING gin(to_tsvector('chinese', content));

-- 评估会话表索引
CREATE INDEX idx_evaluation_sessions_project ON evaluation_sessions(project_id);
CREATE UNIQUE INDEX idx_evaluation_sessions_code ON evaluation_sessions(session_code);

-- 评分标准表索引
CREATE INDEX idx_eval_criteria_project ON eval_criteria(project_id);
CREATE INDEX idx_eval_criteria_parent ON eval_criteria(parent_id);

-- 评估结果表索引
CREATE INDEX idx_eval_results_session ON eval_results(session_id);
CREATE INDEX idx_eval_results_supplier ON eval_results(supplier_id);

-- 评估项表索引
CREATE INDEX idx_eval_items_result ON eval_items(result_id);
CREATE INDEX idx_eval_items_criteria ON eval_items(criteria_id);

-- 引用表索引
CREATE INDEX idx_citations_eval_item ON citations(eval_item_id);
CREATE INDEX idx_citations_document ON citations(document_id);

-- 审计日志表索引
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
```

---

## 六、总结

### 6.1 设计要点

| 要点 | 实现方式 |
|------|----------|
| **异步支持** | SQLAlchemy 2.0 AsyncSession + AsyncAttrs |
| **类型安全** | Mapped[type] + mapped_column |
| **软删除** | is_deleted + deleted_at |
| **审计追踪** | created_at + updated_at + created_by |
| **JSONB 扩展** | metadata, qualifications, graph_state 等 |
| **全文搜索** | to_tsvector + gin 索引 |
| **引用完整性** | 外键约束 + cascade 删除 |

### 6.2 后续优化

| 优化项 | 时机 | 说明 |
|--------|------|------|
| **分区表** | audit_logs 超过 1000 万行 | 按时间分区 |
| **读写分离** | 并发高时 | 只读副本分担查询 |
| **连接池优化** | 生产部署时 | 根据负载调整 pool_size |
| **向量索引** | 大规模检索时 | pgvector 扩展 |

---

*文档版本：v1.0*
*创建日期：2026-02-21*
*参考来源：SQLAlchemy 2.0 官方文档、FastAPI 数据库最佳实践*
