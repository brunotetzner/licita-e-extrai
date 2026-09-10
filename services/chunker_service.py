from langchain_text_splitters import RecursiveCharacterTextSplitter

def create_chunks(elements, chunk_size=1000, chunk_overlap=150):
    chunks = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    for el in elements:
        element_type = el.get("type")
        text = el.get("text", "")
        html = el.get("html")

        # Se for Tabela com HTML, preserva como chunk único sem fatiar
        if element_type == "Table" and html:
            chunks.append({
                "text": f"[TABELA DETECTADA]\n{html}\n[/TABELA]",
                "metadata": {"type": "table"}
            })
        elif text and text.strip():
            sub_chunks = text_splitter.split_text(text)
            for sub_text in sub_chunks:
                chunks.append({
                    "text": sub_text,
                    "metadata": {"type": "text"}
                })

    return chunks