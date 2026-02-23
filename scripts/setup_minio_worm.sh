#!/usr/bin/env bash
set -euo pipefail

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET="${OBJECT_STORAGE_BUCKET:-bea}"

MINIO_CONTAINER_ID="$(docker compose -f docker-compose.production.yml ps -q minio 2>/dev/null || true)"

if [[ -n "$MINIO_CONTAINER_ID" ]]; then
  docker exec "$MINIO_CONTAINER_ID" mc alias set local "http://127.0.0.1:9000" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" --api S3v4 --path on
  docker exec "$MINIO_CONTAINER_ID" mc mb --with-lock "local/$BUCKET" || true
  docker exec "$MINIO_CONTAINER_ID" mc retention set --default governance 30d "local/$BUCKET/" || true
else
  docker run --rm --network host minio/mc:latest \
    alias set local "$MINIO_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" --api S3v4 --path on
  docker run --rm --network host minio/mc:latest \
    mb --with-lock "local/$BUCKET" || true
  docker run --rm --network host minio/mc:latest \
    retention set --default governance 30d "local/$BUCKET/" || true
fi

echo "MinIO bucket $BUCKET ready with object lock"
