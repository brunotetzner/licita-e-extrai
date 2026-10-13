from __future__ import annotations

import os


def _getenv_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _getenv_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


PNCP_API_URL: str = _getenv_str("PNCP_API_URL", "https://pncp.gov.br/api")
REQUEST_TIMEOUT_SECONDS: int = _getenv_int("REQUEST_TIMEOUT_SECONDS", 30)
PNCP_COOKIE: str = _getenv_str("PNCP_COOKIE", "")