from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.errors import ApiError


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _clean_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "object"


@dataclass(frozen=True)
class ObjectStorageConfig:
    backend: str
    bucket: str
    root: str
    prefix: str
    worm_mode: bool
    endpoint: str
    region: str
    access_key: str
    secret_key: str
    force_path_style: bool
    retention_days: int
    retention_mode: str


class ObjectStorageBackend:
    backend_name = "base"

    def put_object(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        filename: str,
        content_bytes: bytes,
        content_type: str | None = None,
    ) -> str:
        raise NotImplementedError

    def get_object(self, *, storage_uri: str) -> bytes:
        raise NotImplementedError

    def delete_object(self, *, storage_uri: str) -> bool:
        raise NotImplementedError

    def apply_legal_hold(self, *, storage_uri: str) -> bool:
        raise NotImplementedError

    def release_legal_hold(self, *, storage_uri: str) -> bool:
        raise NotImplementedError

    def is_legal_hold_active(self, *, storage_uri: str) -> bool:
        raise NotImplementedError

    def set_retention(self, *, storage_uri: str, mode: str, retain_until: datetime) -> bool:
        raise NotImplementedError

    def get_retention(self, *, storage_uri: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def is_retention_active(self, *, storage_uri: str, now: datetime | None = None) -> bool:
        raise NotImplementedError

    def get_presigned_url(
        self,
        *,
        storage_uri: str,
        expires_in: int = 3600,
    ) -> str | None:
        """Generate a presigned URL for the object.

        Args:
            storage_uri: The URI of the object in storage
            expires_in: URL expiration time in seconds (default 1 hour)

        Returns:
            A presigned URL that can be used to download the object,
            or None if the backend doesn't support presigned URLs.
        """
        return None


class LocalObjectStorage(ObjectStorageBackend):
    backend_name = "local"

    def __init__(self, *, config: ObjectStorageConfig) -> None:
        self._bucket = config.bucket
        self._root = Path(config.root)
        self._prefix = config.prefix.strip("/")
        self._worm_mode = bool(config.worm_mode)
        self._retention_days = max(int(config.retention_days), 0)
        self._retention_mode = (config.retention_mode or "GOVERNANCE").upper()
        self._root.mkdir(parents=True, exist_ok=True)

    def put_object(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        filename: str,
        content_bytes: bytes,
        content_type: str | None = None,
    ) -> str:
        key = self._build_key(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
            filename=filename,
        )
        path = self._path_for_key(key)
        if path.exists() and self._worm_mode:
            return self._uri_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content_bytes)
        meta = {
            "legal_hold": False,
            "content_type": content_type or "application/octet-stream",
            "created_at": _now_iso(),
            "retention_mode": self._retention_mode,
        }
        if self._retention_days > 0:
            retain_until = datetime.now(tz=UTC) + timedelta(days=self._retention_days)
            meta["retention_until"] = retain_until.isoformat()
        self._write_meta(path, meta)
        return self._uri_for_key(key)

    def get_object(self, *, storage_uri: str) -> bytes:
        path = self._path_for_uri(storage_uri)
        if not path.exists():
            raise FileNotFoundError(storage_uri)
        return path.read_bytes()

    def delete_object(self, *, storage_uri: str) -> bool:
        if self.is_legal_hold_active(storage_uri=storage_uri):
            raise ApiError(
                code="LEGAL_HOLD_ACTIVE",
                message="object is under legal hold",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )
        if self.is_retention_active(storage_uri=storage_uri):
            raise ApiError(
                code="RETENTION_ACTIVE",
                message="object is under retention",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )
        path = self._path_for_uri(storage_uri)
        if not path.exists():
            return False
        path.unlink()
        meta = self._meta_path(path)
        if meta.exists():
            meta.unlink()
        return True

    def apply_legal_hold(self, *, storage_uri: str) -> bool:
        path = self._path_for_uri(storage_uri)
        if not path.exists():
            return False
        meta = self._read_meta(path)
        meta["legal_hold"] = True
        meta["legal_hold_at"] = _now_iso()
        self._write_meta(path, meta)
        return True

    def release_legal_hold(self, *, storage_uri: str) -> bool:
        path = self._path_for_uri(storage_uri)
        if not path.exists():
            return False
        meta = self._read_meta(path)
        meta["legal_hold"] = False
        meta["legal_hold_released_at"] = _now_iso()
        self._write_meta(path, meta)
        return True

    def is_legal_hold_active(self, *, storage_uri: str) -> bool:
        path = self._path_for_uri(storage_uri)
        if not path.exists():
            return False
        meta = self._read_meta(path)
        return bool(meta.get("legal_hold", False))

    def set_retention(self, *, storage_uri: str, mode: str, retain_until: datetime) -> bool:
        path = self._path_for_uri(storage_uri)
        if not path.exists():
            return False
        meta = self._read_meta(path)
        meta["retention_mode"] = (mode or self._retention_mode).upper()
        meta["retention_until"] = retain_until.astimezone(UTC).isoformat()
        self._write_meta(path, meta)
        return True

    def get_retention(self, *, storage_uri: str) -> dict[str, Any] | None:
        path = self._path_for_uri(storage_uri)
        if not path.exists():
            return None
        meta = self._read_meta(path)
        retain_until = meta.get("retention_until")
        if not retain_until:
            return None
        return {
            "mode": meta.get("retention_mode", self._retention_mode),
            "retain_until": retain_until,
        }

    def is_retention_active(self, *, storage_uri: str, now: datetime | None = None) -> bool:
        retention = self.get_retention(storage_uri=storage_uri)
        if not retention:
            return False
        retain_until_raw = retention.get("retain_until")
        try:
            retain_until = datetime.fromisoformat(retain_until_raw)
        except Exception:
            return False
        current = now.astimezone(UTC) if now is not None else datetime.now(tz=UTC)
        if retain_until.tzinfo is None:
            retain_until = retain_until.replace(tzinfo=UTC)
        return current < retain_until

    def reset(self) -> None:
        if not self._root.exists():
            return
        for path in sorted(self._root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()

    def _build_key(self, *, tenant_id: str, object_type: str, object_id: str, filename: str) -> str:
        safe_filename = _clean_segment(filename)
        safe_type = _clean_segment(object_type)
        safe_id = _clean_segment(object_id)
        safe_tenant = _clean_segment(tenant_id)
        if safe_type == "document":
            base = f"tenants/{safe_tenant}/documents/{safe_id}/raw/{safe_filename}"
        elif safe_type == "report":
            base = f"tenants/{safe_tenant}/reports/{safe_id}/{safe_filename}"
        else:
            base = f"tenants/{safe_tenant}/{safe_type}/{safe_id}/{safe_filename}"
        if self._prefix:
            return f"{self._prefix}/{base}"
        return base

    def _uri_for_key(self, key: str) -> str:
        return f"object://{self.backend_name}/{self._bucket}/{key}"

    def _path_for_key(self, key: str) -> Path:
        return self._root / self._bucket / key

    def _path_for_uri(self, storage_uri: str) -> Path:
        parsed = _parse_storage_uri(storage_uri)
        if parsed["backend"] != self.backend_name:
            raise ValueError("storage backend mismatch")
        return self._root / parsed["bucket"] / parsed["key"]

    def _meta_path(self, path: Path) -> Path:
        return Path(f"{path}.meta.json")

    def _read_meta(self, path: Path) -> dict[str, Any]:
        meta_path = self._meta_path(path)
        if not meta_path.exists():
            return {"legal_hold": False}
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"legal_hold": False}

    def _write_meta(self, path: Path, meta: dict[str, Any]) -> None:
        meta_path = self._meta_path(path)
        meta_path.write_text(json.dumps(meta, ensure_ascii=True, sort_keys=True), encoding="utf-8")


