import os
from uuid import uuid4

from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI

from repositories.vetores_repository import (
    buscar_similares,
    excluir_vetores,
    salvar_vetores,
)

DEFAULT_QUESTIONS = [
    "Liste cada item do termo de referência com sua descrição, unidade de medida, "
    "quantidade E o valor unitário e o valor total estimado de cada item. "
    "Apresente no formato: 'Item XX - quantidade: N unidades, valor unitário R$ ..., "
    "valor total R$ ...'. Se algum valor não estiver explícito no documento, indique "
    "explicitamente que não foi localizado.",
    "Quais são os prazos de entrega dos produtos/serviços e de vigência do contrato, "
    "incluindo as condições para eventual prorrogação?",
    "Qual a descrição do objeto e quais as obrigações específicas da contratada? "
    "Informe também todas as exigências de habilitação técnica e econômico-financeira "
    "previstas no edital/termo de referência, enumerando documentos, comprovações, "
    "índices ou valores exigidos e indicando o item/cláusula correspondente. "
    "Se alguma categoria não tiver exigências específicas, informe isso claramente.",
    "Há exigência de prova de conceito, amostra ou protótipo antes da contratação?",
    "É exigida garantia contratual? O modelo de contratação/entrega é integral, "
    "parcelado, por estimativa ou registro de preços?",
]


def process_pdf(pdf_path: str, questions: list[str] | None = None) -> list[str]:
    """
    Carrega um PDF, cria embeddings e vectorstore, configura um agente RAG
    e executa um loop de perguntas, retornando as respostas.

    Args:
        pdf_path: Caminho para o arquivo PDF.
        questions: Lista de perguntas a serem respondidas.
                   Se None, usa DEFAULT_QUESTIONS.

    Returns:
        list[str]: Lista de respostas geradas pelo agente.
    """
    if questions is None:
        questions = DEFAULT_QUESTIONS

    # 1. Preparar o carregador, splitter e embeddings
    print(f"Carregando PDF de {pdf_path}...")
    loader = PyPDFLoader(file_path=pdf_path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100
    )
    embeddings = OpenAIEmbeddings(
        model="openai/text-embedding-3-small",
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    # Processa uma página por vez para não manter o texto completo do PDF na RAM.
    sufixo = uuid4().hex
    total_chunks = 0
    try:
        for pagina in loader.lazy_load():
            chunks = splitter.split_documents([pagina])
            if not chunks:
                continue
            vetores = embeddings.embed_documents(
                [chunk.page_content for chunk in chunks]
            )
            salvar_vetores(
                sufixo,
                [chunk.page_content for chunk in chunks],
                vetores,
            )
            total_chunks += len(chunks)

        if total_chunks == 0:
            raise ValueError(f"Nenhum texto extraível encontrado em {pdf_path}.")

        print(f"Chunks processados: {total_chunks}.")

        # 2. Ferramenta de busca: cada consulta traz apenas os top-k trechos.
        @tool
        def search_documents(query: str) -> str:
            """Busca trechos relevantes no PDF para a consulta."""
            query_vector = embeddings.embed_query(query)
            docs = buscar_similares(sufixo, query_vector, k=3)
            if not docs:
                return "Nenhum documento encontrado."
            return "\n\n---\n\n".join(docs)

        system_prompt = (
            "Você é um assistente especializado em análise de documentos. "
            "Use a ferramenta search_documents para consultar o PDF antes de "
            "responder perguntas. Sempre cite trechos relevantes quando possível."
        )
        llm = ChatOpenAI(
            model="deepseek/deepseek-v4-flash",
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        agent = create_agent(
            model=llm,
            tools=[search_documents],
            system_prompt=system_prompt,
        )

        responses: list[str] = []
        for question in questions:
            print(f"\n{'=' * 60}")
            print(f"Pergunta: {question}")
            response = agent.invoke(
                {"messages": [HumanMessage(content=question)]}
            )
            answer = response["messages"][-1].content
            print(f"Resposta: {answer}")
            responses.append(answer)
        return responses
    finally:
        excluir_vetores(sufixo)
