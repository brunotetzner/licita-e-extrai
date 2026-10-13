import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()

DEFAULT_QUESTIONS = [
    "Quais são as especificações técnicas e quantitativos mínimos exigidos no termo de referência?",
    "Qual o prazo de entrega dos produtos/serviços estabelecido no edital?",
    "Qual o prazo de vigência do contrato e as condições para prorrogação?",
    "Qual a descrição do objeto e quais as obrigações específicas da contratada para o cumprimento do contrato?",
    "Há exigência de prova de conceito, amostra ou protótipo antes da contratação?",
    "É exigida garantia contratual? O modelo de entrega é integral, parcelado, por estimativa ou registro de preços?"

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

    # 1. Carregar o PDF
    print(f"Carregando PDF de {pdf_path}...")
    loader = PyPDFLoader(file_path=pdf_path)
    documents = loader.load()

    # 2. Dividir em chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100
    )
    chunks = splitter.split_documents(documents)

    print(f"Loaded {len(documents)} document(s), {len(chunks)} chunks.")

    # 3. Embeddings via OpenRouter
    embeddings = OpenAIEmbeddings(
        model="openai/text-embedding-3-small",
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    # 4. Vectorstore FAISS
    vectorstore = FAISS.from_documents(chunks, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 5. Ferramenta de busca
    @tool
    def search_documents(query: str) -> str:
        """
        Busca documentos no PDF com base na query e retorna os resultados.

        Args:
            query: Termo de busca fornecido pelo usuário.

        Returns:
            str: Conteúdos encontrados ou mensagem de vazio.
        """
        docs = retriever.invoke(query)
        if not docs:
            return "Nenhum documento encontrado."
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    # 6. Prompt de sistema
    system_prompt = (
        "Você é um assistente especializado em análise de documentos. "
        "Use a ferramenta search_documents para consultar o PDF antes de "
        "responder perguntas. Sempre cite trechos relevantes quando possível."
    )

    # 7. LLM e agente
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

    # 8. Loop de perguntas
    responses: list[str] = []
    for question in questions:
        print(f"\n{'=' * 60}")
        print(f"Pergunta: {question}")

        response = agent.invoke({"messages": [HumanMessage(content=question)]})
        answer = response["messages"][-1].content
        print(f"Resposta: {answer}")
        responses.append(answer)

    return responses
