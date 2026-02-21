# 部署配置设计

> 版本：v1.0
> 设计日期：2026-02-21

---

## 一、部署架构

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              生产环境部署架构                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│                           ┌─────────────┐                                           │
│                           │   Nginx     │  (反向代理 / SSL 终结)                    │
│                           │   :443      │                                           │
│                           └──────┬──────┘                                           │
│                                  │                                                  │
│              ┌───────────────────┼───────────────────┐                              │
│              │                   │                   │                              │
│              ▼                   ▼                   ▼                              │
│   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐                   │
│   │   Frontend       │ │   Backend API    │ │   LightRAG API   │                   │
│   │   (Vue3 SPA)     │ │   (FastAPI)      │ │   (可选独立服务)  │                   │
│   │   :80            │ │   :8000          │ │   :9621          │                   │
│   └──────────────────┘ └────────┬─────────┘ └──────────────────┘                   │
│                                  │                                                  │
│              ┌───────────────────┼───────────────────┐                              │
│              │                   │                   │                              │
│              ▼                   ▼                   ▼                              │
│   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐                   │
│   │   PostgreSQL     │ │   Redis          │ │   ChromaDB       │                   │
│   │   :5432          │ │   :6379          │ │   (向量存储)      │                   │
│   └──────────────────┘ └──────────────────┘ └──────────────────┘                   │
│                                                                                     │
│   ┌──────────────────┐ ┌──────────────────┐                                         │
│   │   MinIO / S3     │ │   Langfuse       │  (可选: 可观测性)                       │
│   │   (对象存储)      │ │   :3000          │                                         │
│   └──────────────────┘ └──────────────────┘                                         │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、Docker 配置

### 2.1 后端 Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir --target=/app/deps -e ".[dev]"

# 最终镜像
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖
COPY --from=builder /app/deps /usr/local/lib/python3.11/site-packages

# 复制代码
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

