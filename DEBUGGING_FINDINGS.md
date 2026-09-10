# Root Cause Analysis: RAG Falha em "Documentos Obrigatórios"

## Problema Observado

Query: `"Documentos obrigatórios"`

Resposta obtida:
```
1.3.4. Eventuais anexos dos documentos supracitados.
---
A verificação no SICAF ou a exigência dos documentos nele não contidos
---
DA APRESENTAÇÃO DA PROPOSTA E DOS DOCUMENTOS DE
```

**Problema:** Fragmentos genéricos que mencionam "documentos", mas NÃO a seção específica que lista os documentos obrigatórios.

---

## Phase 1: Root Cause Investigation

### 1.1 Fluxo de Dados

```
PDF (edital licitação)
    ↓ partition_pdf() com strategy="fast"
[Elementos: tipo, texto, html]
    ↓ create_chunks(chunk_size=1000, chunk_overlap=???)  ← ERRO: ana não definido
[Chunks de ~1000 caracteres]
    ↓ reset_and_index_chunks()
ChromaDB + DefaultEmbeddingFunction (all-MiniLM-L6-v2)
    ↓ search_similar_chunks("Documentos obrigatórios", top_k=4)
[Retorna 4 chunks mais similares]
    ↓ generate_rag_response()
[DeepSeek v4 Flash com prompt genérico]
RESPOSTA
```

### 1.2 Raízes Identificadas (não sintomas)

#### RAIZ 1: Modelo de Embedding Genérico
**Arquivo:** `vector_store_service.py:6`

```python
default_ef = embedding_functions.DefaultEmbeddingFunction()
```

**Por que é um problema:**
- `all-MiniLM-L6-v2` é treinado em corpus genérico da internet
- NÃO foi treinado em documentos jurídicos ou editais de licitação
- Não entende estrutura específica de editais (artigos, incisos, seções)
- Query "Documentos obrigatórios" = múltiplas interpretações semânticas:
  - Uma lista que enumera documentos
  - Uma menção incidental de "documentos" com qualificador "obrigatório"
  - Uma seção de requisitos
  - Referências a documentos em contextos diferentes

**Evidência:** O embedding retorna fragmentos que mencionam "documento" genericamente, não especificamente seções com LISTAS.

#### RAIZ 2: Chunking Quebra Listas
**Arquivo:** `chunker_service.py:5-7`

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=chunk_overlap  # ← ERRO: "ana" não é variável válida
)
```

**Por que é um problema:**
- Chunks de 1000 caracteres = ~200-250 palavras
- Uma LISTA de "Documentos obrigatórios" em um edital típico:
  - Começa com cabeçalho "Documentos Obrigatórios" ou "Documentação Exigida"
  - Tem 10-30 itens numerados: "1) CPF, 2) Contrato Social, 3) Prova de Patrimônio..."
  - Total: ~1500-3000 caracteres
- Se lista > 1000 chars: **é dividida em múltiplos chunks**
  - Chunk 1: Cabeçalho + itens 1-5
  - Chunk 2: Itens 6-10
  - Chunk 3: Itens 11-15
  - ...

**Problema:** Quando busca por "Documentos obrigatórios":
- Cada chunk é embedidado SEPARADAMENTE
- Chunk 2 (itens 6-10) pode ter baixa similaridade se seu embedding não reconhecer que faz parte de uma lista
- Chunk com cabeçalho pode ser recuperado, mas sem os itens completos

**Evidência:** Resposta mostra fragmentos isolados, não uma lista coerente.

#### RAIZ 3: Query Genérica
**Arquivo:** `hello_controller.py:63`

```python
default_prompt = "Documentos obrigatórios"
```

**Por que é um problema:**
- Query é apenas 2 palavras, muito genérica
- Não contextualiza:
  - "Estamos analisando um EDITAL DE LICITAÇÃO"
  - "Queremos uma LISTA completa"
  - "Queremos a SEÇÃO específica que lista quais documentos"
- Embedding não consegue diferenciar entre:
  - Seção 3.1 que diz "apresente os documentos obrigatórios"
  - Seção 5.2 que LISTA os documentos obrigatórios
  - Referência a "documentação obrigatória" em contexto diferente

#### RAIZ 4: Prompt da IA Genérico
**Arquivo:** `llm_service.py:21-30`

```python
prompt = f"""
Você é um assistente técnico especializado em analisar relatórios e documentos.
Responda à solicitação do usuário utilizando estritamente as informações fornecidas no contexto abaixo.

CONTEXTO DO RELATÓRIO:
{context_str}

SOLICITAÇÃO DO USUÁRIO:
{user_prompt}
"""
```

**Por que é um problema:**
- Prompt não é contextualizado para domínio jurídico
- Não instrui a IA para procurar por:
  - Listas numeradas
  - Seções específicas (ex: "Artigo X", "Capítulo Y")
  - Padrões de formatação típicos de editais
- Se os chunks recuperados são fragmentos isolados, a IA não consegue conectar as peças

#### RAIZ 5: Falta de Validação do Contexto
**Arquivo:** `vector_store_service.py:36-48`

```python
def search_similar_chunks(query: str, top_k: int = 4):
    results = collection.query(query_texts=[query], n_results=top_k)
    if results and results.get("documents"):
        return results["documents"][0]
    return []
