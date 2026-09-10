import pytest
from services.structured_chunker_service import create_structured_chunks, is_section_header


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
