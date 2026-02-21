# 安全实现规范

> 版本：v1.0
> 设计日期：2026-02-21

---

## 一、认证与授权

### 1.1 JWT 认证流程

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              JWT 认证流程                                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   客户端                     后端 API                     数据库                     │
│      │                          │                           │                        │
│      │  POST /auth/login        │                           │                        │
│      │  {username, password}    │                           │                        │
│      │ ────────────────────────►│                           │                        │
│      │                          │  SELECT * FROM users      │                        │
│      │                          │ ──────────────────────────►│                        │
│      │                          │◄────────────────────────── │                        │
│      │                          │                           │                        │
│      │                          │  verify_password()        │                        │
│      │                          │  create_access_token()    │                        │
│      │                          │                           │                        │
│      │  {access_token, user}    │                           │                        │
│      │◄──────────────────────── │                           │                        │
│      │                          │                           │                        │
│      │  GET /projects           │                           │                        │
│      │  Authorization: Bearer   │                           │                        │
│      │ ────────────────────────►│                           │                        │
│      │                          │  verify_token()           │                        │
│      │                          │  get_current_user()       │                        │
│      │                          │                           │                        │
│      │  {projects: [...]}       │                           │                        │
│      │◄──────────────────────── │                           │                        │
│      │                          │                           │                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 角色权限矩阵

| 角色 | 项目管理 | 文档管理 | 评估管理 | 报告查看 | 用户管理 |
|------|:--------:|:--------:|:--------:|:--------:|:--------:|
| **admin** | ✅ 全部 | ✅ 全部 | ✅ 全部 | ✅ 全部 | ✅ 全部 |
| **evaluator** | ✅ 查看 | ✅ 查看 | ✅ 审核/执行 | ✅ 全部 | ❌ |
| **agent** | ✅ 创建/编辑 | ✅ 上传 | ✅ 创建 | ✅ 本项目 | ❌ |
| **viewer** | ✅ 查看 | ✅ 查看 | ❌ | ✅ 查看 | ❌ |

### 1.3 权限实现

```python
# backend/src/core/permissions.py
from functools import wraps
from typing import List, Callable
from fastapi import HTTPException, status
from src.modules.user.infrastructure.models.user import UserRole


def require_roles(allowed_roles: List[UserRole]):
    """角色权限装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user, **kwargs):
            if current_user.role not in allowed_roles and not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_project_access(action: str = "read"):
    """项目访问权限检查"""
    async def check_access(project_id: int, current_user, session):
        from src.modules.project.infrastructure.models.project import BidProject
        from sqlalchemy import select

        result = await session.execute(
            select(BidProject).where(BidProject.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 超级管理员有全部权限
        if current_user.is_superuser:
            return project

        # 检查项目创建者
        if project.created_by == current_user.id:
            return project

        # 检查角色权限
        if current_user.role == UserRole.VIEWER and action != "read":
            raise HTTPException(status_code=403, detail="权限不足")

        return project

    return check_access
```

---

## 二、API 安全

### 2.1 速率限制

```python
# backend/src/core/rate_limit.py
from fastapi import Request, HTTPException, status
from fastapi.dependencies import Depends
import redis.asyncio as redis
from src.core.config import get_settings

settings = get_settings()
redis_client = redis.from_url(settings.redis_url)


async def rate_limit(
    request: Request,
    key_prefix: str = "api",
    max_requests: int = 100,
    window_seconds: int = 60
):
    """速率限制中间件"""
    client_ip = request.client.host
    key = f"rate_limit:{key_prefix}:{client_ip}"

    current = await redis_client.get(key)
    if current and int(current) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试"
        )

    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    await pipe.execute()


# 在路由中使用
@router.post("/query", dependencies=[Depends(lambda r: rate_limit(r, "query", 20, 60))])
async def query(...):
    pass
```

### 2.2 输入验证

```python
# backend/src/core/validation.py
import re
from pydantic import field_validator
from fastapi import HTTPException


class SanitizedInput:
    """输入清理工具"""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名"""
        # 移除路径遍历
        filename = filename.replace("..", "").replace("/", "").replace("\\", "")
        # 只保留安全字符
        filename = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', filename)
        return filename[:255]

    @staticmethod
    def validate_file_type(content_type: str, allowed_types: list) -> None:
        """验证文件类型"""
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {content_type}"
            )


# 在 Schema 中使用
class DocumentUpload(BaseModel):
    file_name: str

    @field_validator('file_name')
    @classmethod
    def validate_file_name(cls, v):
        return SanitizedInput.sanitize_filename(v)
```

### 2.3 SQL 注入防护

