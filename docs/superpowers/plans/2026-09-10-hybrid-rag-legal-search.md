# Hybrid RAG for Legal Edital Search - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement hybrid search (semantic + keyword + heuristics) to reliably extract "Documentos Obrigatórios" from licitação editals with 95%+ precision.

**Architecture:** Three new layers (structured chunking, hybrid search service, domain-aware prompting) plus integration into existing controllers. Minimal changes to existing code.

**Tech Stack:** Python 3.9+, ChromaDB, Langchain, OpenRouter API (DeepSeek), regex patterns for keyword matching.

**Spec:** `docs/superpowers/specs/2026-09-10-hybrid-rag-legal-search.md`

## Global Constraints

- Must work generically (any edital, no per-document tuning)
- Achieve 95%+ precision on document extraction
- No external paid APIs or fine-tuning (use existing OpenRouter account)
- Backward compatible (existing `create_chunks` stays functional)
- Responses formatted as Markdown lists
- No metrics/confidence scores returned (user choice D)

---

## Task 1: Fix Chunker Service Bug

**Files:**
- Modify: `services/chunker_service.py:3`

**Interfaces:**
- No API change (internal bugfix only)

- [ ] **Step 1: Read the buggy function**

```bash
head -10 /home/btetzner/Documents/project/licita-e-extrai/services/chunker_service.py
```

Expected: See `chunk_overlap=ana` (invalid variable name)

- [ ] **Step 2: Fix the bug**

Replace line 3:
```python
# OLD
def create_chunks(elements, chunk_size=1000, chunk_overlap=ana):

# NEW
def create_chunks(elements, chunk_size=1000, chunk_overlap=200):
```

- [ ] **Step 3: Verify no syntax errors**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai && python -m py_compile services/chunker_service.py
```

Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add services/chunker_service.py
git commit -m "fix: correct chunk_overlap default value from invalid 'ana' to 200

The parameter was using an undefined variable name. Default to 200 chars
overlap to maintain backward compatibility.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Create Structured Chunker Service

**Files:**
- Create: `services/structured_chunker_service.py`

**Interfaces:**
- Consumes: `elements` (list of dicts with `type`, `text`, `html` from `partition_pdf`)
- Produces: Function `create_structured_chunks(elements) → list[dict]`
  - Each dict: `{"text": str, "metadata": {"type": "section"|"table", "section_name": str}}`

- [ ] **Step 1: Create test file**

Create `tests/test_structured_chunker_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/test_structured_chunker_service.py -v
```

Expected: All tests FAIL (functions not yet implemented)

- [ ] **Step 3: Implement structured_chunker_service.py**

Create `services/structured_chunker_service.py`:

```python
import re


def is_section_header(element):
    """Detect if element is a section header (heuristic)."""
    text = element.get("text", "").strip()
    
    # Must be short and start with uppercase
    if len(text) > 100 or not text or not text[0].isupper():
        return False
    
    # Must start with a known header pattern
    header_patterns = [
        r"^\d+\.",           # "1.", "2.", etc
        r"^[IVX]+\.",        # "I.", "II.", etc
        r"^ARTIGO",          # "ARTIGO 5"
        r"^CAPÍTULO",        # "CAPÍTULO 2"
        r"^SEÇÃO",           # "SEÇÃO 1"
        r"^ANEXO",           # "ANEXO I"
    ]
    
    return any(re.match(pattern, text, re.IGNORECASE) for pattern in header_patterns)


