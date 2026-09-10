import re
from services.vector_store_service import chroma_client, COLLECTION_NAME


def score_by_keywords(text, query):
    r"""
    Score text based on legal/edital keyword patterns.

    Returns score 0-1 where:
    - 0 = no keyword matches
    - 1 = multiple patterns match

    Patterns checked:
    - "documentos? obrigat[óo]rios?"
    - "documentação? exigida?"
    - "anexo [IViv]+"
    - Numbered lists: "^\d+\)"
    - Lettered lists: "^[a-z]\)"
    - Query phrase appearing verbatim (double weight)
    """
    patterns = [
        r"documentos?\s+obrigat[óo]rios?",
        r"documentação?\s+exigida?",
        r"anexo\s+[IViv]+",
        r"(?:^|\n)\d+\)\s+",      # "1) ..."
        r"(?:^|\n)[a-z]\)\s+",    # "a) ..."
    ]

    matches = 0
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            matches += 1

    # Bonus: query phrase appears verbatim (2x weight)
    if query.lower() in text.lower():
        matches += 2

    # Normalize to 0-1
    return min(matches / 5, 1.0)


def is_numbered_list(text):
    """Check if text looks like a numbered/lettered list."""
    list_items = re.findall(
        r'(?:^|\n)(?:\d+\)|[a-z]\))\s+',
        text,
        re.MULTILINE
    )
    return len(list_items) >= 3


def hybrid_search(query, top_k=4):
    """
    Hybrid search combining semantic similarity + keyword matching + heuristics.

    Phase 1: Semantic similarity
    - Use ChromaDB to find top-10 most similar chunks

    Phase 2: Keyword scoring
    - Score each chunk by legal/edital patterns

    Phase 3: Ranking
    - Combine scores: 50% semantic + 35% keyword + 15% list bonus
    - Return top-k by combined score

    Args:
        query: Search query (e.g., "Documentos obrigatórios")
        top_k: Number of chunks to return (default 4)

    Returns:
        List of chunk texts, ranked by hybrid score
    """
    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception:
        return []

    # Phase 1: Semantic search (top-10)
    try:
        results = collection.query(
            query_texts=[query],
            n_results=10,
            include=["documents", "distances"]
        )
    except Exception:
        return []

    if not results or not results.get("documents"):
        return []

    documents = results["documents"][0]
    distances = results["distances"][0]

    # Phase 2 & 3: Score and rank
    scored_chunks = []

    for chunk_text, distance in zip(documents, distances):
        # Convert distance to similarity (ChromaDB uses distance metric)
        semantic_score = 1 - distance

        # Keyword scoring
        keyword_score = score_by_keywords(chunk_text, query)

        # List bonus (15% weight if looks like a list)
        list_bonus = 0.15 if is_numbered_list(chunk_text) else 0

        # Combine scores with weights
        final_score = (
            semantic_score * 0.50 +    # 50% semantic
            keyword_score * 0.35 +      # 35% keywords
            list_bonus                  # 15% list bonus
        )

        scored_chunks.append((chunk_text, final_score))

    # Sort by score descending, return top-k
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in scored_chunks[:top_k]]