```python
# 使用 SQLAlchemy ORM 参数化查询（自动防护）
# ✅ 正确
result = await session.execute(
    select(User).where(User.username == username)
)

# ❌ 错误（不要使用字符串拼接）
# query = f"SELECT * FROM users WHERE username = '{username}'"
```

---

## 三、数据安全

### 3.1 敏感数据加密

```python
# backend/src/core/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

from src.core.config import get_settings

settings = get_settings()


class DataEncryptor:
    """敏感数据加密器"""

    def __init__(self):
        # 从密钥派生加密密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'bid_eval_salt',  # 生产环境应使用随机 salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))
        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        """加密数据"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()


# 使用示例
encryptor = DataEncryptor()

# 加密敏感配置
encrypted_api_key = encryptor.encrypt("sk-xxx")

# 解密使用
api_key = encryptor.decrypt(encrypted_api_key)
```

### 3.2 密码安全

```python
# backend/src/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # 增加密成本
)


def hash_password(password: str) -> str:
    """密码哈希"""
    # 验证密码强度
    if len(password) < 8:
        raise ValueError("密码长度至少8位")
    if not any(c.isupper() for c in password):
        raise ValueError("密码需包含大写字母")
    if not any(c.isdigit() for c in password):
        raise ValueError("密码需包含数字")

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """密码验证"""
    return pwd_context.verify(plain_password, hashed_password)
```

---

## 四、审计日志

### 4.1 审计日志中间件

```python
# backend/src/core/audit.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import json

from src.core.database import async_session_factory
from src.core.infrastructure.models.audit_log import AuditLog


class AuditMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""

    async def dispatch(self, request: Request, call_next):
        # 记录请求开始时间
        start_time = datetime.utcnow()

        # 执行请求
        response: Response = await call_next(request)

        # 记录审计日志（仅记录写操作）
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            await self._log_audit(request, response, start_time)

        return response

    async def _log_audit(self, request, response, start_time):
        try:
            # 获取当前用户
            user_id = getattr(request.state, "user_id", None)
            username = getattr(request.state, "username", None)

            # 获取请求体（需要特殊处理）
            request_body = getattr(request.state, "request_body", None)

            async with async_session_factory() as session:
                audit_log = AuditLog(
                    action=f"{request.method} {request.url.path}",
                    resource_type=self._extract_resource_type(request.url.path),
                    resource_id=self._extract_resource_id(request.url.path),
                    user_id=user_id,
                    username=username,
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent", ""),
                    request_path=request.url.path,
                    request_method=request.method,
                    created_at=start_time
                )
                session.add(audit_log)
                await session.commit()
        except Exception as e:
            # 审计日志失败不应影响请求
            print(f"Audit log error: {e}")

    def _extract_resource_type(self, path: str) -> str:
        parts = path.split("/")
        if len(parts) >= 4:
            return parts[3]  # /api/v1/{resource}
        return "unknown"

    def _extract_resource_id(self, path: str) -> int | None:
        import re
        match = re.search(r'/(\d+)(?:/|$)', path)
        return int(match.group(1)) if match else None
```

### 4.2 关键操作审计

```python
# 在关键服务中添加审计
class EvaluationService:
    async def start_evaluation(self, session_id: int, user):
        # 业务逻辑
        ...

        # 记录审计
        await self._audit(
            action="evaluation_started",
            resource_type="evaluation_session",
            resource_id=session_id,
            user=user,
            details={"status": "in_progress"}
        )

    async def submit_review(self, item_id: int, decision: str, user):
        # 业务逻辑
        ...

        # 记录审计
        await self._audit(
            action="review_submitted",
            resource_type="eval_item",
            resource_id=item_id,
            user=user,
            details={"decision": decision, "reviewer": user.username}
        )
```

---

## 五、安全检查清单

| 检查项 | 实现 | 状态 |
|--------|------|------|
| JWT Token 认证 | python-jose + HS256 | ✅ |
| 密码哈希 | bcrypt (12 rounds) | ✅ |
| CORS 限制 | 白名单域名 | ✅ |
| 速率限制 | Redis + IP 限制 | ✅ |
| SQL 注入防护 | SQLAlchemy ORM | ✅ |
| XSS 防护 | 输入清理 + 输出编码 | ✅ |
| 文件上传安全 | 类型验证 + 大小限制 | ✅ |
| 敏感数据加密 | Fernet 对称加密 | ✅ |
| HTTPS 强制 | Nginx SSL 终结 | ✅ |
| 审计日志 | 中间件自动记录 | ✅ |
| 错误信息脱敏 | 不暴露内部细节 | ✅ |
| 依赖安全扫描 | pip-audit | ✅ |

---

*文档版本：v1.0*
*创建日期：2026-02-21*
