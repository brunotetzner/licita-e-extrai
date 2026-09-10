import chromadb
from chromadb.utils import embedding_functions

# Cliente em memória (ou substitua por PersistentClient se quiser salvar em disco)
chroma_client = chromadb.Client()
default_ef = embedding_functions.DefaultEmbeddingFunction()
COLLECTION_NAME = "pdf_docs"


def reset_and_index_chunks(chunks):
    """Deleta o banco vetorial anterior se existir e reescreve com os novos chunks."""
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass  # Coleção ainda não existia

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=default_ef
    )

    if not chunks:
        return

    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [f"id_{i}" for i in range(len(chunks))]

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )


def search_similar_chunks(query: str, top_k: int = 4):
    """Recupera os chunks mais relevantes para o prompt informado."""
    try:
        collection = chroma_client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=default_ef
        )
        results = collection.query(query_texts=[query], n_results=top_k)
        if results and results.get("documents"):
            return results["documents"][0]
        return []
    except Exception:
        return []