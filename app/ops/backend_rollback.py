from __future__ import annotations

from collections.abc import Mapping

TARGETS = {
    "BEA_STORE_BACKEND": "sqlite",
    "BEA_QUEUE_BACKEND": "sqlite",
}


def switch_backends_to_sqlite(env: Mapping[str, str]) -> dict[str, str]:
    out = dict(env)
    for k, v in TARGETS.items():
        out[k] = v
    return out


def update_dotenv_for_sqlite(content: str) -> str:
    lines = content.splitlines()
    updated: list[str] = []
    seen: set[str] = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated.append(line)
            continue
        key, _value = line.split("=", 1)
        key = key.strip()
        if key in TARGETS:
            updated.append(f"{key}={TARGETS[key]}")
            seen.add(key)
        else:
            updated.append(line)

    for key, value in TARGETS.items():
        if key not in seen:
            updated.append(f"{key}={value}")

    output = "\n".join(updated)
    if not output.endswith("\n"):
        output += "\n"
    return output
