# Task 4 Report: Update LLM Service with Domain-Aware Prompting

## Status: DONE

## Commit
`f2acfc0` — feat: add domain-aware prompting to LLM service

## Test Summary
`tests/test_llm_service_domain_detection.py`: **6/6 PASS**

- test_detects_documentos_obrigatorios_query — PASS
- test_uses_generic_prompt_for_other_queries — PASS
- test_prompt_includes_context_chunks — PASS
- test_prompt_includes_user_question — PASS
- test_generate_rag_response_calls_api — PASS
- test_empty_context_handled_gracefully — PASS

## Full Suite Check
`python -m pytest tests/ -v` → **16/16 PASS** (includes Tasks 2-3 tests: `test_hybrid_search_service.py` 6 tests, `test_structured_chunker_service.py` 4 tests, plus the 6 new tests). No regressions.

## Implementation Summary
- `services/llm_service.py` was rewritten: extracted prompt-building logic into `_build_prompt(user_prompt, context_chunks)`, which detects "documento" + "obrigat" (case-insensitive) in the user query and selects between a specialized "especialista em editais de licitação" system prompt (instructs complete numbered Markdown lists, annex references, category separation) and a generic legal-document-analysis system prompt. `generate_rag_response()` now delegates prompt construction to `_build_prompt()` and calls the OpenRouter API unchanged otherwise (model `deepseek/deepseek-v4-flash` default, temperature 0.2).
- `tests/test_llm_service_domain_detection.py` created with the 6 unit tests as specified, using `unittest.mock.patch` on `services.llm_service.get_openrouter_client`.

## Deviation from Brief (and why)

The brief's verbatim test file and verbatim implementation file were internally inconsistent for the **generic prompt** case:

- Test asserted: `"especialista em documentos jurídicos" in prompt.lower()` and `"informações do contexto" in prompt.lower()`
- Given implementation text was: `"Você é um especialista em análise de documentos jurídicos... utilizando estritamente as informações fornecidas no contexto."`

Neither assertion is a substring match of that exact wording (extra words "análise de" and "fornecidas no" break the substring checks), so running both verbatim pieces together produced a failing test (`test_uses_generic_prompt_for_other_queries`).

Resolution (TDD-driven): kept the test assertions as given (they define the contract) and adjusted only the generic system prompt's wording to:

```
Você é um especialista em documentos jurídicos.
Responda à solicitação do usuário utilizando estritamente as informações do contexto fornecido.
Cite a seção/artigo quando relevante.
```

This preserves the intended meaning/behavior exactly (same role, same strict-context instruction, same citation instruction) while satisfying the exact substrings the test checks for. The domain-specific ("Documentos obrigatórios") prompt required no changes — it matched its test verbatim.

No other deviations. All other code (client setup, context joining with `---` separator, empty-context fallback message, domain detection logic, full prompt structure, API call parameters) matches the brief verbatim.

## Concerns
None outstanding. The only concern is the noted prompt-wording deviation above, which is cosmetic (Portuguese phrasing) and does not change any control flow, detection logic, or the domain-specific specialized prompt.
