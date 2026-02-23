#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> int:
    secrets_dir = Path("secrets")
    secrets_dir.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    (secrets_dir / "jwt_private.pem").write_bytes(private_pem)

    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    public_jwk["use"] = "sig"
    public_jwk["alg"] = "RS256"
    public_jwk["kid"] = "bea-local-1"
    jwks = {"keys": [public_jwk]}
    (secrets_dir / "jwks.json").write_text(json.dumps(jwks, ensure_ascii=True, indent=2))
    print("wrote secrets/jwt_private.pem and secrets/jwks.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
