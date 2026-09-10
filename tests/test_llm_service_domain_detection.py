import os
import pytest
from unittest.mock import patch, MagicMock
from services.llm_service import generate_rag_response, _build_prompt


def test_detects_documentos_obrigatorios_query():
    """Test that query with 'documento' + 'obrigat' triggers domain detection."""
    user_prompt = "Documentos obrigatórios"
    context_chunks = ["Sample chunk about docs"]

    prompt = _build_prompt(user_prompt, context_chunks)

    # Should use specialized system prompt
    assert "especialista em editais de licitação" in prompt.lower()
    assert "lista completa" in prompt.lower() or "lista markdown" in prompt.lower()


def test_uses_generic_prompt_for_other_queries():
    """Test that non-domain queries use generic prompt."""
    user_prompt = "What is the deadline for submission?"
    context_chunks = ["Sample chunk about deadlines"]

    prompt = _build_prompt(user_prompt, context_chunks)

    # Should use generic system prompt
    assert "especialista em documentos jurídicos" in prompt.lower()
    assert "informações do contexto" in prompt.lower()


def test_prompt_includes_context_chunks():
    """Test that context chunks are included in prompt."""
    user_prompt = "Documentos obrigatórios"
    context_chunks = ["Chunk 1 about docs", "Chunk 2 about requirements"]

    prompt = _build_prompt(user_prompt, context_chunks)

    assert "Chunk 1 about docs" in prompt
    assert "Chunk 2 about requirements" in prompt
    assert "---" in prompt  # Separator between chunks


def test_prompt_includes_user_question():
    """Test that user prompt appears in final prompt."""
    user_prompt = "Documentos obrigatórios"
    context_chunks = ["Some context"]

    prompt = _build_prompt(user_prompt, context_chunks)

    assert user_prompt in prompt


@patch('services.llm_service.get_openrouter_client')
def test_generate_rag_response_calls_api(mock_get_client):
    """Test that API is called with proper format."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "## Documentos Obrigatórios\n1. CPF"
    mock_client.chat.completions.create.return_value = mock_response

    result = generate_rag_response("Documentos obrigatórios", ["Context 1", "Context 2"])

    # Verify API was called
    mock_client.chat.completions.create.assert_called_once()

    # Verify model
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert "deepseek" in call_kwargs["model"].lower()

    # Verify temperature (deterministic)
    assert call_kwargs["temperature"] == 0.2

    # Result should be the LLM response
    assert result == "## Documentos Obrigatórios\n1. CPF"


def test_empty_context_handled_gracefully():
    """Test that empty context is handled."""
    user_prompt = "Documentos obrigatórios"
    context_chunks = []

    prompt = _build_prompt(user_prompt, context_chunks)

    assert "Nenhum contexto relevante" in prompt or "sem contexto" in prompt.lower()
