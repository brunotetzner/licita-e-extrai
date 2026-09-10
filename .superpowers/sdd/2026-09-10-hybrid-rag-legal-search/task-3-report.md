# Task 3 Report: Create Hybrid Search Service

## Status
DONE

## Commit
`456733a` — feat: add hybrid search service with 3-phase ranking

Files committed:
- `services/hybrid_search_service.py`
- `tests/test_hybrid_search_service.py`

## Test Summary
6/6 PASS (`python -m pytest tests/test_hybrid_search_service.py -v`)

- test_score_by_keywords_finds_exact_phrase — PASS
- test_score_by_keywords_finds_patterns — PASS
- test_score_by_keywords_low_for_generic_text — PASS
- test_is_numbered_list_true_for_lists — PASS
- test_is_numbered_list_false_for_non_lists — PASS
- test_hybrid_search_combines_scores — PASS

Full project suite also green: 10/10 tests pass (`python -m pytest -v`), no regressions in `tests/test_structured_chunker_service.py`.

## TDD Workflow Followed
1. Created `tests/test_hybrid_search_service.py` verbatim from brief.
2. Ran tests — confirmed collection error (`ModuleNotFoundError: No module named 'services.hybrid_search_service'`), i.e. expected failure since the module didn't exist yet.
3. Created `services/hybrid_search_service.py` verbatim from brief, implementing `hybrid_search()`, `score_by_keywords()`, `is_numbered_list()`.
4. Re-ran tests — all 6 passed.
5. Committed with the exact message specified in the brief (co-author: `Claude Haiku 4.5 <noreply@anthropic.com>`), staging only the two new files.

## Deviations from Plan
One minor, non-functional deviation:
- The `score_by_keywords()` docstring contained `\d+\)` inside a plain (non-raw) triple-quoted string, which produced a `SyntaxWarning: invalid escape sequence '\d'` at import time. Changed the docstring to a raw string (`r"""..."""`) to silence the warning. No behavioral change — the actual regex patterns in the `patterns` list were already raw strings (`r"..."`) as specified and are untouched. Verified tests still pass 6/6 after the fix.

No other deviations. Interfaces (`chroma_client`, `COLLECTION_NAME` from `services/vector_store_service`) matched the brief's assumptions exactly — confirmed by reading `services/vector_store_service.py` before implementing.

## Concerns
None blocking. Notes for future integration:
- `hybrid_search()` currently calls `collection.get_collection(name=COLLECTION_NAME)` without passing an `embedding_function`, unlike `search_similar_chunks()` in `vector_store_service.py` which passes `embedding_function=default_ef`. This matches the brief's exact code, but may need alignment later if ChromaDB requires the embedding function to be re-supplied when re-fetching a collection outside of test/mock scenarios (not an issue for the unit tests, which mock `chroma_client` entirely).
