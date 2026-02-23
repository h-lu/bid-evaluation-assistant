#!/usr/bin/env bash
set -euo pipefail

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET="${OBJECT_STORAGE_BUCKET:-bea}"

docker run --rm --network host minio/mc:RELEASE.2024-10-29T15-34-04Z \
  alias set local "$MINIO_ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

docker run --rm --network host minio/mc:RELEASE.2024-10-29T15-34-04Z \
  mb --with-lock "local/$BUCKET" || true

docker run --rm --network host minio/mc:RELEASE.2024-10-29T15-34-04Z \
  retention set GOVERNANCE 30d "local/$BUCKET" || true

echo "MinIO bucket $BUCKET ready with object lock"