class S3ObjectStorage(ObjectStorageBackend):
    backend_name = "s3"

    def __init__(self, *, config: ObjectStorageConfig) -> None:
        try:
            import boto3  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("boto3 is required for s3 object storage backend") from exc
        self._bucket = config.bucket
        self._prefix = config.prefix.strip("/")
        self._worm_mode = bool(config.worm_mode)
        self._retention_days = max(int(config.retention_days), 0)
        self._retention_mode = (config.retention_mode or "GOVERNANCE").upper()
        session = boto3.session.Session(
            aws_access_key_id=config.access_key or None,
            aws_secret_access_key=config.secret_key or None,
            region_name=config.region or None,
        )
        self._client = session.client(
            "s3",
            endpoint_url=config.endpoint or None,
            config=boto3.session.Config(s3={"addressing_style": "path" if config.force_path_style else "auto"}),
        )

    def put_object(
        self,
        *,
        tenant_id: str,
        object_type: str,
        object_id: str,
        filename: str,
        content_bytes: bytes,
        content_type: str | None = None,
    ) -> str:
        key = self._build_key(tenant_id=tenant_id, object_type=object_type, object_id=object_id, filename=filename)
        if self._worm_mode and self._object_exists(key):
            return self._uri_for_key(key)
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content_bytes,
            ContentType=content_type or "application/octet-stream",
        )
        if self._retention_days > 0:
            retain_until = datetime.now(tz=UTC) + timedelta(days=self._retention_days)
            self.set_retention(storage_uri=self._uri_for_key(key), mode=self._retention_mode, retain_until=retain_until)
        return self._uri_for_key(key)

    def get_object(self, *, storage_uri: str) -> bytes:
        parsed = _parse_storage_uri(storage_uri)
        response = self._client.get_object(Bucket=parsed["bucket"], Key=parsed["key"])
        return response["Body"].read()

    def delete_object(self, *, storage_uri: str) -> bool:
        if self.is_legal_hold_active(storage_uri=storage_uri):
            raise ApiError(
                code="LEGAL_HOLD_ACTIVE",
                message="object is under legal hold",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )
        if self.is_retention_active(storage_uri=storage_uri):
            raise ApiError(
                code="RETENTION_ACTIVE",
                message="object is under retention",
                error_class="business_rule",
                retryable=False,
                http_status=409,
            )
        parsed = _parse_storage_uri(storage_uri)
        self._client.delete_object(Bucket=parsed["bucket"], Key=parsed["key"])
        return True

    def apply_legal_hold(self, *, storage_uri: str) -> bool:
        parsed = _parse_storage_uri(storage_uri)
        try:
            self._client.put_object_legal_hold(
                Bucket=parsed["bucket"],
                Key=parsed["key"],
                LegalHold={"Status": "ON"},
            )
            return True
        except Exception:  # pragma: no cover - depends on bucket settings
            return False

    def release_legal_hold(self, *, storage_uri: str) -> bool:
        parsed = _parse_storage_uri(storage_uri)
        try:
            self._client.put_object_legal_hold(
                Bucket=parsed["bucket"],
                Key=parsed["key"],
                LegalHold={"Status": "OFF"},
            )
            return True
        except Exception:  # pragma: no cover
            return False

    def is_legal_hold_active(self, *, storage_uri: str) -> bool:
        parsed = _parse_storage_uri(storage_uri)
        try:
            response = self._client.get_object_legal_hold(Bucket=parsed["bucket"], Key=parsed["key"])
            return response.get("LegalHold", {}).get("Status") == "ON"
        except Exception:  # pragma: no cover
            return False

    def set_retention(self, *, storage_uri: str, mode: str, retain_until: datetime) -> bool:
        parsed = _parse_storage_uri(storage_uri)
        try:
            self._client.put_object_retention(
                Bucket=parsed["bucket"],
                Key=parsed["key"],
                Retention={
                    "Mode": (mode or self._retention_mode).upper(),
                    "RetainUntilDate": retain_until.astimezone(UTC),
                },
            )
            return True
        except Exception:  # pragma: no cover
            return False

    def get_retention(self, *, storage_uri: str) -> dict[str, Any] | None:
        parsed = _parse_storage_uri(storage_uri)
        try:
            response = self._client.get_object_retention(Bucket=parsed["bucket"], Key=parsed["key"])
        except Exception:  # pragma: no cover
            return None
        retention = response.get("Retention", {})
        if not retention:
            return None
        return {
            "mode": retention.get("Mode"),
            "retain_until": retention.get("RetainUntilDate"),
        }

    def is_retention_active(self, *, storage_uri: str, now: datetime | None = None) -> bool:
        retention = self.get_retention(storage_uri=storage_uri)
        if not retention:
            return False
        retain_until = retention.get("retain_until")
        if not isinstance(retain_until, datetime):
            return False
        current = now.astimezone(UTC) if now is not None else datetime.now(tz=UTC)
        if retain_until.tzinfo is None:
            retain_until = retain_until.replace(tzinfo=UTC)
        return current < retain_until

    def get_presigned_url(
        self,
        *,
        storage_uri: str,
        expires_in: int = 3600,
    ) -> str | None:
        """Generate a presigned URL for S3 object download."""
        parsed = _parse_storage_uri(storage_uri)
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": parsed["bucket"], "Key": parsed["key"]},
                ExpiresIn=expires_in,
            )
            return str(url)
        except Exception:  # pragma: no cover
            return None

    def _build_key(self, *, tenant_id: str, object_type: str, object_id: str, filename: str) -> str:
        safe_filename = _clean_segment(filename)
        safe_type = _clean_segment(object_type)
        safe_id = _clean_segment(object_id)
        safe_tenant = _clean_segment(tenant_id)
        if safe_type == "document":
            base = f"tenants/{safe_tenant}/documents/{safe_id}/raw/{safe_filename}"
        elif safe_type == "report":
            base = f"tenants/{safe_tenant}/reports/{safe_id}/{safe_filename}"
        else:
            base = f"tenants/{safe_tenant}/{safe_type}/{safe_id}/{safe_filename}"
        if self._prefix:
            return f"{self._prefix}/{base}"
        return base

    def _uri_for_key(self, key: str) -> str:
        return f"object://{self.backend_name}/{self._bucket}/{key}"

    def _object_exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False