def create_structured_chunks(elements):
    """
    Divide PDF elements into chunks respecting natural section boundaries.
    
    Algorithm:
    1. Iterate through elements
    2. When section header found, start accumulating
    3. Keep accumulating until next header
    4. Tables: store as separate chunk
    5. Text sections: keep as one chunk regardless of size
    
    Args:
        elements: List of dicts with keys: type, text, html
        
    Returns:
        List of dicts: {"text": str, "metadata": {"type": "section"|"table", "section_name": str}}
    """
    chunks = []
    current_section_name = None
    section_buffer = []
    
    for element in elements:
        element_type = element.get("type")
        text = element.get("text", "").strip()
        html = element.get("html")
        
        # Check if this is a section header
        if is_section_header(element):
            # Save previous section if exists
            if section_buffer:
                chunks.append({
                    "text": "\n".join(section_buffer),
                    "metadata": {
                        "type": "section",
                        "section_name": current_section_name
                    }
                })
                section_buffer = []
            
            # Start new section
            current_section_name = text
            section_buffer = [text]
        
        # Handle tables separately
        elif element_type == "Table" and html:
            # Save current section if exists
            if section_buffer:
                chunks.append({
                    "text": "\n".join(section_buffer),
                    "metadata": {
                        "type": "section",
                        "section_name": current_section_name
                    }
                })
                section_buffer = []
            
            # Add table as separate chunk
            chunks.append({
                "text": f"[TABELA DETECTADA]\n{html}\n[/TABELA]",
                "metadata": {
                    "type": "table",
                    "section_name": current_section_name or "SEM SEÇÃO"
                }
            })
        
        # Regular text: accumulate in current section
        elif text:
            section_buffer.append(text)
    
    # Flush final section
    if section_buffer:
        chunks.append({
            "text": "\n".join(section_buffer),
            "metadata": {
                "type": "section",
                "section_name": current_section_name
            }
        })
    
    return chunks
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/test_structured_chunker_service.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/structured_chunker_service.py tests/test_structured_chunker_service.py
git commit -m "feat: add structured chunker service respecting section boundaries

New service divides PDF into chunks that respect natural edital structure
(articles, chapters, sections) instead of breaking on arbitrary character
counts. Preserves numbered lists and keeps tables as separate chunks.

Includes section header detection heuristics and comprehensive unit tests.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Create Hybrid Search Service

**Files:**
- Create: `services/hybrid_search_service.py`
- Create: `tests/test_hybrid_search_service.py`

**Interfaces:**
- Consumes: 
  - `search_similar_chunks(query, top_k)` from `vector_store_service` (already exists)
  - ChromaDB collection with stored chunks
- Produces: Function `hybrid_search(query, top_k=4) → list[str]`
  - Input: query string (e.g., "Documentos obrigatórios")
  - Output: List of chunk texts (strings) ranked by hybrid score

- [ ] **Step 1: Create test file**

Create `tests/test_hybrid_search_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/test_hybrid_search_service.py -v
```

