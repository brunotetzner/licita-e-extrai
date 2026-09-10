# Task 4: Update LLM Service with Domain-Aware Prompting

## Overview

Update `services/llm_service.py` to detect domain-specific queries (about "Documentos obrigatórios") and use specialized prompts. Add helper function `_build_prompt()` for testing.

## Interface Change

**Current function:** `generate_rag_response(user_prompt, context_chunks) → str`
**New behavior:** Same signature, but detects domain queries internally

**New helper (for testing):**
```python
def _build_prompt(user_prompt: str, context_chunks: list) -> str:
    """Build the full prompt with context and system instructions."""
```

## Domain Query Detection

Trigger specialized prompt when BOTH conditions are true:
- `"documento" in user_prompt.lower()`
- `"obrigat" in user_prompt.lower()`

Otherwise use generic prompt.

## Prompts

### Specialized Prompt (Domain Query)

```
Você é um especialista em editais de licitação.

Quando perguntado sobre "Documentos Obrigatórios":
1. Procure por seções que listam requisitos documentais
2. Compile uma lista COMPLETA e ordenada
3. Inclua referências a anexos se mencionados (ex: "Anexo I")
4. Separe por categoria se o edital assim o faz

Responda SEMPRE em formato de lista Markdown numerada.
Seja conciso mas completo. Não omita documentos.
```

### Generic Prompt

```
Você é um especialista em análise de documentos jurídicos.
Responda à solicitação do usuário utilizando estritamente as informações fornecidas no contexto.
Cite a seção/artigo quando relevante.
```

### Full Prompt Structure

```
{system_prompt}

CONTEXTO DO EDITAL:
{context_chunks_joined_by_---}

SOLICITAÇÃO DO USUÁRIO:
{user_prompt}
```

Context joining: `"\n\n---\n\n".join(context_chunks)` or "Nenhum contexto relevante..." if empty.

## OpenRouter API Call

```python
response = client.chat.completions.create(
    model=os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-v4-flash",
    messages=[
        {"role": "user", "content": full_prompt}
    ],
    temperature=0.2,
    extra_headers={
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "PDF RAG API - Editais de Licitação",
    }
)
return response.choices[0].message.content
```

## Tests

Location: `tests/test_llm_service_domain_detection.py`

1. **test_detects_documentos_obrigatorios_query** — Domain prompt triggered
2. **test_uses_generic_prompt_for_other_queries** — Generic prompt for non-domain
3. **test_prompt_includes_context_chunks** — Context chunks in prompt
4. **test_prompt_includes_user_question** — User prompt in final prompt
5. **test_generate_rag_response_calls_api** — API called with correct params (mocked)
6. **test_empty_context_handled_gracefully** — Empty context doesn't crash

All test code is in the plan's Task 4 section — use it verbatim (including mocks).

## Files to Modify

1. **`services/llm_service.py`** — Replace entire file with new implementation
2. **`tests/test_llm_service_domain_detection.py`** — Create with tests

All code is in the plan's Task 4 section — use it verbatim.

## Testing

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/test_llm_service_domain_detection.py -v
```

Expected: 6/6 tests PASS

## Commit

```bash
git add services/llm_service.py tests/test_llm_service_domain_detection.py
git commit -m "feat: add domain-aware prompting to LLM service

Detect queries about 'Documentos obrigatórios' and use specialized
system prompt that instructs the LLM to:
- Search for document requirement sections specifically
- Return complete, ordered lists
- Include references to appendices
- Format response as Markdown

Generic queries continue using standard prompt.

Includes helper function _build_prompt() for testing and comprehensive
unit tests with API mocking.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

Report file: `/home/btetzner/Documents/project/licita-e-extrai/.superpowers/sdd/2026-09-10-hybrid-rag-legal-search/task-4-report.md`
