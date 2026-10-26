from __future__ import annotations

import math
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from repositories.config import (
    MONGO_COLLECTION_VETORES_PREFIX,
    MONGO_DATABASE,
    MONGO_URI,
)


def _nome_collection(sufixo: str) -> str:
    return f"{MONGO_COLLECTION_VETORES_PREFIX}_{sufixo}"


def _get_collection(sufixo: str) -> tuple[Collection, MongoClient]:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5_000)
    return client[MONGO_DATABASE][_nome_collection(sufixo)], client


def salvar_vetores(
    sufixo: str, textos: list[str], vetores: list[list[float]]
) -> None:
    if len(textos) != len(vetores):
        raise ValueError("Cada chunk deve possuir exatamente um vetor.")

    collection, client = _get_collection(sufixo)
    try:
        for inicio in range(0, len(textos), 100):
            documentos = []
            for texto, vetor in zip(
                textos[inicio : inicio + 100], vetores[inicio : inicio + 100]
            ):
                normalizado = _normalizar(vetor)
                if normalizado is None:
                    raise ValueError("Embedding com norma zero não é válido.")
                documentos.append({"text": texto, "vector": normalizado})
            if documentos:
                collection.insert_many(documentos)
    finally:
        client.close()


def buscar_similares(
    sufixo: str, query_vector: list[float], k: int = 3
) -> list[str]:
    normalizado = _normalizar(query_vector)
    if normalizado is None:
        raise ValueError("Embedding da consulta com norma zero.")

    collection, client = _get_collection(sufixo)
    try:
        pipeline: list[dict[str, Any]] = [
            {
                "$addFields": {
                    "score": {
                        "$reduce": {
                            "input": {
                                "$zip": {
                                    "inputs": ["$vector", normalizado],
                                }
                            },
                            "initialValue": 0.0,
                            "in": {
                                "$add": [
                                    "$$value",
                                    {
                                        "$multiply": [
                                            {"$arrayElemAt": ["$$this", 0]},
                                            {"$arrayElemAt": ["$$this", 1]},
                                        ]
                                    },
                                ]
                            },
                        }
                    }
                }
            },
            {"$sort": {"score": -1}},
            {"$limit": k},
            {"$project": {"_id": 0, "text": 1}},
        ]
        return [
            documento["text"]
            for documento in collection.aggregate(pipeline)
            if "text" in documento
        ]
    finally:
        client.close()


def excluir_vetores(sufixo: str) -> None:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5_000)
    try:
        client[MONGO_DATABASE].drop_collection(_nome_collection(sufixo))
    finally:
        client.close()


def _normalizar(vetor: list[float]) -> list[float] | None:
    norma = math.sqrt(sum(valor * valor for valor in vetor))
    if norma == 0:
        return None
    return [valor / norma for valor in vetor]