Expected: All tests FAIL (module doesn't exist)

- [ ] **Step 3: Implement hybrid_search_service.py**

Create `services/hybrid_search_service.py`:

```python
import re
from services.vector_store_service import chroma_client, COLLECTION_NAME


def score_by_keywords(text, query):
    """
    Score text based on legal/edital keyword patterns.
    
    Returns score 0-1 where:
    - 0 = no keyword matches
    - 1 = multiple patterns match
    
    Patterns checked:
    - "documentos? obrigat[óo]rios?" 
    - "documentação? exigida?"
    - "anexo [IViv]+"
    - Numbered lists: "^\d+\)"
    - Lettered lists: "^[a-z]\)"
    - Query phrase appearing verbatim (double weight)
    """
    patterns = [
        r"documentos?\s+obrigat[óo]rios?",
        r"documentação?\s+exigida?",
        r"anexo\s+[IViv]+",
        r"(?:^|\n)\d+\)\s+",      # "1) ..."
        r"(?:^|\n)[a-z]\)\s+",    # "a) ..."
    ]
    
    matches = 0
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            matches += 1
    
    # Bonus: query phrase appears verbatim (2x weight)
    if query.lower() in text.lower():
        matches += 2
    
    # Normalize to 0-1
    return min(matches / 5, 1.0)


def is_numbered_list(text):
    """Check if text looks like a numbered/lettered list."""
    list_items = re.findall(
        r'(?:^|\n)(?:\d+\)|[a-z]\))\s+',
        text,
        re.MULTILINE
    )
    return len(list_items) >= 3


def hybrid_search(query, top_k=4):
    """
    Hybrid search combining semantic similarity + keyword matching + heuristics.
    
    Phase 1: Semantic similarity
    - Use ChromaDB to find top-10 most similar chunks
    
    Phase 2: Keyword scoring
    - Score each chunk by legal/edital patterns
    
    Phase 3: Ranking
    - Combine scores: 50% semantic + 35% keyword + 15% list bonus
    - Return top-k by combined score
    
    Args:
        query: Search query (e.g., "Documentos obrigatórios")
        top_k: Number of chunks to return (default 4)
        
    Returns:
        List of chunk texts, ranked by hybrid score
    """
    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception:
        return []
    
    # Phase 1: Semantic search (top-10)
    try:
        results = collection.query(
            query_texts=[query],
            n_results=10,
            include=["documents", "distances"]
        )
    except Exception:
        return []
    
    if not results or not results.get("documents"):
        return []
    
    documents = results["documents"][0]
    distances = results["distances"][0]
    
    # Phase 2 & 3: Score and rank
    scored_chunks = []
    
    for chunk_text, distance in zip(documents, distances):
        # Convert distance to similarity (ChromaDB uses distance metric)
        semantic_score = 1 - distance
        
        # Keyword scoring
        keyword_score = score_by_keywords(chunk_text, query)
        
        # List bonus (15% weight if looks like a list)
        list_bonus = 0.15 if is_numbered_list(chunk_text) else 0
        
        # Combine scores with weights
        final_score = (
            semantic_score * 0.50 +    # 50% semantic
            keyword_score * 0.35 +      # 35% keywords
            list_bonus                  # 15% list bonus
        )
        
        scored_chunks.append((chunk_text, final_score))
    
    # Sort by score descending, return top-k
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    return [chunk for chunk, _ in scored_chunks[:top_k]]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/test_hybrid_search_service.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

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

---

## Task 4: Update LLM Service with Domain-Aware Prompting

**Files:**
- Modify: `services/llm_service.py`
- Create: `tests/test_llm_service_domain_detection.py`

**Interfaces:**
- Consumes: 
  - `user_prompt: str` and `context_chunks: list[str]` (existing)
  - OpenRouter API client (existing)
- Produces: Same interface, but internally detects domain-specific queries and uses specialized prompts

- [ ] **Step 1: Create test file**

Create `tests/test_llm_service_domain_detection.py`:

```python
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
```

- [ ] **Step 2: Read current LLM service**

```bash
cat /home/btetzner/Documents/project/licita-e-extrai/services/llm_service.py
```

Expected: See current implementation

- [ ] **Step 3: Update llm_service.py**

Replace the entire file with:

```python
import os
from openai import OpenAI


def get_openrouter_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )


def _build_prompt(user_prompt: str, context_chunks: list) -> str:
    """
    Build the full prompt with context and system instructions.
    
    Detects if query is about "Documentos obrigatórios" and uses specialized prompt.
    
    Args:
        user_prompt: User's query
        context_chunks: List of context chunks from search
        
    Returns:
        Full prompt string ready for LLM
    """
    # Join context chunks
    if context_chunks:
        context_str = "\n\n---\n\n".join(context_chunks)
    else:
        context_str = "Nenhum contexto relevante foi encontrado no documento enviado."
    
    # Detect if this is a "Documentos obrigatórios" query
    is_doc_query = (
        "documento" in user_prompt.lower() and 
        "obrigat" in user_prompt.lower()
    )
    
    if is_doc_query:
        system_prompt = """Você é um especialista em editais de licitação.

Quando perguntado sobre "Documentos Obrigatórios":
1. Procure por seções que listam requisitos documentais
2. Compile uma lista COMPLETA e ordenada
3. Inclua referências a anexos se mencionados (ex: "Anexo I")
4. Separe por categoria se o edital assim o faz

Responda SEMPRE em formato de lista Markdown numerada.
Seja conciso mas completo. Não omita documentos."""
    else:
        system_prompt = """Você é um especialista em análise de documentos jurídicos.
Responda à solicitação do usuário utilizando estritamente as informações fornecidas no contexto.
Cite a seção/artigo quando relevante."""
    
    full_prompt = f"""{system_prompt}

CONTEXTO DO EDITAL:
{context_str}

SOLICITAÇÃO DO USUÁRIO:
{user_prompt}
"""
    
    return full_prompt


def generate_rag_response(user_prompt: str, context_chunks: list) -> str:
    """
    Generate RAG response using domain-aware prompting.
    
    Args:
        user_prompt: User's query
        context_chunks: List of context chunks from hybrid search
        
    Returns:
        LLM response string
    """
    client = get_openrouter_client()
    
    prompt = _build_prompt(user_prompt, context_chunks)
    
    # Log for debugging
    print(prompt)
    
    response = client.chat.completions.create(
        model=os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-v4-flash",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        extra_headers={
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "PDF RAG API - Editais de Licitação",
        }
    )
    
    return response.choices[0].message.content
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/test_llm_service_domain_detection.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

