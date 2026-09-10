import os
from openai import OpenAI


def get_openrouter_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )


def generate_rag_response(user_prompt: str, context_chunks: list) -> str:
    client = get_openrouter_client()

    if context_chunks:
        context_str = "\n\n---\n\n".join(context_chunks)
    else:
        context_str = "Nenhum contexto relevante foi encontrado no relatório enviado."

    print(context_str)
    prompt = f"""
Você é um assistente técnico especializado em analisar relatórios e documentos.
Responda à solicitação do usuário utilizando estritamente as informações fornecidas no contexto abaixo.

CONTEXTO DO RELATÓRIO:
{context_str}

SOLICITAÇÃO DO USUÁRIO:
{user_prompt}
"""

    response = client.chat.completions.create(
        model=os.getenv("OPENROUTER_MODEL") or 'deepseek/deepseek-v4-flash',
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        extra_headers={
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "PDF RAG API",
        }
    )

    return response.choices[0].message.content