# 错误处理规范

> 版本：v1.0
> 设计日期：2026-02-21

---

## 一、错误码体系

### 1.1 错误码格式

```
E[模块][类型][序号]
│  │     │     │
│  │     │     └── 3位序号
│  │     └── 1位类型 (0=通用, 1=参数, 2=业务, 3=系统)
│  └── 1位模块 (1=通用, 2=项目, 3=文档, 4=评估, 5=RAG)
└── 错误标识
```

### 1.2 错误码清单

| 错误码 | 说明 | HTTP 状态码 |
|--------|------|-------------|
| **通用错误 (E1xxx)** | | |
| E1000 | 未知错误 | 500 |
| E1001 | 请求参数无效 | 400 |
| E1002 | 参数验证失败 | 422 |
| E1003 | 未授权访问 | 401 |
| E1004 | 权限不足 | 403 |
| E1005 | 资源不存在 | 404 |
| E1006 | 资源冲突 | 409 |
| E1007 | 请求过于频繁 | 429 |
| **项目错误 (E2xxx)** | | |
| E2001 | 项目不存在 | 404 |
| E2002 | 项目编号已存在 | 409 |
| E2003 | 项目状态无效 | 400 |
| E2004 | 项目已有进行中的评估 | 409 |
| **文档错误 (E3xxx)** | | |
| E3001 | 文档不存在 | 404 |
| E3002 | 文档解析失败 | 500 |
| E3003 | 文档上传失败 | 500 |
| E3004 | 不支持的文件类型 | 400 |
| E3005 | 文件大小超限 | 413 |
| E3006 | 文件哈希校验失败 | 400 |
| **评估错误 (E4xxx)** | | |
| E4001 | 评估会话不存在 | 404 |
| E4002 | 评估已在进行中 | 409 |
| E4003 | 评估未准备好 | 400 |
| E4004 | 供应商不在项目中 | 400 |
| E4005 | 评估项不存在 | 404 |
| E4006 | 已审核不能修改 | 400 |
| **RAG 错误 (E5xxx)** | | |
| E5001 | 检索失败 | 500 |
| E5002 | 索引失败 | 500 |
| E5003 | 查询超时 | 504 |
| E5004 | 向量服务不可用 | 503 |
| E5005 | LLM 服务不可用 | 503 |

---

## 二、错误响应格式

### 2.1 标准错误响应

```json
{
  "success": false,
  "error": {
    "code": "E1002",
    "message": "参数验证失败",
    "field": "project_name",
    "details": {
      "expected": "string",
      "received": "null"
    }
  },
  "request_id": "req_abc123",
  "timestamp": "2026-02-21T10:00:00Z"
}
```

### 2.2 错误响应模型

```python
# backend/src/core/api/errors.py
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 通用错误
    UNKNOWN_ERROR = "E1000"
    INVALID_REQUEST = "E1001"
    VALIDATION_ERROR = "E1002"
    UNAUTHORIZED = "E1003"
    FORBIDDEN = "E1004"
    NOT_FOUND = "E1005"
    CONFLICT = "E1006"
    RATE_LIMITED = "E1007"

    # 项目错误
    PROJECT_NOT_FOUND = "E2001"
    PROJECT_ALREADY_EXISTS = "E2002"
    PROJECT_STATUS_INVALID = "E2003"

    # 文档错误
    DOCUMENT_NOT_FOUND = "E3001"
    DOCUMENT_PARSE_FAILED = "E3002"
    DOCUMENT_UPLOAD_FAILED = "E3003"
    DOCUMENT_TYPE_INVALID = "E3004"
    FILE_SIZE_EXCEEDED = "E3005"

    # 评估错误
    EVALUATION_NOT_FOUND = "E4001"
    EVALUATION_ALREADY_RUNNING = "E4002"

    # RAG 错误
    RETRIEVAL_FAILED = "E5001"
    INDEXING_FAILED = "E5002"
    QUERY_TIMEOUT = "E5003"


class ErrorDetail(BaseModel):
    """错误详情"""
    code: ErrorCode
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: ErrorDetail
    request_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# 错误消息映射
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.UNKNOWN_ERROR: "未知错误，请稍后重试",
    ErrorCode.INVALID_REQUEST: "请求参数无效",
    ErrorCode.VALIDATION_ERROR: "参数验证失败",
    ErrorCode.UNAUTHORIZED: "未授权访问，请先登录",
    ErrorCode.FORBIDDEN: "权限不足",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.CONFLICT: "资源冲突",
    ErrorCode.RATE_LIMITED: "请求过于频繁，请稍后重试",
    ErrorCode.PROJECT_NOT_FOUND: "项目不存在",
    ErrorCode.PROJECT_ALREADY_EXISTS: "项目编号已存在",
    ErrorCode.DOCUMENT_NOT_FOUND: "文档不存在",
    ErrorCode.DOCUMENT_PARSE_FAILED: "文档解析失败",
    ErrorCode.EVALUATION_NOT_FOUND: "评估会话不存在",
    ErrorCode.RETRIEVAL_FAILED: "检索服务异常",
}
```