Create a helper function and refactor. Commit:

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

---

## Task 5: Integrate New Services into Controllers

**Files:**
- Modify: `controllers/hello_controller.py`

**Interfaces:**
- Consumes:
  - Old: `create_chunks`, `search_similar_chunks`
  - New: `create_structured_chunks`, `hybrid_search`
- Produces: Same API endpoints (no signature changes)

- [ ] **Step 1: Read current controller**

```bash
cat /home/btetzner/Documents/project/licita-e-extrai/controllers/hello_controller.py
```

Expected: See current `/extract` and `/analyze` endpoints

- [ ] **Step 2: Update imports**

In `controllers/hello_controller.py`, replace the import section (lines 1-6):

```python
# OLD
from services.chunker_service import create_chunks
from services.vector_store_service import reset_and_index_chunks, search_similar_chunks

# NEW
from services.structured_chunker_service import create_structured_chunks
from services.hybrid_search_service import hybrid_search
from services.vector_store_service import reset_and_index_chunks
# Keep old imports for backward compatibility (if needed elsewhere)
from services.chunker_service import create_chunks
```

- [ ] **Step 3: Update `/extract` endpoint**

In the `extract()` function (around line 47), replace:

```python
# OLD
chunks = create_chunks(resultado)

# NEW
chunks = create_structured_chunks(resultado)
```

- [ ] **Step 4: Update `/analyze` endpoint**

In the `analyze()` function (around line 72), replace:

```python
# OLD
context_chunks = search_similar_chunks(user_prompt, top_k=4)

# NEW
context_chunks = hybrid_search(user_prompt, top_k=4)
```

- [ ] **Step 5: Verify syntax**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai && python -m py_compile controllers/hello_controller.py
```

Expected: No output (success)

- [ ] **Step 6: Test the API locally (manual)**

Start the Flask server:
```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m flask run
```

In another terminal, test the endpoints:

```bash
# Test 1: Health check
curl http://localhost:5000/hello

# Test 2: Extract (requires a PDF file)
# For now, just verify no import errors by checking the app starts

# Test 3: Check that new services loaded
python -c "from services.structured_chunker_service import create_structured_chunks; from services.hybrid_search_service import hybrid_search; print('✓ All imports successful')"
```

- [ ] **Step 7: Commit**

```bash
git add controllers/hello_controller.py
git commit -m "feat: integrate structured chunking and hybrid search into API

Update /extract endpoint to use structured_chunker_service for better
section boundary preservation.

Update /analyze endpoint to use hybrid_search service for improved
ranking (semantic + keywords + heuristics).

Maintains backward compatibility by keeping old imports available.
No API signature changes — drop-in replacement for existing code.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

---

## Task 6: End-to-End Integration Testing

**Files:**
- No new files (uses existing debug script)

**Interfaces:**
- Tests the full pipeline: `/extract` → `/analyze`

- [ ] **Step 1: Create a manual test document**

Create a test edital file or use an existing one. The test should verify:

```bash
# 1. Start Flask server
cd /home/btetzner/Documents/project/licita-e-extrai
python -m flask run --port 5000 &
FLASK_PID=$!

# 2. Wait for server to start
sleep 2

# 3. Upload a PDF (if you have one)
# For now, create a mock test
python -c "
from services.structured_chunker_service import create_structured_chunks
from services.hybrid_search_service import hybrid_search
from services.vector_store_service import reset_and_index_chunks

# Mock elements (simulating PDF extraction)
elements = [
    {'type': 'Text', 'text': '1. ARTIGOS GERAIS', 'html': None},
    {'type': 'Text', 'text': 'Disposições gerais do edital...', 'html': None},
    {'type': 'Text', 'text': '2. DOCUMENTOS OBRIGATÓRIOS', 'html': None},
    {'type': 'Text', 'text': '1) Cópia do CPF do responsável\n2) Contrato Social\n3) Prova de Patrimônio', 'html': None},
    {'type': 'Text', 'text': '3. PRAZOS', 'html': None},
    {'type': 'Text', 'text': 'Prazo para apresentação: 30 dias...', 'html': None},
]

# Test structured chunking
chunks = create_structured_chunks(elements)
print(f'✓ Created {len(chunks)} chunks')
for i, chunk in enumerate(chunks):
    print(f'  Chunk {i}: {chunk[\"metadata\"][\"section_name\"][:30]}...')

# Test indexing
reset_and_index_chunks(chunks)
print('✓ Indexed chunks in ChromaDB')

# Test hybrid search
results = hybrid_search('Documentos obrigatórios', top_k=2)
print(f'✓ Retrieved {len(results)} results for \"Documentos obrigatórios\"')
print('  Results:')
for i, result in enumerate(results):
    preview = result[:60].replace('\n', ' ')
    print(f'    {i+1}: {preview}...')
"

# 4. Kill Flask server
kill $FLASK_PID
```

