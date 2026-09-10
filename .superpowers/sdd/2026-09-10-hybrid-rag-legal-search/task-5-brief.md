# Task 5: Integrate New Services into Controllers

## Overview

Update `controllers/hello_controller.py` to wire up the new services (structured chunker and hybrid search) into the existing `/extract` and `/analyze` endpoints.

## Changes Required

### File: `controllers/hello_controller.py`

**Step 1: Update imports (top of file)**

Replace lines 1-6 with:
```python
from flask import Blueprint, jsonify, request
from unstructured.partition.pdf import partition_pdf

from services.structured_chunker_service import create_structured_chunks
from services.hybrid_search_service import hybrid_search
from services.vector_store_service import reset_and_index_chunks
# Keep old imports for backward compatibility (if needed elsewhere)
from services.chunker_service import create_chunks

bp = Blueprint("hello", __name__)
```

**Step 2: Update `/extract` endpoint**

In the `extract()` function, around line 47, replace:
```python
# OLD
chunks = create_chunks(resultado)

# NEW
chunks = create_structured_chunks(resultado)
```

**Step 3: Update `/analyze` endpoint**

In the `analyze()` function, around line 72, replace:
```python
# OLD
context_chunks = search_similar_chunks(user_prompt, top_k=4)

# NEW
context_chunks = hybrid_search(user_prompt, top_k=4)
```

## Verification

After making changes:

1. Check syntax:
   ```bash
   python -m py_compile /home/btetzner/Documents/project/licita-e-extrai/controllers/hello_controller.py
   ```
   Expected: No output (success)

2. Test imports load without error:
   ```bash
   python -c "from services.structured_chunker_service import create_structured_chunks; from services.hybrid_search_service import hybrid_search; print('✓ All imports successful')"
   ```
   Expected: Prints "✓ All imports successful"

## API Compatibility

- No endpoint signatures change
- No request/response format changes
- Drop-in replacement for existing code
- Backward compatibility: old `create_chunks()` still available

## Commit

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

Report file: `/home/btetzner/Documents/project/licita-e-extrai/.superpowers/sdd/2026-09-10-hybrid-rag-legal-search/task-5-report.md`
