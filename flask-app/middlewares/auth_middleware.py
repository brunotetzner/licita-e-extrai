from __future__ import annotations

from typing import Any

import jwt
from flask import jsonify, request

from controllers.licitacao_controller import licitacao_controller
from repositories.config import JWT_SECRET_KEY


def _extrair_token() -> str | None:
    """
    Extrai o token do header Authorization no formato 'Bearer <token>'.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header[len("Bearer "):].strip() or None


@licitacao_controller.before_request
def validar_token():
    """
    Middleware que valida o token JWT em todas as rotas do
    licitacao_controller.

    Aplica-se a qualquer requisição a /licitacoes/*. Se o token for
    inválido, ausente ou expirado, retorna 401.
    """
    if request.method == "OPTIONS":
        return None

    token = _extrair_token()
    if token is None:
        return jsonify({"erro": "Token ausente. Envie 'Authorization: Bearer <token>'."}), 401

    try:
        payload: dict[str, Any] = jwt.decode(
            token, JWT_SECRET_KEY, algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        return jsonify({"erro": "Token expirado."}), 401
    except jwt.InvalidTokenError:
        return jsonify({"erro": "Token invalido."}), 401

    # Armazena o usuário autenticado para uso nas rotas.
    request.usuario = payload
    return None


def obter_usuario_atual() -> dict[str, Any] | None:
    """
    Retorna o payload do usuário autenticado na requisição atual.

    O payload é definido pelo middleware validar_token em request.usuario.
    """
    return getattr(request, "usuario", None)