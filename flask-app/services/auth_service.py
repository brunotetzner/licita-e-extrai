from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from repositories.auth_repository import (
    UsuarioDocumento,
    buscar_usuario_por_email,
    salvar_usuario,
)
from repositories.config import JWT_EXPIRACAO_SEGUNDOS, JWT_SECRET_KEY


def _gerar_token(usuario: UsuarioDocumento) -> str:
    """
    Gera um token JWT assinado com a chave secreta.

    Args:
        usuario: Documento do usuário (precisa de '_id' e 'email').

    Returns:
        Token JWT codificado.
    """
    payload = {
        "id": usuario["_id"],
        "email": usuario["email"],
        "exp": datetime.now(timezone.utc) + timedelta(seconds=JWT_EXPIRACAO_SEGUNDOS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def _sanitizar_usuario(usuario: UsuarioDocumento) -> dict:
    """Remove a senha (hash) do documento para não expor no JSON."""
    return {"id": usuario["_id"], "email": usuario["email"]}


def criar_conta(email: str, senha: str) -> dict | None:
    """
    Cria uma nova conta de usuário.

    Args:
        email: Email do usuário.
        senha: Senha em texto puro (será hasheada antes de salvar).

    Returns:
        Dict com usuário sanitizado + token JWT, ou None se o email
        já estiver cadastrado.
    """
    email = email.strip().lower()
    if not email or not senha:
        return None

    senha_hash = generate_password_hash(senha)
    usuario = salvar_usuario(email, senha_hash)
    if usuario is None:
        return None

    token = _gerar_token(usuario)
    return {"usuario": _sanitizar_usuario(usuario), "token": token}


def login(email: str, senha: str) -> dict | None:
    """
    Autentica um usuário e retorna um token JWT.

    Args:
        email: Email do usuário.
        senha: Senha em texto puro.

    Returns:
        Dict com usuário sanitizado + token JWT, ou None se as credenciais
        forem inválidas.
    """
    email = email.strip().lower()
    usuario = buscar_usuario_por_email(email)
    if usuario is None:
        return None

    if not check_password_hash(usuario["senha"], senha):
        return None

    token = _gerar_token(usuario)
    return {"usuario": _sanitizar_usuario(usuario), "token": token}