import pytest
from unittest.mock import patch, MagicMock
from services.structured_chunker_service import create_structured_chunks, is_section_header
from services.hybrid_search_service import hybrid_search


def test_creates_chunks_from_elements():
    """Test basic chunking."""
    elements = [
        {"type": "Text", "text": "1. ARTIGOS", "html": None},
        {"type": "Text", "text": "Blah blah blah", "html": None},
        {"type": "Text", "text": "2. DOCUMENTOS", "html": None},
        {"type": "Text", "text": "1) CPF\n2) Contrato", "html": None},
    ]

    chunks = create_structured_chunks(elements)

    assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
    assert chunks[0]["metadata"]["type"] == "section"
    assert chunks[0]["metadata"]["section_name"] == "1. ARTIGOS"
    assert "Blah blah blah" in chunks[0]["text"]
    assert chunks[1]["metadata"]["section_name"] == "2. DOCUMENTOS"


def test_preserves_tables_as_separate_chunks():
    """Test that tables are not merged with text sections."""
    elements = [
        {"type": "Text", "text": "Section 1", "html": None},
        {"type": "Table", "text": "Table content", "html": "<table><tr><td>Data</td></tr></table>"},
        {"type": "Text", "text": "Section 2", "html": None},
    ]

    chunks = create_structured_chunks(elements)

    assert len(chunks) == 3
    assert chunks[0]["metadata"]["type"] == "section"
    assert chunks[1]["metadata"]["type"] == "table"
    assert chunks[2]["metadata"]["type"] == "section"
    assert "[TABELA" in chunks[1]["text"]


def test_detects_section_headers():
    """Test header detection heuristics."""
    assert is_section_header({"type": "Text", "text": "1. DOCUMENTOS OBRIGATÓRIOS", "html": None})
    assert is_section_header({"type": "Text", "text": "ARTIGO 5", "html": None})
    assert is_section_header({"type": "Text", "text": "II. REQUISITOS", "html": None})
    assert not is_section_header({"type": "Text", "text": "This is a very long sentence that is definitely not a header because it exceeds 100 characters and spans multiple clauses and concepts.", "html": None})
    assert not is_section_header({"type": "Text", "text": "lowercase header", "html": None})


def test_does_not_split_lists_in_middle():
    """Test that numbered lists stay together in one chunk."""
    elements = [
        {"type": "Text", "text": "2. DOCUMENTOS OBRIGATÓRIOS", "html": None},
        {"type": "Text", "text": "1) CPF do responsável\n2) Contrato Social\n3) Prova de Patrimônio\n4) Certidão de Regularidade Fiscal\n5) Comprovante de Experiência", "html": None},
    ]

    chunks = create_structured_chunks(elements)

    # Should be 1 chunk (header + list together)
    assert len(chunks) == 1
    # List should not be split
    assert "CPF do responsável" in chunks[0]["text"]
    assert "Prova de Patrimônio" in chunks[0]["text"]
    assert "5) Comprovante" in chunks[0]["text"]


def test_handles_preamble_text_before_first_header():
    """Test that text appearing before the first recognized header does not
    crash ChromaDB indexing by leaving section_name as None."""
    elements = [
        {"type": "Text", "text": "Título do edital\nPreâmbulo com informações gerais", "html": None},
        {"type": "Text", "text": "1. ARTIGOS", "html": None},
        {"type": "Text", "text": "Conteúdo...", "html": None},
    ]

    chunks = create_structured_chunks(elements)

    assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
    assert chunks[0]["metadata"]["section_name"] == "SEM SEÇÃO"
    assert chunks[1]["metadata"]["section_name"] == "1. ARTIGOS"

    # No metadata value should ever be None (ChromaDB cannot store None)
    for chunk in chunks:
        for value in chunk["metadata"].values():
            assert value is not None


def test_does_not_split_dotted_numbering():
    """Test that dotted subsection numbering (e.g. '1.1.', '1.2.') is not
    misclassified as its own section header. In real PDF extraction each
    list item typically arrives as its own element, so each of "1.1. CPF",
    "1.2. RG", "1.3. Comprovante de residência" must NOT be treated as a
    fresh header, otherwise a 3-item list gets fragmented into 3 separate
    one-line chunks (the exact bug from the spec, e.g. "1.3.4. Eventuais
    anexos...")."""
    elements = [
        {"type": "Text", "text": "2. DOCUMENTOS OBRIGATÓRIOS", "html": None},
        {"type": "Text", "text": "1.1. CPF", "html": None},
        {"type": "Text", "text": "1.2. RG", "html": None},
        {"type": "Text", "text": "1.3. Comprovante de residência", "html": None},
    ]

    chunks = create_structured_chunks(elements)

    # Header + all list items should be kept together as ONE chunk, not
    # fragmented into 4 (one per line).
    assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}: {chunks}"
    assert chunks[0]["metadata"]["section_name"] == "2. DOCUMENTOS OBRIGATÓRIOS"

    list_chunk_text = chunks[0]["text"]
    assert "1.1. CPF" in list_chunk_text
    assert "1.2. RG" in list_chunk_text
    assert "1.3. Comprovante de residência" in list_chunk_text


@patch("services.hybrid_search_service.chroma_client")
def test_dotted_numbering_list_retrieved_as_single_result_via_hybrid_search(mock_chroma):
    """End-to-end style check: once chunked correctly, hybrid_search should
    surface the complete dotted-numbering list as a single result rather than
    3 separate fragments."""
    elements = [
        {"type": "Text", "text": "2. DOCUMENTOS OBRIGATÓRIOS", "html": None},
        {"type": "Text", "text": "1.1. CPF", "html": None},
        {"type": "Text", "text": "1.2. RG", "html": None},
        {"type": "Text", "text": "1.3. Comprovante de residência", "html": None},
    ]

    chunks = create_structured_chunks(elements)
    assert len(chunks) == 1

    mock_collection = MagicMock()
    mock_chroma.get_collection.return_value = mock_collection
    mock_collection.query.return_value = {
        "documents": [[chunk["text"] for chunk in chunks]],
        "distances": [[0.1]],
    }

    results = hybrid_search("Documentos obrigatórios", top_k=1)

    assert len(results) == 1
    assert "1.1. CPF" in results[0]
    assert "1.2. RG" in results[0]
    assert "1.3. Comprovante de residência" in results[0]
