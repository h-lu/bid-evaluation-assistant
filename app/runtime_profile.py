from __future__ import annotations

from collections.abc import Mapping
import os


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def true_stack_required(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return _as_bool(env.get("BEA_REQUIRE_TRUESTACK", "false"))
