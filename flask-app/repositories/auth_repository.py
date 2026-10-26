from __future__ import annotations

from typing import Any, TypedDict

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.results import InsertOneResult

from repositories.config import (
    MONGO_COLLECTION_USUARIOS,
    MONGO_DATABASE,
    MONGO_URI,
)


class UsuarioDocumento(TypedDict, total=False):
    """Documento de usuário salvo no MongoDB."""

    _id: str
    email: str
    senha: str
    criado_em: str


def _get_collection() -> tuple[Collection, MongoClient]:
    """Retorna a collection 'usuarios' do MongoDB."""
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5_000,
    )
    db = client[MONGO_DATABASE]
    return db[MONGO_COLLECTION_USUARIOS], client


def salvar_usuario(email: str, senha_hash: str) -> UsuarioDocumento | None:
    """
    Cria um usuário no MongoDB.

    Args:
        email: Email do usuário (único).
        senha_hash: Hash da senha (nunca a senha em texto puro).

    Returns:
        Dict com '_id', 'email' e 'senha' (hash), ou None se já existir
        um usuário com o mesmo email.
    """
    try:
        collection, client = _get_collection()
        collection.create_index("email", unique=True)

        resultado: InsertOneResult = collection.insert_one(
            {"email": email, "senha": senha_hash}
        )
        client.close()

        return {
            "_id": str(resultado.inserted_id),
            "email": email,
            "senha": senha_hash,
        }
    except DuplicateKeyError:
        print(f"Email {email} já cadastrado.")
        client.close()
        return None
    except PyMongoError as error:
        print(f"Erro ao salvar usuário {email}: {error}")
        client.close()
        return None


def buscar_usuario_por_email(email: str) -> UsuarioDocumento | None:
    """
    Busca um usuário pelo email.

    Args:
        email: Email do usuário.

    Returns:
        O documento do usuário ou None se não existir.
    """
    try:
        collection, client = _get_collection()
        documento: dict[str, Any] | None = collection.find_one(
            {"email": email}
        )
        client.close()
        if documento is None:
            return None
        return UsuarioDocumento(
            _id=str(documento["_id"]),
            email=documento.get("email", ""),
            senha=documento.get("senha", ""),
        )
    except PyMongoError as error:
        print(f"Erro ao buscar usuário {email}: {error}")
        return None