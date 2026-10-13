from flask import jsonify, request

from controllers.licitacao_controller import licitacao_controller
from services.licitacao_service import listar_licitacoes_guardadas


def register_routes(app):
    app.register_blueprint(licitacao_controller)

    @app.get("/")
    def raiz():
        """
        GET /

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