---

## 三、异常类定义

### 3.1 业务异常基类

```python
# backend/src/core/exceptions.py
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

from src.core.api.errors import ErrorCode, ERROR_MESSAGES


class AppException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        http_status: int = status.HTTP_400_BAD_REQUEST
    ):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "未知错误")
        self.field = field
        self.details = details
        self.http_status = http_status
        super().__init__(self.message)

    def to_error_response(self) -> dict:
        """转换为错误响应"""
        return {
            "success": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "field": self.field,
                "details": self.details
            }
        }


# 具体异常类
class NotFoundException(AppException):
    """资源不存在异常"""

    def __init__(self, resource: str, resource_id: Optional[int] = None):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource}不存在",
            details={"resource": resource, "id": resource_id},
            http_status=status.HTTP_404_NOT_FOUND
        )


class UnauthorizedException(AppException):
    """未授权异常"""

    def __init__(self, message: str = "未授权访问"):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            http_status=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenException(AppException):
    """权限不足异常"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            http_status=status.HTTP_403_FORBIDDEN
        )


class ValidationException(AppException):
    """验证失败异常"""

    def __init__(self, field: str, message: str, details: Optional[dict] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            field=field,
            details=details,
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class ConflictException(AppException):
    """资源冲突异常"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            code=ErrorCode.CONFLICT,
            message=message,
            details=details,
            http_status=status.HTTP_409_CONFLICT
        )


class RateLimitedException(AppException):
    """请求限流异常"""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            message=f"请求过于频繁，请 {retry_after} 秒后重试",
            details={"retry_after": retry_after},
            http_status=status.HTTP_429_TOO_MANY_REQUESTS
        )
        self.retry_after = retry_after


class ExternalServiceException(AppException):
    """外部服务异常"""

    def __init__(self, service: str, message: str = "服务暂时不可用"):
        super().__init__(
            code=ErrorCode.UNKNOWN_ERROR,
            message=f"{service}: {message}",
            details={"service": service},
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
```

---

## 四、全局异常处理

### 4.1 异常处理器

```python
# backend/src/core/exception_handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
import logging
import uuid

from src.core.exceptions import AppException
from src.core.api.errors import ErrorCode, ErrorResponse

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """应用异常处理器"""
    request_id = str(uuid.uuid4())[:8]

    logger.warning(
        f"AppException [{request_id}]: {exc.code.value} - {exc.message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.code.value,
            "field": exc.field,
            "details": exc.details
        }
    )

    response = exc.to_error_response()
    response["request_id"] = request_id

    return JSONResponse(
        status_code=exc.http_status,
        content=response
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic 验证异常处理器"""
    request_id = str(uuid.uuid4())[:8]

    # 提取验证错误
    errors = exc.errors()
    first_error = errors[0] if errors else {}

    field = ".".join(str(loc) for loc in first_error.get("loc", []))
    message = first_error.get("msg", "参数验证失败")

    logger.warning(
        f"ValidationError [{request_id}]: {field} - {message}",
        extra={"request_id": request_id, "errors": errors}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": message,
                "field": field,
                "details": {"errors": errors}
            },
            "request_id": request_id
        }
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """数据库完整性错误处理器"""
    request_id = str(uuid.uuid4())[:8]

    logger.error(
        f"IntegrityError [{request_id}]: {str(exc)}",
        extra={"request_id": request_id}
    )

    # 解析错误类型
    error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)

    if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
        code = ErrorCode.CONFLICT
        message = "资源已存在"
    else:
        code = ErrorCode.UNKNOWN_ERROR
        message = "数据操作失败"

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "error": {
                "code": code.value,
                "message": message
            },
            "request_id": request_id
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    request_id = str(uuid.uuid4())[:8]

    logger.exception(
        f"UnhandledException [{request_id}]: {type(exc).__name__}: {str(exc)}",
        extra={"request_id": request_id, "path": request.url.path}
    )

    # 生产环境不暴露详细错误
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.UNKNOWN_ERROR.value,
                "message": "服务器内部错误，请稍后重试"
            },
            "request_id": request_id
        }
    )
```

### 4.2 注册异常处理器

