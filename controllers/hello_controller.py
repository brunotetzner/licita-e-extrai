from flask import Blueprint, jsonify, request
from unstructured.partition.pdf import partition_pdf

from services.chunker_service import create_chunks
from services.vector_store_service import reset_and_index_chunks, search_similar_chunks
from services.llm_service import generate_rag_response

bp = Blueprint("hello", __name__)


@bp.get("/hello")
def hello():
    return jsonify(message="Hello, World!")


@bp.post("/extract")
def extract():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado. Envie no campo 'file'."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado."}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "O arquivo enviado precisa ser um PDF."}), 400

    try:
        elements = partition_pdf(
            file=file,
            strategy="fast",
            infer_table_structure=True,
            extract_images_in_pdf=False
        )

        resultado = [
            {
                "type": el.category,
                "text": el.text,
                "html": el.metadata.text_as_html if el.category == "Table" else None
            }
            for el in elements
        ]

        # Processa chunks e reseta o banco vetorial com o novo arquivo
        chunks = create_chunks(resultado)
        reset_and_index_chunks(chunks)

        return jsonify({
            "message": "PDF processado e reindexado com sucesso.",
            "total_elementos": len(resultado),
            "total_chunks": len(chunks)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Erro ao processar PDF: {str(e)}"}), 500


@bp.post("/analyze")
def analyze():
    data = request.get_json() or {}
    default_prompt = "Documentos obrigatórios"
    user_prompt = data.get("prompt") or data.get("question") or default_prompt

    if not user_prompt:
        return jsonify({"error": "O campo 'prompt' é obrigatório no JSON."}), 400

    try:
        # Busca contexto relevante no banco e consulta o DeepSeek
        print(f"Prompt do usuário: {user_prompt}")
        context_chunks = search_similar_chunks(user_prompt, top_k=4)
        ai_response = generate_rag_response(user_prompt, context_chunks)

        return jsonify({
            "prompt": user_prompt,
            "response": ai_response,
            "context_chunks_used": len(context_chunks)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Erro ao analisar o relatório: {str(e)}"}), 500