def _parse_storage_uri(uri: str) -> dict[str, str]:
    if not uri.startswith("object://"):
        raise ValueError("invalid storage uri")
    raw = uri[len("object://") :]
    parts = raw.split("/", 2)
    if len(parts) != 3:
        raise ValueError("invalid storage uri")
    return {"backend": parts[0], "bucket": parts[1], "key": parts[2]}


def create_object_storage_from_env(environ: dict[str, str] | None = None) -> ObjectStorageBackend:
    env = os.environ if environ is None else environ
    backend = env.get("BEA_OBJECT_STORAGE_BACKEND", "local").strip().lower() or "local"
    retention_days_raw = env.get("OBJECT_STORAGE_RETENTION_DAYS", "0").strip() or "0"
    try:
        retention_days = int(retention_days_raw)
    except ValueError:
        retention_days = 0
    config = ObjectStorageConfig(
        backend=backend,
        bucket=env.get("OBJECT_STORAGE_BUCKET", "bea").strip() or "bea",
        root=env.get("OBJECT_STORAGE_ROOT", "/tmp/bea-object-storage").strip() or "/tmp/bea-object-storage",
        prefix=env.get("OBJECT_STORAGE_PREFIX", "").strip(),
        worm_mode=env.get("OBJECT_STORAGE_WORM_MODE", "true").strip().lower() not in {"0", "false", "no", "off"},
        endpoint=env.get("OBJECT_STORAGE_ENDPOINT", "").strip(),
        region=env.get("OBJECT_STORAGE_REGION", "").strip(),
        access_key=env.get("OBJECT_STORAGE_ACCESS_KEY", "").strip(),
        secret_key=env.get("OBJECT_STORAGE_SECRET_KEY", "").strip(),
        force_path_style=env.get("OBJECT_STORAGE_FORCE_PATH_STYLE", "true").strip().lower()
        not in {"0", "false", "no", "off"},
        retention_days=max(retention_days, 0),
        retention_mode=env.get("OBJECT_STORAGE_RETENTION_MODE", "GOVERNANCE").strip() or "GOVERNANCE",
    )
    if config.backend == "s3":
        return S3ObjectStorage(config=config)
    return LocalObjectStorage(config=config)


def build_report_filename(*, report_payload: dict[str, Any]) -> str:
    payload = dict(report_payload)
    payload.pop("report_uri", None)
    blob = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = sha256(blob).hexdigest()[:12]
    return f"report-{digest}.json"
