from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from repositories.config import (
    MONGO_COLLECTION_LICITACOES,
    MONGO_DATABASE,
    MONGO_URI,
)


class LicitacaoDocumento(TypedDict, total=False):
    """Documento completo de licitação salvo no MongoDB."""

    numero_controle_pncp: str
    licitacao: dict[str, Any]
    arquivo: dict[str, Any]
    respostas: list[str]
    resumo_edital: list[str]
    processado_em: str


def _get_collection():
    """Retorna a collection 'licitacoes' do MongoDB."""
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5_000,
    )
    db = client[MONGO_DATABASE]
    return db[MONGO_COLLECTION_LICITACOES], client


def buscar_por_id(numero_controle_pncp: str) -> LicitacaoDocumento | None:
    """
    Busca uma licitação já processada pelo seu número de controle PNCP.

    Args:
        numero_controle_pncp: Identificador único da licitação no PNCP.

    Returns:
        O documento salvo ou None se não existir.
    """
    try:
        collection, client = _get_collection()
        documento = collection.find_one(
            {"numero_controle_pncp": numero_controle_pncp}
        )
        client.close()
        if documento is not None:
            return LicitacaoDocumento(
                numero_controle_pncp=documento.get("numero_controle_pncp", ""),
                licitacao=documento.get("licitacao", {}),
                arquivo=documento.get("arquivo", {}),
                respostas=documento.get("respostas", []),
                processado_em=documento.get("processado_em", ""),
            )
        return None
    except PyMongoError as error:
        print(f"Erro ao buscar licitação {numero_controle_pncp}: {error}")
        return None


def listar_licitacoes(
    *,
    page: int = 1,
    page_size: int = 10,
    numero_controle_pncp: str | None = None,
) -> tuple[list[LicitacaoDocumento], int]:
    """
    Lista licitações guardadas no MongoDB com paginação e filtro opcional.

    Args:
        page: Número de página (1-based).
        page_size: Tamanho da página.
        numero_controle_pncp: Filtro opcional por número de controle PNCP.

    Returns:
        Tupla (documentos, total) onde 'total' é o número total de documentos
        que casam com o filtro (ignorando a paginação).
    """
    filtro: dict[str, Any] = {}
    if numero_controle_pncp:
        filtro["numero_controle_pncp"] = numero_controle_pncp

    try:
        collection, client = _get_collection()
        total = collection.count_documents(filtro)
        cursor = (
            collection.find(filtro)
            .sort("processado_em", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        documentos = [
            LicitacaoDocumento(
                numero_controle_pncp=doc.get("numero_controle_pncp", ""),
                licitacao=doc.get("licitacao", {}),
                arquivo=doc.get("arquivo", {}),
                respostas=doc.get("respostas", []),
                resumo_edital=doc.get("resumo_edital", []),
                processado_em=doc.get("processado_em", ""),
            )
            for doc in cursor
        ]
        client.close()
        return documentos, total
    except PyMongoError as error:
        print(f"Erro ao listar licitações: {error}")
        return [], 0


def salvar_licitacao(documento: LicitacaoDocumento) -> bool:
    """
    Salva (upsert) uma licitação processada no MongoDB.

    Usa 'numero_controle_pncp' como chave única para evitar duplicatas.

    Args:
        documento: Dicionário com os dados da licitação processada.

    Returns:
        True se salvou com sucesso, False caso contrário.
    """
    try:
        collection, client = _get_collection()
        collection.update_one(
            {"numero_controle_pncp": documento["numero_controle_pncp"]},
            {"$set": {**documento, "processado_em": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        client.close()
        return True
    except PyMongoError as error:
        print(f"Erro ao salvar licitação {documento.get('numero_controle_pncp')}: {error}")
        return False