from __future__ import annotations

import os


def _getenv_str(name: str, default: str) -> str:
    return os.getenv(name, default)


MONGO_URI: str = _getenv_str("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE: str = _getenv_str("MONGO_DATABASE", "licitacoes_db")
MONGO_COLLECTION_LICITACOES: str = _getenv_str(
    "MONGO_COLLECTION_LICITACOES", "licitacoes"
)

SERVERLESS_LICITATION_SUMMARY_ENABLED: bool = os.getenv(
    "SERVERLESS_LICITATION_SUMMARY_ENABLED", "false"
).strip().lower() in ("1", "true", "yes", "on")
SERVERLESS_LICITATION_SUMMARY_URL: str = _getenv_str(
    "SERVERLESS_LICITATION_SUMMARY_URL", ""
)