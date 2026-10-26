from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _getenv_str(name: str, default: str) -> str:
    return os.getenv(name, default)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


MONGO_URI: str = _getenv_str("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE: str = _getenv_str("MONGO_DATABASE", "licitacoes_db")
MONGO_COLLECTION_LICITACOES: str = _getenv_str(
    "MONGO_COLLECTION_LICITACOES", "licitacoes"
)
MONGO_COLLECTION_USUARIOS: str = _getenv_str(
    "MONGO_COLLECTION_USUARIOS", "usuarios"
)
# Prefixo das collections temporárias que guardam os vetores do RAG.
# Uma collection é criada por execução do process_pdf e excluída ao final.
MONGO_COLLECTION_VETORES_PREFIX: str = _getenv_str(
    "MONGO_COLLECTION_VETORES_PREFIX", "vetores_temporarios"
)

JWT_SECRET_KEY: str = _getenv_str(
    "JWT_SECRET_KEY",
    "dev-secret-trocar-em-producao-0123456789abcdef",
)
JWT_EXPIRACAO_SEGUNDOS: int = int(
    _getenv_str("JWT_EXPIRACAO_SEGUNDOS", "3600")
)

ASYNC_LICITATION_SUMMARY_ENABLED: bool = os.getenv(
    "ASYNC_LICITATION_SUMMARY_ENABLED", "false"
).strip().lower() in ("1", "true", "yes", "on")
GITHUB_ACTIONS_TOKEN: str = _getenv_str("GITHUB_ACTIONS_TOKEN", "")
GITHUB_ACTIONS_REPOSITORY: str = _getenv_str(
    "GITHUB_ACTIONS_REPOSITORY", "brunotetzner/licita-e-extrai"
)
GITHUB_ACTIONS_REF: str = _getenv_str("GITHUB_ACTIONS_REF", "main")