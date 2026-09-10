# Task 3: Create Hybrid Search Service

## Overview

Create `services/hybrid_search_service.py` implementing hybrid search with 3-phase ranking: semantic similarity + legal keyword matching + list heuristics.

## Interface

**Main Function:**
```python
def hybrid_search(query: str, top_k: int = 4) -> list[str]
```

Input: Query string (e.g., "Documentos obrigatórios")
Output: List of chunk texts ranked by hybrid score

**Helper Functions:**

```python
def score_by_keywords(text: str, query: str) -> float:
    """Returns 0-1 score based on legal patterns."""

def is_numbered_list(text: str) -> bool:
    """Returns True if text looks like a list (3+ numbered/lettered items)."""
```

## Algorithm: 3-Phase Ranking

**Phase 1: Semantic Search (top-10)**
- Use ChromaDB's `collection.query()` to get 10 most similar chunks
- Extract distance scores (ChromaDB returns distance, not similarity)

**Phase 2: Keyword Scoring**
- Check for legal/edital patterns:
  - "documentos? obrigat[óo]rios?"
  - "documentação? exigida?"
  - "anexo [IViv]+"
  - Numbered lists: "^\d+\)"
  - Lettered lists: "^[a-z]\)"
- Double weight if query phrase appears verbatim
- Score: 0-1 (normalized)

**Phase 3: Combined Ranking**
- Weights: 50% semantic + 35% keyword + 15% list bonus
- Formula:
  ```
  final_score = semantic * 0.50 + keyword * 0.35 + (0.15 if is_list else 0)
  ```
- Return top-4 by final_score

## Implementation Notes

- Convert ChromaDB distance to similarity: `semantic_score = 1 - distance`
- Use `re.search()` with `re.IGNORECASE | re.MULTILINE` flags
- Handle empty results gracefully (return empty list)

## Keyword Patterns (Exact Regexes)

Use these EXACT patterns in `score_by_keywords()`:

```python
patterns = [
    r"documentos?\s+obrigat[óo]rios?",
    r"documentação?\s+exigida?",
    r"anexo\s+[IViv]+",
    r"(?:^|\n)\d+\)\s+",      # "1) ..."
    r"(?:^|\n)[a-z]\)\s+",    # "a) ..."
]
```

## Tests

Location: `tests/test_hybrid_search_service.py`

1. **test_score_by_keywords_finds_exact_phrase** — Exact query match gets high score
2. **test_score_by_keywords_finds_patterns** — Legal patterns scored correctly
3. **test_score_by_keywords_low_for_generic_text** — Generic text gets low score
4. **test_is_numbered_list_true_for_lists** — List detection works
5. **test_is_numbered_list_false_for_non_lists** — Non-lists rejected
6. **test_hybrid_search_combines_scores** — Ranking combines scores correctly

All test code is in the plan's Task 3 section — use it verbatim (including mocks).

## Implementation Code

All code is in the plan's Task 3 section for `services/hybrid_search_service.py` — use it verbatim.

## Testing

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/test_hybrid_search_service.py -v
```

Expected: 6/6 tests PASS

## Commit

```bash
git add services/hybrid_search_service.py tests/test_hybrid_search_service.py
git commit -m "feat: add hybrid search service with 3-phase ranking

Implements hybrid search combining semantic similarity (50%) + legal
keyword patterns (35%) + list heuristics (15%) to rank chunks.

Keyword patterns detect legal/edital terminology and numbered lists.
Returns top-k chunks ranked by combined score.

Includes comprehensive unit tests with mocked ChromaDB.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

Report file: `/home/btetzner/Documents/project/licita-e-extrai/.superpowers/sdd/2026-09-10-hybrid-rag-legal-search/task-3-report.md`
