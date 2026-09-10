# Task 2: Create Structured Chunker Service

## Overview

Create a new service `services/structured_chunker_service.py` that divides PDF elements into chunks respecting natural section boundaries (articles, chapters) instead of breaking on arbitrary character counts.

## Key Differences from Old Chunker

**Old approach:** Fixed chunk size of 1000 chars → breaks numbered lists in middle
**New approach:** Divide by section boundaries → preserves list coherence

## Interface

**Function Signature:**
```python
def create_structured_chunks(elements) -> list[dict]
```

**Input:** List of dicts from `partition_pdf()`:
```python
[
  {"type": "Text", "text": "...", "html": None},
  {"type": "Table", "text": "...", "html": "<table>...</table>"},
  ...
]
```

**Output:** List of chunks:
```python
[
  {
    "text": "full section text",
    "metadata": {"type": "section", "section_name": "1. ARTIGOS"}
  },
  {
    "text": "[TABELA DETECTADA]\n<table>...</table>\n[/TABELA]",
    "metadata": {"type": "table", "section_name": "1. ARTIGOS"}
  },
  ...
]
```

## Implementation Details

### Helper Function: `is_section_header(element) -> bool`

Detects section headers using these heuristics:
- Text length < 100 characters
- First character is uppercase
- Starts with known pattern: "1.", "2.", "I", "II", "ARTIGO", "CAPÍTULO", "SEÇÃO", "ANEXO"

### Main Algorithm

1. Iterate through elements
2. When section header found, flush previous buffer and start new section
3. Accumulate text until next header
4. Tables: store separately (preserve HTML as-is)
5. Text sections: keep as one chunk regardless of size

### Example

```
Input:
  {"type": "Text", "text": "1. ARTIGOS"}
  {"type": "Text", "text": "Blah blah (2000 chars)..."}
  {"type": "Table", "html": "<table>..."}
  {"type": "Text", "text": "2. DOCUMENTOS"}
  {"type": "Text", "text": "1) CPF\n2) Contrato (1500 chars)..."}

Output (3 chunks):
  Chunk 0: type=section, "1. ARTIGOS\nBlah blah..."  (NOT split)
  Chunk 1: type=table, "[TABELA...]"
  Chunk 2: type=section, "2. DOCUMENTOS\n1) CPF..."  (NOT split, even at 1500 chars)
```

## Tests to Write

Location: `tests/test_structured_chunker_service.py`

1. **test_creates_chunks_from_elements** — Basic flow, 2 sections created
2. **test_preserves_tables_as_separate_chunks** — Tables get own chunks
3. **test_detects_section_headers** — Header detection works
4. **test_does_not_split_lists_in_middle** — Numbered list stays together even if > 1000 chars

All test code is in the plan's Task 2 section — use it verbatim.

## Implementation Code

All code is in the plan's Task 2 section for `services/structured_chunker_service.py` — use it verbatim.

## Testing

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/test_structured_chunker_service.py -v
```

Expected: 4/4 tests PASS

## Commit

```bash
git add services/structured_chunker_service.py tests/test_structured_chunker_service.py
git commit -m "feat: add structured chunker service respecting section boundaries

New service divides PDF into chunks that respect natural edital structure
(articles, chapters, sections) instead of breaking on arbitrary character
counts. Preserves numbered lists and keeps tables as separate chunks.

Includes section header detection heuristics and comprehensive unit tests.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

Report file: `/home/btetzner/Documents/project/licita-e-extrai/.superpowers/sdd/2026-09-10-hybrid-rag-legal-search/task-2-report.md`
