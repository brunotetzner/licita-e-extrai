from flask import Blueprint, jsonify, request

from services.auth_service import criar_conta, login


auth_controller = Blueprint("auth", __name__, url_prefix="/auth")


#disabled for production
# @auth_controller.post("/criar-conta")
# def criar_conta_route():
#     """
#     POST /auth/criar-conta

#     Cria uma nova conta de usuário.

#     JSON body:
#         email: str (obrigatorio)
#         senha: str (obrigatorio)
#     """
#     dados = request.get_json(silent=True)
#     if not dados:
#         return jsonify({"erro": "Corpo da requisicao deve ser JSON."}), 400

#     email = dados.get("email")
#     senha = dados.get("senha")
#     if not email or not senha:
#         return jsonify({"erro": "Campos 'email' e 'senha' sao obrigatorios."}), 400

#     resultado = criar_conta(email, senha)
#     if resultado is None:
#         return (
#             jsonify(
#                 {
#                     "erro": (
#                         "Nao foi possivel criar a conta. "
#                         "Verifique se o email ja esta cadastrado."
#                     )
#                 }
#             ),
#             409,
#         )

#     return jsonify(resultado), 201


@auth_controller.post("/login")
def login_route():
    """
    POST /auth/login

    Autentica um usuário e retorna um token JWT.

    JSON body:
        email: str (obrigatorio)
        senha: str (obrigatorio)
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisicao deve ser JSON."}), 400

    email = dados.get("email")
    senha = dados.get("senha")
    if not email or not senha:
        return jsonify({"erro": "Campos 'email' e 'senha' sao obrigatorios."}), 400

    resultado = login(email, senha)
    if resultado is None:
        return (
            jsonify({"erro": "Credenciais invalidas."}),
            401,
        )

    return jsonify(resultado)