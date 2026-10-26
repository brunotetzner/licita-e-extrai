import threading
from pathlib import Path

from flask import Blueprint, jsonify, request

from services.licitacao_service import (
    analisar_pdf,
    analizar_licitacao_por_id,
    get_licitacoes,
    listar_licitacoes_guardadas,
    processar_resumo_edital,
)


licitacao_controller = Blueprint("licitacao", __name__, url_prefix="/licitacoes")


@licitacao_controller.post("")
def listar_licitacoes():
    return jsonify(get_licitacoes())


@licitacao_controller.get("")
def listar_licitacoes_guardadas_route():
    """
    GET /licitacoes/

    Lista licitacoes guardadas no MongoDB com paginacao e filtro opcional
    por numero de controle PNCP.

    Query params:
        page: Numero de pagina (default 1).
        page_size: Tamano da pagina (default 10, max 100).
        id: Numero de controle PNCP para filtrar.
    """
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    try:
        page_size = int(request.args.get("page_size", 10))
    except ValueError:
        page_size = 10

    numero_controle = request.args.get("id") or None

    return jsonify(
        listar_licitacoes_guardadas(
            page=page,
            page_size=page_size,
            numero_controle_pncp=numero_controle,
        )
    )


@licitacao_controller.post("/analisar/<path:numero_controle_pncp>")
def analizar_licitacao_route(numero_controle_pncp: str):
    """
    POST /licitacoes/analisar/<numero_controle_pncp>

    Busca a licitacao no PNCP pelo numero de control, analiza seus editais
    e retorna o resultado.
    """
    try:
        resultado = analizar_licitacao_por_id(
            numero_controle_pncp,
            authorization=request.headers.get("Authorization"),
        )
    except ValueError as error:
        return jsonify({"erro": str(error)}), 400

    if resultado is None:
        return (
            jsonify(
                {
                    "erro": (
                        f"Licitacao {numero_controle_pncp} nao encontrada "
                        "no PNCP ou sem editais."
                    )
                }
            ),
            404,
        )

    return jsonify(resultado)


@licitacao_controller.post("/processar-resumo")
def processar_resumo_route():
    """
    POST /licitacoes/processar-resumo

    Endpoint interno para processar o resumo do edital de forma assincrona.
    Recebe os dados da licitacao e arquivo, dispara o processamento em
    background e retorna 202 (Accepted) imediatamente.

    JSON body:
        numero_controle_pncp: str (obrigatorio)
        licitacao: dict (obrigatorio)
        arquivo: dict (obrigatorio)
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisicao deve ser JSON."}), 400

    if not all(k in dados for k in ("numero_controle_pncp", "licitacao", "arquivo")):
        return jsonify(
            {
                "erro": (
                    "Campos obrigatorios: "
                    "'numero_controle_pncp', 'licitacao', 'arquivo'."
                )
            }
        ), 400

    # Dispara o processamento em uma thread separada para nao bloquear
    thread = threading.Thread(
        target=processar_resumo_edital,
        args=(dados,),
        daemon=True,
    )
    thread.start()

    return jsonify({"status": "processamento iniciado"}), 202
