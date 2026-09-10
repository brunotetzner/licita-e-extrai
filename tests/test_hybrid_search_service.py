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
