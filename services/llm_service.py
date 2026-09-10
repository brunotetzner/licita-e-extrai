import os
from openai import OpenAI


def get_openrouter_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )


def _build_prompt(user_prompt: str, context_chunks: list) -> str:
    """
    Build the full prompt with context and system instructions.

    Detects if query is about "Documentos obrigatórios" and uses specialized prompt.

    Args:
        user_prompt: User's query
        context_chunks: List of context chunks from search

    Returns:
        Full prompt string ready for LLM
    """
    # Join context chunks
    if context_chunks:
        context_str = "\n\n---\n\n".join(context_chunks)
    else:
        context_str = "Nenhum contexto relevante foi encontrado no documento enviado."

    # Detect if this is a "Documentos obrigatórios" query
    is_doc_query = (
        "documento" in user_prompt.lower() and
        "obrigat" in user_prompt.lower()
    )

    if is_doc_query:
        system_prompt = """Você é um especialista em editais de licitação.

Quando perguntado sobre "Documentos Obrigatórios":
1. Procure por seções que listam requisitos documentais
2. Compile uma lista COMPLETA e ordenada
3. Inclua referências a anexos se mencionados (ex: "Anexo I")
4. Separe por categoria se o edital assim o faz

Responda SEMPRE em formato de lista Markdown numerada.
Seja conciso mas completo. Não omita documentos."""
    else:
        system_prompt = """Você é um especialista em documentos jurídicos.
Responda à solicitação do usuário utilizando estritamente as informações do contexto fornecido.
Cite a seção/artigo quando relevante."""

    full_prompt = f"""{system_prompt}

CONTEXTO DO EDITAL:
{context_str}

SOLICITAÇÃO DO USUÁRIO:
{user_prompt}
"""

    return full_prompt


def generate_rag_response(user_prompt: str, context_chunks: list) -> str:
    """
    Generate RAG response using domain-aware prompting.

    Args:
        user_prompt: User's query
        context_chunks: List of context chunks from hybrid search

    Returns:
        LLM response string
    """
    client = get_openrouter_client()

    prompt = _build_prompt(user_prompt, context_chunks)

    response = client.chat.completions.create(
        model=os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-v4-flash",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        extra_headers={
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "PDF RAG API - Editais de Licitação",
        }
    )

    return response.choices[0].message.content
