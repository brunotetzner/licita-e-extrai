from flask import Blueprint, jsonify, request
from unstructured.partition.pdf import partition_pdf

bp = Blueprint("hello", __name__)


@bp.get("/hello")
def hello():
    return jsonify(message="Hello, World!")


@bp.post("/extract")
def extract():
    # 1. Valida se o arquivo foi enviado na requisição
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado. Envie no campo 'file'."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado."}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "O arquivo enviado precisa ser um PDF."}), 400

    try:
        # 2. Passa o stream do arquivo diretamente para o Unstructured via parâmetro 'file'
        print('aqui')
        elements = partition_pdf(
            file=file,
            strategy="fast",
            infer_table_structure=True,
            extract_images_in_pdf=False
        )
        print('aqui 2')


        # 3. Estrutura o resultado simples para resposta da API
        resultado = [
            {
                "type": el.category,
                "text": el.text,
                "html": el.metadata.text_as_html if el.category == "Table" else None
            }
            for el in elements
        ]

        print('aqui 3')

        return jsonify({
            "message": "PDF processado com sucesso",
            "total_elementos": len(resultado),
            "data": resultado
        }), 200

    except Exception as e:
        return jsonify({"error": f"Erro ao processar PDF: {str(e)}"}), 500