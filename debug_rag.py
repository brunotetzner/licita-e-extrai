#!/usr/bin/env python3
"""
Script de diagnóstico para debugar o RAG.
Rastreia cada camada do sistema para identificar onde o contexto se perde.
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from services.chunker_service import create_chunks
from services.vector_store_service import reset_and_index_chunks, search_similar_chunks
from unstructured.partition.pdf import partition_pdf

# Configurações de diagnóstico
TEST_QUERY = "Documentos obrigatórios"
TOP_K = 10  # Aumentar para ver mais resultados


def diagnose_chunking(pdf_path):
    """Analisa como o PDF é dividido em chunks."""
    print("\n" + "="*80)
    print("FASE 1: EXTRAÇÃO E CHUNKING")
    print("="*80)

    # Extração
    elements = partition_pdf(
        file=pdf_path,
        strategy="fast",
        infer_table_structure=True,
        extract_images_in_pdf=False
    )

    print(f"\n✓ Total de elementos extraídos: {len(elements)}")

    # Análise de elementos
    element_types = {}
    for el in elements:
        cat = el.category
        element_types[cat] = element_types.get(cat, 0) + 1

    print("\nTipos de elementos encontrados:")
    for elem_type, count in sorted(element_types.items()):
        print(f"  - {elem_type}: {count}")

    # Conversão para formato esperado
    resultado = [
        {
            "type": el.category,
            "text": el.text,
            "html": el.metadata.text_as_html if el.category == "Table" else None
        }
        for el in elements
    ]

    # Chunking
    chunks = create_chunks(resultado)

    print(f"\n✓ Total de chunks criados: {len(chunks)}")

    # Análise de chunks
    chunk_types = {}
    for chunk in chunks:
        ct = chunk["metadata"]["type"]
        chunk_types[ct] = chunk_types.get(ct, 0) + 1

    print("\nTipos de chunks:")
    for ct, count in sorted(chunk_types.items()):
        print(f"  - {ct}: {count}")

    # Procurar chunks relacionados a "documentos"
    print("\n" + "-"*80)
    print("Chunks que mencionam 'documento' (primeiros 5):")
    print("-"*80)

    doc_chunks = []
    for i, chunk in enumerate(chunks):
        if "documento" in chunk["text"].lower():
            doc_chunks.append((i, chunk))

    print(f"Total: {len(doc_chunks)} chunks mencionam 'documento'\n")

    for i, (idx, chunk) in enumerate(doc_chunks[:5]):
        print(f"\nChunk #{idx} ({chunk['metadata']['type']}):")
        print("-" * 40)
        text_preview = chunk["text"][:300] + "..." if len(chunk["text"]) > 300 else chunk["text"]
        print(text_preview)

    return chunks


def diagnose_embedding(chunks):
    """Analisa como o banco vetorial recupera chunks."""
    print("\n" + "="*80)
    print("FASE 2: EMBEDDING E BUSCA SEMÂNTICA")
    print("="*80)

    # Indexar chunks
    reset_and_index_chunks(chunks)
    print(f"✓ {len(chunks)} chunks indexados no ChromaDB")

    # Busca com a query do usuário
    print(f"\nBuscando com query: '{TEST_QUERY}'")
    print(f"Recuperando top {TOP_K} resultados...\n")

    results = search_similar_chunks(TEST_QUERY, top_k=TOP_K)

    print(f"✓ Recuperados {len(results)} chunks\n")
    print("-"*80)

    for i, chunk_text in enumerate(results, 1):
        print(f"\n[RESULTADO #{i}]")
        print("-" * 40)
        preview = chunk_text[:250] + "..." if len(chunk_text) > 250 else chunk_text
        print(preview)


def diagnose_prompt_quality(chunks):
    """Analisa se o prompt é específico o suficiente."""
    print("\n" + "="*80)
    print("FASE 3: QUALIDADE DO PROMPT")
    print("="*80)

    print("\nPrompt atual (genérico):")
    print(f"  '{TEST_QUERY}'")

    print("\nProblemas identificados:")
    print("  ⚠ Query muito genérica ('documentos' aparece em muitos contextos)")
    print("  ⚠ Não especifica que é um edital de licitação")
    print("  ⚠ Não pede por 'lista', 'seção', 'artigo específico'")

    print("\nSugestões de queries melhoradas:")
    suggestions = [
        "Quais são os documentos obrigatórios que o licitante deve apresentar?",
        "Liste todos os documentos exigidos para participação na licitação",
        "Quais documentos são necessários para submissão da proposta? Faça uma lista completa",
        "Documentos que devem ser anexados à proposta (artigos, seções)",
    ]

    for i, sugg in enumerate(suggestions, 1):
        print(f"  {i}. {sugg}")


def main():
    pdf_path = None

    # Procurar por um PDF no diretório
    for file in Path(".").glob("*.pdf"):
        pdf_path = file
        break

    if not pdf_path:
        print("❌ Nenhum PDF encontrado no diretório atual")
        print("Use: python debug_rag.py <caminho_do_pdf>")
        sys.exit(1)

    print(f"\n📄 Analisando PDF: {pdf_path}")

    try:
        chunks = diagnose_chunking(str(pdf_path))
        diagnose_embedding(chunks)
        diagnose_prompt_quality(chunks)

        print("\n" + "="*80)
        print("DIAGNÓSTICO CONCLUÍDO")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Erro durante diagnóstico: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
