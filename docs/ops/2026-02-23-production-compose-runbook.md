# 生产级 Docker Compose 运行手册

> 日期：2026-02-23  
> 目标：在本地或受控环境以 Docker Compose 启动“真栈”并完成验收。

## 1. 生成 JWT 密钥与 JWKS

```bash
python3 scripts/generate_jwt_keys.py
```

输出：`secrets/jwt_private.pem` 与 `secrets/jwks.json`。

## 2. 启动真栈

```bash
docker compose -f docker-compose.production.yml up -d
```

## 3. 初始化 MinIO WORM

```bash
scripts/setup_minio_worm.sh
```

## 4. 验收（示例）

```bash
pytest -q tests/test_store_persistence_backend.py
pytest -q tests/test_queue_backend.py tests/test_internal_outbox_queue_api.py
```

## 5. 关闭

```bash
docker compose -f docker-compose.production.yml down
```