# 创建必要目录
RUN mkdir -p uploads lightrag_storage logs

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令
CMD ["uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 前端 Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Nginx 服务
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 2.3 Docker Compose (开发环境)

```yaml
# docker-compose.yml
version: "3.8"

services:
  # 后端 API
  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/bid_eval
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o-mini}
      - REDIS_URL=redis://redis:6379/0
      - UPLOAD_DIR=/app/uploads
      - LIGHTRAG_WORKING_DIR=/app/lightrag_storage
    volumes:
      - ./uploads:/app/uploads
      - ./lightrag_storage:/app/lightrag_storage
      - ./logs:/app/logs
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - bid-eval-network
    restart: unless-stopped

  # 前端
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - api
    networks:
      - bid-eval-network
    restart: unless-stopped

  # PostgreSQL 数据库
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=bid_eval
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - bid-eval-network
    restart: unless-stopped

  # Redis 缓存
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - bid-eval-network
    restart: unless-stopped

  # MinIO 对象存储（可选，生产环境用 S3）
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - bid-eval-network
    restart: unless-stopped

networks:
  bid-eval-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### 2.4 Docker Compose (生产环境)

```yaml
# docker-compose.prod.yml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
      args:
        - ENV=production
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=${REDIS_URL}
      - CORS_ORIGINS=https://your-domain.com
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "2"
          memory: 4G
        reservations:
          cpus: "0.5"
          memory: 1G
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
        interval: 30s
        timeout: 10s
        retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - VITE_API_BASE_URL=https://api.your-domain.com
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 2G

volumes:
  postgres_data:
  redis_data:
```

---

## 三、Nginx 配置

### 3.1 前端 Nginx

```nginx
# frontend/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    keepalive_timeout 65;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml;

    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;

        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # SPA 路由
        location / {
            try_files $uri $uri/ /index.html;
        }

        # API 代理
        location /api/ {
            proxy_pass http://api:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        # 健康检查
        location /health {
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### 3.2 生产环境 Nginx (SSL)

```nginx
# /etc/nginx/conf.d/bid-eval.conf
upstream api_backend {
    least_conn;
    server api:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # 现代加密配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 前端静态文件
    location / {
        root /var/www/frontend;
        try_files $uri $uri/ /index.html;

        # 缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API 代理
    location /api/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # 文件上传大小限制
        client_max_body_size 100M;
    }

    # 日志
    access_log /var/log/nginx/bid-eval-access.log;
    error_log /var/log/nginx/bid-eval-error.log;
}
```

---

## 四、环境变量配置

### 4.1 后端环境变量

```bash
# .env.example (生产环境)

# 应用配置
APP_NAME=bid-evaluation-assistant
APP_ENV=production
DEBUG=false

# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/bid_eval
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://:password@redis-host:6379/0

# 安全
SECRET_KEY=your-256-bit-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS
CORS_ORIGINS=https://your-domain.com

# LLM 配置
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# 本地 LLM (可选)
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=qwen2.5:7b

# Embedding
EMBEDDING_MODEL=BAAI/bge-m3

# 存储
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE=104857600

# LightRAG
LIGHTRAG_WORKING_DIR=/app/lightrag_storage

# 可观测性
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=https://cloud.langfuse.com

# 日志
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 4.2 前端环境变量

```bash
# frontend/.env.production

VITE_API_BASE_URL=https://api.your-domain.com
VITE_APP_TITLE=辅助评标专家系统
```

---

## 五、数据库初始化

### 5.1 初始化脚本

```sql
-- init.sql
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建初始管理员用户
INSERT INTO users (username, email, hashed_password, role, is_active, is_superuser)
VALUES (
    'admin',
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYqBpB.dQ.eG',  -- password: admin123
    'admin',
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- 创建索引（如果 Alembic 迁移未创建）
CREATE INDEX IF NOT EXISTS idx_bid_projects_status ON bid_projects(status) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id) WHERE is_deleted = FALSE;
```

### 5.2 Alembic 迁移

```bash
# 初始化迁移
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

---

## 六、监控与健康检查

### 6.1 健康检查端点

```python
# backend/src/modules/health/api/routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from src.core.database import SessionDep
from src.core.config import get_settings

router = APIRouter(tags=["健康检查"])
settings = get_settings()


@router.get("/health")
async def health_check(session: SessionDep):
    """健康检查"""
    checks = {}

    # 数据库检查
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    # Redis 检查
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        checks["redis"] = "healthy"
        await redis_client.close()
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"

    # LightRAG 检查
    try:
        import os
        if os.path.exists(settings.lightrag_working_dir):
            checks["lightrag"] = "healthy"
        else:
            checks["lightrag"] = "unhealthy: working directory not found"
    except Exception as e:
        checks["lightrag"] = f"unhealthy: {str(e)}"

    all_healthy = all(v == "healthy" for v in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": "1.0.0",
        "components": checks
    }


@router.get("/ready")
async def readiness_check(session: SessionDep):
    """就绪检查（Kubernetes 使用）"""
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except:
        return {"status": "not ready"}, 503


@router.get("/live")
async def liveness_check():
    """存活检查（Kubernetes 使用）"""
    return {"status": "alive"}
```

### 6.2 Prometheus 指标

```python
# backend/src/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# 请求计数
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# 活跃评估数
ACTIVE_EVALUATIONS = Gauge(
    'active_evaluations',
    'Number of active evaluations'
)


async def metrics_endpoint():
    """Prometheus 指标端点"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

---

## 七、备份与恢复

### 7.1 数据库备份脚本

```bash
#!/bin/bash
# scripts/backup.sh

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups
DB_NAME=bid_eval

# 创建备份目录
mkdir -p $BACKUP_DIR

# PostgreSQL 备份
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 保留最近 7 天的备份
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_$DATE.sql.gz"
```

### 7.2 恢复脚本

```bash
#!/bin/bash
# scripts/restore.sh

set -e

BACKUP_FILE=$1
DB_NAME=bid_eval

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup_file>"
    exit 1
fi

# 恢复数据库
gunzip -c $BACKUP_FILE | psql -h $DB_HOST -U $DB_USER $DB_NAME

echo "Restore completed from: $BACKUP_FILE"
```

---

## 八、CI/CD 配置

### 8.1 GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: .
          file: backend/Dockerfile
          push: true
          tags: your-org/bid-eval-api:latest

      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: your-org/bid-eval-frontend:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /app/bid-evaluation-assistant
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker system prune -f
```

---

## 九、部署清单

| 检查项 | 说明 |
|--------|------|
| ✅ 环境变量配置 | 所有敏感信息通过环境变量注入 |
| ✅ SSL 证书 | 使用 Let's Encrypt 自动更新 |
| ✅ 数据库备份 | 每日自动备份，保留 7 天 |
| ✅ 日志收集 | JSON 格式日志，集中收集 |
| ✅ 健康检查 | /health, /ready, /live 端点 |
| ✅ 监控告警 | Prometheus + Grafana |
| ✅ 滚动更新 | 零停机部署 |
| ✅ 回滚机制 | 保留最近 3 个版本 |

---

*文档版本：v1.0*
*创建日期：2026-02-21*
