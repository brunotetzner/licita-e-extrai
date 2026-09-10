import re


def is_section_header(element):
    """Detect if element is a section header (heuristic)."""
    text = element.get("text", "").strip()

    # Must be short and start with uppercase (or a digit, e.g. "1.", "2.")
    if len(text) > 100 or not text or not (text[0].isupper() or text[0].isdigit()):
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
