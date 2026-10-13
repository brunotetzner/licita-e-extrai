from pathlib import Path

from flask import Blueprint, jsonify, request

from services.licitacao_service import (
    analisar_pdf,
    analizar_licitacao_por_id,
    get_licitacoes,
    listar_licitacoes_guardadas,
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
        resultado = analizar_licitacao_por_id(numero_controle_pncp)
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


@licitacao_controller.post("/analisar")
def analisar_pdf_route():
    """
    Recebe um PDF via upload, delega ao serviço RAG e retorna as respostas.
    Espera um multipart/form-data com o campo 'pdf' contendo o arquivo
    e um campo opcional 'perguntas' (JSON array de strings).
    """
    if "pdf" not in request.files:
        return jsonify({"erro": "Campo 'pdf' é obrigatório."}), 400

    pdf_file = request.files["pdf"]
    if pdf_file.filename == "":
        return jsonify({"erro": "Nenhum arquivo enviado."}), 400

    temp_path = Path("/tmp") / pdf_file.filename
    pdf_file.save(str(temp_path))

    perguntas_raw = request.form.get("perguntas")
    perguntas: list[str] | None = None
    if perguntas_raw:
        import json
        perguntas = json.loads(perguntas_raw)

    try:
        respostas = analisar_pdf(str(temp_path), perguntas)
        return jsonify({"respostas": respostas})
    finally:
        if temp_path.exists():
            temp_path.unlink()

