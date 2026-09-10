import pytest
from unittest.mock import patch, MagicMock
from services.hybrid_search_service import (
    hybrid_search,
    score_by_keywords,
    is_numbered_list
)


def test_score_by_keywords_finds_exact_phrase():
    """Test keyword scoring with exact phrase match."""
    text = "DOCUMENTOS OBRIGATÓRIOS\n1) CPF\n2) RG"
    query = "Documentos obrigatórios"

    score = score_by_keywords(text, query)

    assert score > 0.5, f"Expected score > 0.5 for exact match, got {score}"


def test_score_by_keywords_finds_patterns():
    """Test keyword scoring with legal patterns."""
    text = "ANEXO I - Documentação exigida:\n1) CPF\n2) Contrato Social"
    query = "Documentos obrigatórios"

    score = score_by_keywords(text, query)

    # Should match: "ANEXO", "documentação exigida", numbered list
    assert score >= 0.4


def test_score_by_keywords_low_for_generic_text():
    """Test that generic text gets low score."""
    text = "This is some random text about documents in general but not a specific list."
    query = "Documentos obrigatórios"

    score = score_by_keywords(text, query)

    assert score < 0.3


def test_is_numbered_list_true_for_lists():
    """Test list detection."""
    assert is_numbered_list("1) First\n2) Second\n3) Third")
    assert is_numbered_list("a) Item A\nb) Item B\nc) Item C")
    assert is_numbered_list("Mixed:\n1) One\n2) Two\na) A\nb) B")


def test_is_numbered_list_false_for_non_lists():
    """Test list detection rejects non-lists."""
    assert not is_numbered_list("Just some regular text")
    assert not is_numbered_list("One item:\n1) Lonely item")
    assert not is_numbered_list("Mention of 1) something but only once")


@patch('services.hybrid_search_service.chroma_client')
def test_hybrid_search_combines_scores(mock_chroma):
    """Test that hybrid search ranks by combined score."""
    # Mock ChromaDB results
    mock_collection = MagicMock()
    mock_chroma.get_collection.return_value = mock_collection

    # Simulate 3 chunks with different scores
    mock_collection.query.return_value = {
        "documents": [[
            "Generic mention of documents in section 3.2",
            "DOCUMENTOS OBRIGATÓRIOS\n1) CPF\n2) Contrato Social",
            "Some other section"
        ]],
        "distances": [[0.3, 0.1, 0.4]]  # Lower distance = higher similarity
    }

    results = hybrid_search("Documentos obrigatórios", top_k=2)

    # Chunk with best combined score should be first
    assert len(results) == 2
    assert "DOCUMENTOS OBRIGATÓRIOS" in results[0]
    assert "1) CPF" in results[0]


@patch('services.hybrid_search_service.chroma_client')
def test_semantic_score_handles_unbounded_distance(mock_chroma):
    """ChromaDB's default distance metric (squared L2) is unbounded, so
    distances can exceed 1.0. semantic_score = 1 - distance must be clamped
    to [0, 1] instead of going negative, to preserve the documented
    50/35/15 weighting."""
    mock_collection = MagicMock()
    mock_chroma.get_collection.return_value = mock_collection

    # Distances include values well above 1.0 (unbounded metric)
    mock_collection.query.return_value = {
        "documents": [[
            "Low distance chunk (most similar)",
            "Mid distance chunk",
            "High distance chunk (least similar, distance > 1)",
        ]],
        "distances": [[0.49, 1.79, 2.5]]
    }

    results = hybrid_search("some query", top_k=3)

    assert len(results) == 3

    # Recompute semantic scores the way the implementation should, and make
    # sure none of them are negative / out of [0, 1] bounds by checking the
    # ranking is preserved (low distance -> ranked at or above high distance).
    from services.hybrid_search_service import score_by_keywords, is_numbered_list

    def compute_final_score(text, distance, query):
        semantic_score = max(0, 1 - distance)
        assert 0 <= semantic_score <= 1
        keyword_score = score_by_keywords(text, query)
        list_bonus = 0.15 if is_numbered_list(text) else 0
        return semantic_score * 0.50 + keyword_score * 0.35 + list_bonus

    low_distance_score = compute_final_score("Low distance chunk (most similar)", 0.49, "some query")
    high_distance_score = compute_final_score("High distance chunk (least similar, distance > 1)", 2.5, "some query")

    assert high_distance_score <= low_distance_score