```

**Por que é um problema:**
- Sempre retorna top_k=4 chunks
- Não verifica se a similaridade é REALMENTE alta
- Pode retornar chunks com baixa relevância se não houver chunk muito relevante
- Não há feedback de "confiança" da busca

#### RAIZ 6: Erro no Código
**Arquivo:** `chunker_service.py:3`

```python
def create_chunks(elements, chunk_size=1000, chunk_overlap=ana):  # ❌
```

- `ana` não é variável válida
- Deve ser um número, ex: `chunk_overlap=200`
- Isso pode estar causando erro silencioso ou chunk_overlap=None

---

## Phase 2: Pattern Analysis

### Padrão 1: Sistemas RAG para Domínios Específicos
- Precisam de embeddings treinados no domínio (domain-specific embeddings)
- Exemplo: Para contratos jurídicos, usar model treinado em jurisprudência
- Alternativa: Fine-tune sobre dados do domínio

### Padrão 2: Chunking para Documentos Estruturados
- Editais têm estrutura: artigos, incisos, seções, tabelas
- Chunking deve RESPEITAR essa estrutura
- Não quebrar no meio de listas
- Manter cabeçalhos com conteúdo relacionado

### Padrão 3: Queries Contextualizadas
- Sempre incluir contexto sobre o tipo de documento
- Ser específico: "Lista de documentos" > "Documentos"
- Usar o mesmo tipo de linguagem do documento (formal/jurídica)

### Padrão 4: Prompts Domain-Aware
- Instruir a IA sobre o formato esperado (lista, tabela, etc)
- Instruir a IA sobre características do domínio
- Pedir resposta estruturada (ex: JSON, markdown list)

---

## Resumo das Raízes

| Raiz | Camada | Severidade | Impacto |
|------|--------|------------|--------|
| Embedding genérico | Vector Store | 🔴 ALTA | Não entende editais, recupera chunks errados |
| Chunking quebra listas | Chunking | 🔴 ALTA | Fragmenta informação coerente |
| Query genérica | Application | 🟠 MÉDIA | Ambígua, não contextualizada |
| Prompt genérico | LLM | 🟠 MÉDIA | Não orienta a IA para domínio jurídico |
| Falta validação contexto | Vector Store | 🟡 BAIXA | Retorna resultados mesmo com pouca confiança |
| Erro em chunk_overlap | Chunking | 🟡 BAIXA | Pode causar comportamento indefinido |

---

## Hipótese de Teste

**Hipótese:** A causa PRINCIPAL é a combinação de embedding genérico + chunking inadequado.

**Predição:** Se melhorar APENAS o chunking, pode ajudar 30-40%.
Se melhorar APENAS o embedding, pode ajudar 40-50%.
Se melhorar ambos + query + prompt, pode resolver 90%+ do problema.