Expected output:
```
✓ Created 3 chunks
  Chunk 0: 1. ARTIGOS GERAIS...
  Chunk 1: 2. DOCUMENTOS OBRIGATÓRIOS...
  Chunk 2: 3. PRAZOS...
✓ Indexed chunks in ChromaDB
✓ Retrieved 2 results for "Documentos obrigatórios"
  Results:
    1: 2. DOCUMENTOS OBRIGATÓRIOS
    1) Cópia do CPF...
    2: 1. ARTIGOS GERAIS...
```

The first result should be the DOCUMENTOS OBRIGATÓRIOS section (because it has highest hybrid score).

- [ ] **Step 2: Verify no regressions in existing endpoints**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai

# Test that old create_chunks still works (backward compat)
python -c "
from services.chunker_service import create_chunks

elements = [
    {'type': 'Text', 'text': 'Section 1', 'html': None},
    {'type': 'Text', 'text': 'Long text ' * 200, 'html': None},  # Will be split
]

chunks = create_chunks(elements)
print(f'✓ Old create_chunks still works: {len(chunks)} chunks created')
"
```

Expected: Output shows backward compatibility maintained

- [ ] **Step 3: Run all tests**

```bash
cd /home/btetzner/Documents/project/licita-e-extrai
python -m pytest tests/ -v --tb=short
```

Expected: All tests PASS (from tasks 2-4)

- [ ] **Step 4: Commit integration test results**

```bash
git log --oneline -5
```

Expected: See commits from all previous tasks.

No new commit for this task (it's verification only).

---

## Success Criteria Verification

Before claiming done, verify against the spec:

- [ ] ✅ Structured chunking respects section boundaries (Task 2)
- [ ] ✅ Hybrid search combines semantic + keywords + heuristics (Task 3)
- [ ] ✅ Domain-aware prompting for "Documentos obrigatórios" queries (Task 4)
- [ ] ✅ Integration into `/extract` and `/analyze` endpoints (Task 5)
- [ ] ✅ Backward compatibility maintained (Task 1, 5)
- [ ] ✅ All unit tests passing (Tasks 2-4, verified in 6)
- [ ] ✅ No external paid APIs added
- [ ] ✅ Responses formatted as Markdown lists (ensured by domain-aware prompt)

---

## Notes for Implementer

1. **Test-Driven:** Each task has failing tests → implementation → passing tests. This is intentional.
2. **Commits:** Frequent commits make review easier and rollback simpler.
3. **Backward Compat:** Old functions still exist. New services are additions, not replacements.
4. **ChromaDB:** Uses existing in-memory instance. No persistence changes.
5. **OpenRouter:** Uses existing `.env` configuration. No API changes needed.
6. **Debugging:** `print()` statements left in `llm_service.py` for prompt visibility. Remove if noisy.

---

## Potential Blockers

- **If hybrid_search returns wrong order:** Debug by checking `score_by_keywords()` output. Adjust weights (0.50/0.35/0.15) if needed.
- **If LLM response isn't Markdown list:** Verify the domain prompt is being used. Check that `_build_prompt()` correctly detects "documento" + "obrigat".
- **If structured chunking creates too-large chunks:** That's OK and expected — preserves list coherence.
- **If tests timeout on ChromaDB:** Increase timeout or mock more aggressively.
