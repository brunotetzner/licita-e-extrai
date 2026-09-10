# Task 2 Report: Create Structured Chunker Service

## Status: DONE

## Summary
Created `services/structured_chunker_service.py` with `is_section_header()` and
`create_structured_chunks()`, plus `tests/test_structured_chunker_service.py`
with the 4 specified unit tests. Followed TDD: wrote tests first, confirmed
they failed (ModuleNotFoundError), then implemented and confirmed all 4 pass.

## Files Changed
- **New**: `/home/btetzner/Documents/project/licita-e-extrai/services/structured_chunker_service.py`
- **New**: `/home/btetzner/Documents/project/licita-e-extrai/tests/test_structured_chunker_service.py`

## Deviation from "verbatim" plan code (bug found and fixed)

The plan/brief said to use the implementation code verbatim, but the verbatim
version of `is_section_header()` failed 2 of the 4 specified (verbatim) tests.
Root cause: the header check required `text[0].isupper()`, but Python's
`str.isupper()` returns `False` for digit characters. This meant headers like
`"1. ARTIGOS"` or `"2. DOCUMENTOS OBRIGATÓRIOS"` (digit-first) were never
recognized as section headers, even though the regex patterns explicitly
include `r"^\d+\."` for exactly this case.

Since the tests are the fixed contract (per TDD, and per the brief's own
"4/4 tests PASS" requirement), I fixed the implementation instead of altering
the tests. Change made in `is_section_header`:

```python
# Before (from plan, verbatim — fails tests)
if len(text) > 100 or not text or not text[0].isupper():
    return False

# After (fix)
if len(text) > 100 or not text or not (text[0].isupper() or text[0].isdigit()):
    return False
```

This is analogous to Task 1, where the plan's prose also didn't exactly match
what needed to end up in the file — a small correction was needed to satisfy
the actual spec (the tests).

Everything else (algorithm structure, regex patterns, output shape, table
handling, docstrings) matches the plan verbatim.

## Environment note
`pytest` was not installed in the project's `.venv` (only `unstructured` and
related PDF packages were present). Installed `pytest==9.1.1` (with
`pluggy`, `iniconfig`) into `.venv` to run the test suite. This was not added
to `requirements.txt` since the brief didn't ask for dependency changes —
flagging this as a concern for whoever runs Task 3+ tests next, since they'll
likely need pytest available too (it will already be installed in this
`.venv` if the same environment is reused).

## Verification
```
$ .venv/bin/python -m pytest tests/test_structured_chunker_service.py -v
tests/test_structured_chunker_service.py::test_creates_chunks_from_elements PASSED
tests/test_structured_chunker_service.py::test_preserves_tables_as_separate_chunks PASSED
tests/test_structured_chunker_service.py::test_detects_section_headers PASSED
tests/test_structured_chunker_service.py::test_does_not_split_lists_in_middle PASSED
4 passed in 0.02s
```
Also ran full repo test suite (`pytest -v`) — only these 4 tests exist, all pass, nothing else broken.

## Git Commit
- **Commit Hash**: eaf148bb3ff6f3bb6cd03b807293d36651c1f169
- **Files in commit**: `services/structured_chunker_service.py`, `tests/test_structured_chunker_service.py` (only these two — verified via `git status` before and after commit; unrelated untracked `.superpowers/` dir left untouched)
- **Message**: matches brief's required commit message, with both required co-author attribution lines (Claude Haiku 4.5 from the brief, Claude Sonnet 5 per current session's attribution instruction)

## Task Completion
All steps in the TDD workflow completed: tests written first, verified failing,
implementation added (with one necessary bugfix over the "verbatim" plan text),
verified 4/4 passing, committed.
