from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient

from app.errors import ApiError


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _split_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _b64url_decode(raw: str) -> bytes:
    padded = raw + "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        if value.strip().isdigit():
            return int(value.strip())
    return None


def redact_sensitive(value: object) -> object:
    sensitive_keys = {"authorization", "token", "secret", "password", "api_key", "apikey", "access_token"}
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if key_lower in sensitive_keys:
                redacted[str(key)] = "***REDACTED***"
            else:
                redacted[str(key)] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(x) for x in value]
    if isinstance(value, str):
        if len(value) >= 24 and any(k in value.lower() for k in ("sk-", "bearer ", "token")):
            return "***REDACTED***"
    return value


@dataclass
class AuthContext:
    tenant_id: str
    subject: str
    claims: dict[str, Any]


@dataclass
class JwtSecurityConfig:
    enabled: bool
    issuer: str
    audience: str
    shared_secret: str
    jwks_url: str
    alg: str
    required_claims: list[str]
    tenant_claim: str
    approval_required_actions: set[str]
    dual_approval_required_actions: set[str]
    log_redaction_enabled: bool
    secret_scan_enabled: bool
    trace_id_strict_required: bool

    @classmethod
    def from_env(cls) -> JwtSecurityConfig:
        issuer = os.environ.get("JWT_ISSUER", "").strip()
        audience = os.environ.get("JWT_AUDIENCE", "").strip()
        shared_secret = os.environ.get("JWT_SHARED_SECRET", "").strip()
        jwks_url = os.environ.get("JWT_JWKS_URL", "").strip()
        alg = os.environ.get("JWT_ALG", "HS256").strip().upper() or "HS256"
        required_claims = _split_csv(os.environ.get("JWT_REQUIRED_CLAIMS", "tenant_id,sub,exp"))
        enabled = bool(issuer or audience or shared_secret or jwks_url)
        approval_required_actions = set(
            _split_csv(os.environ.get("SECURITY_APPROVAL_REQUIRED_ACTIONS", "dlq_discard,legal_hold_release"))
        )
        dual_approval_required_actions = set(
            _split_csv(
                os.environ.get(
                    "SECURITY_DUAL_APPROVAL_REQUIRED_ACTIONS",
                    "dlq_discard,legal_hold_release",
                )
            )
        )
        return cls(
            enabled=enabled,
            issuer=issuer,
            audience=audience,
            shared_secret=shared_secret,
            jwks_url=jwks_url,
            alg=alg,
            required_claims=required_claims,
            tenant_claim=os.environ.get("JWT_TENANT_CLAIM", "tenant_id").strip() or "tenant_id",
            approval_required_actions=approval_required_actions,
            dual_approval_required_actions=dual_approval_required_actions,
            log_redaction_enabled=_env_bool("SECURITY_LOG_REDACTION_ENABLED", True),
            secret_scan_enabled=_env_bool("SECURITY_SECRET_SCAN_ENABLED", True),
            trace_id_strict_required=_env_bool("TRACE_ID_STRICT_REQUIRED", False),
        )


_JWK_CLIENTS: dict[str, PyJWKClient] = {}


def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    client = _JWK_CLIENTS.get(jwks_url)
    if client is None:
        client = PyJWKClient(jwks_url)
        _JWK_CLIENTS[jwks_url] = client
    return client


def _parse_token_parts(token: str) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="invalid token format",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        )
    header_raw, payload_raw, signature_raw = parts
    try:
        header_obj = json.loads(_b64url_decode(header_raw))
        payload_obj = json.loads(_b64url_decode(payload_raw))
    except (json.JSONDecodeError, ValueError, TypeError):
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="invalid token payload",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        ) from None
    if not isinstance(header_obj, dict) or not isinstance(payload_obj, dict):
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="invalid token payload",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        )
    return header_obj, payload_obj, f"{header_raw}.{payload_raw}", signature_raw


def parse_and_validate_bearer_token(*, authorization: str | None, cfg: JwtSecurityConfig) -> AuthContext:
    if not authorization:
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="missing Authorization bearer token",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        )
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="invalid Authorization header",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        )
    token = authorization[len(prefix) :].strip()
    if not token:
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="empty bearer token",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        )
    header_obj, _payload_obj, _signing_input, _signature_raw = _parse_token_parts(token)
    token_alg = str(header_obj.get("alg", "")).upper()
    if token_alg != cfg.alg:
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="unsupported jwt algorithm",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        )

    decode_kwargs: dict[str, Any] = {
        "algorithms": [cfg.alg],
        "options": {"require": cfg.required_claims},
    }
    if cfg.issuer:
        decode_kwargs["issuer"] = cfg.issuer
    if cfg.audience:
        decode_kwargs["audience"] = cfg.audience

    try:
        if cfg.alg.startswith("RS"):
            if not cfg.jwks_url:
                raise ApiError(
                    code="AUTH_UNAUTHORIZED",
                    message="jwks url not configured",
                    error_class="security_sensitive",
                    retryable=False,
                    http_status=401,
                )
            jwk_client = _get_jwk_client(cfg.jwks_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token).key
            payload_obj = jwt.decode(token, signing_key, **decode_kwargs)
        else:
            if not cfg.shared_secret:
                raise ApiError(
                    code="AUTH_UNAUTHORIZED",
                    message="jwt shared secret not configured",
                    error_class="security_sensitive",
                    retryable=False,
                    http_status=401,
                )
            payload_obj = jwt.decode(token, cfg.shared_secret, **decode_kwargs)
    except ApiError:
        raise
    except jwt.PyJWTError as exc:
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="invalid token",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        ) from exc

    tenant_id = str(payload_obj.get(cfg.tenant_claim) or "").strip()
    subject = str(payload_obj.get("sub") or "").strip()
    if not tenant_id or not subject:
        raise ApiError(
            code="AUTH_UNAUTHORIZED",
            message="missing tenant or subject claim",
            error_class="security_sensitive",
            retryable=False,
            http_status=401,
        )
    return AuthContext(
        tenant_id=tenant_id,
        subject=subject,
        claims=payload_obj,
    )