```python
# backend/src/main.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import AppException
from src.core.exception_handlers import (
    app_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    generic_exception_handler
)


def create_app() -> FastAPI:
    app = FastAPI(...)

    # 注册异常处理器
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    return app
```

---

## 五、重试策略

### 5.1 外部服务重试

```python
# backend/src/core/retry.py
import asyncio
from functools import wraps
from typing import Callable, Type, Tuple
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


def retry_on_failure(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """重试装饰器"""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
        retry=retry_if_exception_type(retry_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


# 使用示例
@retry_on_failure(max_attempts=3, retry_exceptions=(ConnectionError, TimeoutError))
async def call_llm_service(prompt: str) -> str:
    """调用 LLM 服务（带重试）"""
    ...
```

### 5.2 断路器

```python
# backend/src/core/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
import asyncio
from typing import Optional


class CircuitState(str, Enum):
    CLOSED = "closed"      # 正常
    OPEN = "open"          # 断开
    HALF_OPEN = "half_open"  # 半开


class CircuitBreaker:
    """断路器"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.half_open_requests = half_open_requests

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_success_count = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def can_execute(self) -> bool:
        """检查是否可以执行"""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # 检查是否可以进入半开状态
                if datetime.utcnow() - self._last_failure_time > self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_success_count = 0
                    return True
                return False

            # HALF_OPEN 状态
            return True

    async def record_success(self):
        """记录成功"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_success_count += 1
                if self._half_open_success_count >= self.half_open_requests:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def record_failure(self):
        """记录失败"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN


# 使用示例
llm_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

async def call_llm_with_circuit(prompt: str) -> str:
    if not await llm_circuit.can_execute():
        raise ExternalServiceException("LLM Service", "服务暂时不可用")

    try:
        result = await actual_llm_call(prompt)
        await llm_circuit.record_success()
        return result
    except Exception as e:
        await llm_circuit.record_failure()
        raise
```

---

## 六、降级策略

### 6.1 服务降级

```python
# backend/src/core/degradation.py
from typing import Optional, Any, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def with_fallback(fallback_func: Callable, enabled: bool = True):
    """降级装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not enabled:
                return await func(*args, **kwargs)

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Service degraded: {func.__name__} -> {fallback_func.__name__}: {e}"
                )
                return await fallback_func(*args, **kwargs)
        return wrapper
    return decorator


# 降级实现示例
async def get_rag_result_with_fallback(query: str) -> dict:
    """RAG 查询（带降级）"""
    try:
        # 尝试使用 LightRAG
        return await lightrag_query(query)
    except Exception as e:
        logger.warning(f"LightRAG failed, falling back to simple search: {e}")
        # 降级为简单向量检索
        return await simple_vector_search(query)


async def simple_vector_search(query: str) -> dict:
    """简单向量检索（降级方案）"""
    # 直接使用 ChromaDB，不经过 LightRAG
    return {"answer": "基于降级检索的结果", "confidence": 0.6}
```

### 6.2 功能开关

```python
# backend/src/core/features.py
from typing import Dict
from enum import Enum


class Feature(str, Enum):
    """功能开关"""
    RAG_ENHANCED = "rag_enhanced"        # 增强 RAG（使用 LightRAG 图谱）
    AUTO_EVALUATION = "auto_evaluation"  # 自动评估
    HUMAN_REVIEW = "human_review"        # 人工审核
    PDF_HIGHLIGHT = "pdf_highlight"      # PDF 高亮


class FeatureFlags:
    """功能开关管理"""

    def __init__(self):
        self._flags: Dict[Feature, bool] = {
            Feature.RAG_ENHANCED: True,
            Feature.AUTO_EVALUATION: True,
            Feature.HUMAN_REVIEW: True,
            Feature.PDF_HIGHLIGHT: True,
        }

    def is_enabled(self, feature: Feature) -> bool:
        return self._flags.get(feature, False)

    def enable(self, feature: Feature):
        self._flags[feature] = True

    def disable(self, feature: Feature):
        self._flags[feature] = False


feature_flags = FeatureFlags()


# 使用示例
if feature_flags.is_enabled(Feature.RAG_ENHANCED):
    result = await lightrag_query(query)
else:
    result = await simple_vector_search(query)
```

---

## 七、错误处理最佳实践

| 场景 | 策略 |
|------|------|
| **外部 API 调用** | 重试 + 超时 + 断路器 |
| **数据库操作** | 事务回滚 + 重试（乐观锁） |
| **文件处理** | 校验 + 降级（跳过错误文件） |
| **LLM 调用** | 重试 + 降级（使用缓存/简单模型） |
| **向量检索** | 降级（简单向量检索） |

---

*文档版本：v1.0*
*创建日期：2026-02-21*
