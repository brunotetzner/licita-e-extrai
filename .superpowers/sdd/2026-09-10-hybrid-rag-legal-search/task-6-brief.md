# Task 6: End-to-End Integration Testing

## Overview

Verify that the complete hybrid RAG pipeline works correctly by simulating PDF extraction → chunking → indexing → search → LLM response.

No new code to write — this is verification only.

## Test Scenario

Use mock PDF elements (simulating `partition_pdf()` output) to verify the full pipeline:

```python
elements = [
    {"type": "Text", "text": "1. ARTIGOS GERAIS", "html": None},
    {"type": "Text", "text": "Disposições gerais do edital...", "html": None},
    {"type": "Text", "text": "2. DOCUMENTOS OBRIGATÓRIOS", "html": None},
    {"type": "Text", "text": "1) Cópia do CPF do responsável\n2) Contrato Social\n3) Prova de Patrimônio", "html": None},
    {"type": "Text", "text": "3. PRAZOS", "html": None},
    {"type": "Text", "text": "Prazo para apresentação: 30 dias...", "html": None},
]
```

## Verification Steps

### Step 1: Test Structured Chunking

```bash
python -c "
from services.structured_chunker_service import create_structured_chunks
chunks = create_structured_chunks(elements)
print(f'✓ Created {len(chunks)} chunks')
for i, chunk in enumerate(chunks):
    print(f'  Chunk {i}: {chunk[\"metadata\"][\"section_name\"][:30]}...')
"
```

**Expected Output:**
```
✓ Created 3 chunks
  Chunk 0: 1. ARTIGOS GERAIS...
  Chunk 1: 2. DOCUMENTOS OBRIGATÓRIOS...
  Chunk 2: 3. PRAZOS...
```

### Step 2: Test Indexing in ChromaDB

```bash
python -c "
from services.structured_chunker_service import create_structured_chunks
from services.vector_store_service import reset_and_index_chunks

chunks = create_structured_chunks(elements)
reset_and_index_chunks(chunks)
print(f'✓ Indexed {len(chunks)} chunks in ChromaDB')
"
```

**Expected Output:**
```
✓ Indexed 3 chunks in ChromaDB
```

### Step 3: Test Hybrid Search

```bash
python -c "
from services.structured_chunker_service import create_structured_chunks
from services.vector_store_service import reset_and_index_chunks
from services.hybrid_search_service import hybrid_search

chunks = create_structured_chunks(elements)
reset_and_index_chunks(chunks)

results = hybrid_search('Documentos obrigatórios', top_k=2)
print(f'✓ Retrieved {len(results)} results for \"Documentos obrigatórios\"')
print('  Results:')
for i, result in enumerate(results, 1):
    preview = result[:60].replace('\n', ' ')
    print(f'    {i}: {preview}...')
"
```

**Expected Output:**
```
✓ Retrieved 2 results for "Documentos obrigatórios"
  Results:
    1: 2. DOCUMENTOS OBRIGATÓRIOS
    1) Cópia do CPF...
    2: 1. ARTIGOS GERAIS...
```

**Key Check:** First result should be the DOCUMENTOS OBRIGATÓRIOS section (because it has the highest hybrid score: exact keyword match + list bonus).

### Step 4: Verify Backward Compatibility

Test that old `create_chunks()` still works:

```bash
python -c "
from services.chunker_service import create_chunks
elements = [
    {'type': 'Text', 'text': 'Section 1', 'html': None},
    {'type': 'Text', 'text': 'Long text ' * 200, 'html': None},
]
chunks = create_chunks(elements)
print(f'✓ Old create_chunks still works: {len(chunks)} chunks created')
"
```

**Expected Output:**
```
✓ Old create_chunks still works: 2 chunks created
```

### Step 5: Run All Unit Tests

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/ -v --tb=short
```

**Expected Output:**
```
tests/test_structured_chunker_service.py::test_creates_chunks_from_elements PASSED
tests/test_structured_chunker_service.py::test_preserves_tables_as_separate_chunks PASSED
tests/test_structured_chunker_service.py::test_detects_section_headers PASSED
tests/test_structured_chunker_service.py::test_does_not_split_lists_in_middle PASSED
tests/test_hybrid_search_service.py::test_score_by_keywords_finds_exact_phrase PASSED
... (all tests PASS)
```

## Success Criteria

- ✅ Structured chunking creates correct number of chunks
- ✅ Hybrid search ranks "Documentos obrigatórios" section first
- ✅ Old `create_chunks()` still works (backward compat)
- ✅ All unit tests pass (from tasks 2-4)
- ✅ No syntax/import errors

## No New Files

This task is verification only — no new files to create or commit. Just run the verification steps and report results.

Report file: `/home/btetzner/Documents/project/licita-e-extrai/.superpowers/sdd/2026-09-10-hybrid-rag-legal-search/task-6-report.md`
