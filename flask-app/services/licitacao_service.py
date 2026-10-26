from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TypedDict

import requests

from integrations.pncp import (
    ArquivoLicitacao,
    Licitacao,
    baixar_pdf,
    buscar_editais,
    buscar_licitacao_por_numero_controle,
    buscar_licitacoes,
)
from internal_services.archivo_utils import extraer_pdfs
from internal_services.rag_service import process_pdf
from repositories import (
    LicitacaoDocumento,
    buscar_por_id,
    listar_licitacoes,
    salvar_licitacao,
)
from repositories.config import (
    ASYNC_LICITATION_SUMMARY_ENABLED,
    GITHUB_ACTIONS_REF,
    GITHUB_ACTIONS_REPOSITORY,
    GITHUB_ACTIONS_TOKEN,
)

MAX_LICITACOES = 3
MAX_PAGINAS = 10


class ResultadoAnaliseLicitacao(TypedDict):
    licitacao: Licitacao
    arquivo: ArquivoLicitacao
    resumo_edital: list[str]
    status: str


def _licitacao_ja_processada(licitacao: Licitacao) -> bool:
    """Verifica si la licitacion ya fue procesada en la base."""
    nc = licitacao.get("numero_controle_pncp")
    if not nc:
        return False
    return buscar_por_id(nc) is not None


def _analizar_editais(
    licitacao: Licitacao,
    arquivo: ArquivoLicitacao,
) -> list[str]:
    """
    Descarga el archivo de una licitacion, extrae los PDFs (descomprimiendo
    RAR/ZIP si es necesario) y los analiza con el agente RAG.

    Args:
        licitacao: Datos de la licitacion.
        arquivo: Archivo (edital/termo de referencia) a analizar.

    Returns:
        list[str]: Respuestas generadas por el agente RAG.
    """
    archivo_path: Path | None = None
    dir_extraccion: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="pncp_",
            suffix=".bin",
            delete=False,
        ) as temporario:
            archivo_path = Path(temporario.name)

        print(f"Baixando arquivo para {archivo_path, arquivo}...")
        baixar_pdf(arquivo, archivo_path)

        # Extraer PDFs (descomprime RAR/ZIP si es necesario)
        dir_extraccion = Path(tempfile.mkdtemp(prefix="pncp_extraer_"))
        pdfs = extraer_pdfs(archivo_path, dir_extraccion)
        print(f"PDFs encontrados: {[p.name for p in pdfs]}")

        respuestas: list[str] = []
        for pdf in pdfs:
            respuestas.extend(analisar_pdf(str(pdf)))
        return respuestas
    finally:
        if archivo_path is not None:
            archivo_path.unlink(missing_ok=True)
        if dir_extraccion is not None:
            shutil.rmtree(dir_extraccion, ignore_errors=True)


def _disparar_action_processar_resumo(numero_controle_pncp: str) -> None:
    """
    Dispara o workflow do GitHub Actions que processa o resumo da licitação.

    Args:
        numero_controle_pncp: Identificador da licitação já salva no MongoDB.
    """
    if not GITHUB_ACTIONS_TOKEN:
        raise RuntimeError(
            "GITHUB_ACTIONS_TOKEN não foi configurado no ambiente."
        )

    url = (
        f"https://api.github.com/repos/{GITHUB_ACTIONS_REPOSITORY}"
        "/actions/workflows/processar-resumo.yml/dispatches"
    )
    response = requests.post(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_ACTIONS_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "ref": GITHUB_ACTIONS_REF,
            "inputs": {"numero_controle_pncp": numero_controle_pncp},
        },
        timeout=10,
    )
    if response.status_code != 204:
        raise RuntimeError(
            "GitHub Actions rejeitou o disparo do workflow "
            f"(HTTP {response.status_code})."
        )
    print(
        f"Workflow de resumo disparado para a licitação "
        f"{numero_controle_pncp}."
    )


def get_licitacoes() -> list[ResultadoAnaliseLicitacao]:
    """Busca tres licitacoes NAO processadas e analisa seus editais."""
    resultados: list[ResultadoAnaliseLicitacao] = []
    pagina = 1

    while len(resultados) < MAX_LICITACOES and pagina <= MAX_PAGINAS:
        licitacoes = buscar_licitacoes(pagina=pagina)

        if not licitacoes:
            break

        print(f"+++++ LICITACOES ENCONTRADAS (pagina {pagina}) +++++")
        print(licitacoes)

        for licitacao in licitacoes:
            if len(resultados) >= MAX_LICITACOES:
                break

            numero_controle = licitacao.get("numero_controle_pncp")
            if not numero_controle:
                continue

            if _licitacao_ja_processada(licitacao):
                print(
                    f"Licitacao {numero_controle} ja processada, descartando..."
                )
                continue

            editais = buscar_editais(licitacao)

            for arquivo in editais:
                documento: LicitacaoDocumento = {
                    "numero_controle_pncp": numero_controle,
                    "licitacao": dict(licitacao),
                    "arquivo": dict(arquivo),
                    "resumo_edital": [],
                    "status": "PENDENTE",
                }
                if not salvar_licitacao(documento):
                    raise RuntimeError(
                        f"Não foi possível salvar a licitação {numero_controle}."
                    )

                if ASYNC_LICITATION_SUMMARY_ENABLED:
                    _disparar_action_processar_resumo(numero_controle)
                    return resultados

                respuestas = _analizar_editais(licitacao, arquivo)

                documento: LicitacaoDocumento = {
                    "numero_controle_pncp": numero_controle,
                    "licitacao": dict(licitacao),
                    "arquivo": dict(arquivo),
                    "resumo_edital": respuestas,
                    "status": "PROCESSADO",
                }
                salvar_licitacao(documento)

                resultados.append(
                    {
                        "licitacao": licitacao,
                        "arquivo": arquivo,
                        "resumo_edital": respuestas,
                        "status": "PROCESSADO",
                    }
                )

        pagina += 1

    print(f"+++++ TOTAL DE {len(resultados)} LICITACOES PROCESSADAS +++++")
    return resultados


def analisar_pdf(pdf_path: str, perguntas: list[str] | None = None) -> list[str]:
    """
    Recebe o caminho de um PDF, delega ao servico RAG e retorna as respostas.

    Args:
        pdf_path: Caminho absoluto ou relativo para o arquivo PDF.
        perguntas: Lista opcional de perguntas. Se None, usa as padrao.

    Returns:
        list[str]: Respostas geradas pelo agente RAG.
    """
    return process_pdf(pdf_path, perguntas)


def analizar_licitacao_por_id(
    numero_controle_pncp: str,
) -> ResultadoAnaliseLicitacao | None:
    """
    Analisa uma licitacao especifica pelo numero de control.

    Se a licitacao ja existe no MongoDB, retorna o documento salvo sem
    re-processar. Caso contrario, busca no PNCP, descarga e analisa seus
    editais, guarda o resultado no MongoDB e o retorna.

    Args:
        numero_controle_pncp: Identificador unico da licitacao no PNCP.

    Returns:
        Resultado da analise ou None se a licitacao nao existe no PNCP.
    """
    # Se ja foi processada, retorna o documento salvo sem re-analisar.
    documento_existente = buscar_por_id(numero_controle_pncp)
    if documento_existente is not None:
        print(
            f"Licitacao {numero_controle_pncp} ja processada, "
            "retornando do banco..."
        )
        # Documentos antigos usam "respostas"; os novos usam "resumo_edital".
        resumo = documento_existente.get("resumo_edital") or documento_existente.get(
            "respostas", []
        )
        return {
            "licitacao": documento_existente.get("licitacao", {}),
            "arquivo": documento_existente.get("arquivo", {}),
            "resumo_edital": resumo,
            "status": documento_existente.get("status") or (
                "PROCESSADO" if resumo else "PENDENTE"
            ),
        }
    licitacao = buscar_licitacao_por_numero_controle(numero_controle_pncp)
    if licitacao is None:
        return None

    editais = buscar_editais(licitacao)
    if not editais:
        print(
            f"Licitacao {numero_controle_pncp} sem editais/termos de referencia."
        )
        return None

    arquivo = editais[0]

    documento_pendente: LicitacaoDocumento = {
        "numero_controle_pncp": numero_controle_pncp,
        "licitacao": dict(licitacao),
        "arquivo": dict(arquivo),
        "resumo_edital": [],
        "status": "PENDENTE",
    }
    if not salvar_licitacao(documento_pendente):
        raise RuntimeError(
            f"Não foi possível salvar a licitação {numero_controle_pncp}."
        )

    if ASYNC_LICITATION_SUMMARY_ENABLED:
        _disparar_action_processar_resumo(numero_controle_pncp)

        return {
            "licitacao": licitacao,
            "arquivo": arquivo,
            "resumo_edital": [],
            "status": "PENDENTE",
        }

    responses = _analizar_editais(licitacao, arquivo)

    documento: LicitacaoDocumento = {
        "numero_controle_pncp": numero_controle_pncp,
        "licitacao": dict(licitacao),
        "arquivo": dict(arquivo),
        "resumo_edital": responses,
        "status": "PROCESSADO",
    }
    if not salvar_licitacao(documento):
        raise RuntimeError(
            f"Não foi possível salvar o resumo da licitação "
            f"{numero_controle_pncp}."
        )

    return {
        "licitacao": licitacao,
        "arquivo": arquivo,
        "resumo_edital": responses,
        "status": "PROCESSADO",
    }


def processar_resumo_edital(dados: dict) -> dict:
    """
    Processa o resumo do edital de forma assincrona: baixa o PDF, extrai,
    analisa com RAG e atualiza o MongoDB com o resultado.

    Args:
        dados: Dicionario com 'numero_controle_pncp', 'licitacao' e 'arquivo'.

    Returns:
        Dict com o resultado da analise.
    """
    numero_controle_pncp = dados["numero_controle_pncp"]
    licitacao = dados["licitacao"]
    arquivo = dados["arquivo"]

    print(f"Processando resumo do edital {numero_controle_pncp}...")
    responses = _analizar_editais(licitacao, arquivo)

    documento: LicitacaoDocumento = {
        "numero_controle_pncp": numero_controle_pncp,
        "licitacao": dict(licitacao),
        "arquivo": dict(arquivo),
        "resumo_edital": responses,
        "status": "PROCESSADO",
    }
    if not salvar_licitacao(documento):
        raise RuntimeError(
            f"Não foi possível salvar o resumo da licitação "
            f"{numero_controle_pncp}."
        )

    print(f"Resumo do edital {numero_controle_pncp} processado com sucesso.")
    return {
        "licitacao": licitacao,
        "arquivo": arquivo,
        "resumo_edital": responses,
        "status": "PROCESSADO",
    }


def listar_licitacoes_guardadas(
    *,
    page: int = 1,
    page_size: int = 10,
    numero_controle_pncp: str | None = None,
) -> dict:
    """
    Lista licitaciones guardadas en MongoDB con paginacion y filtro opcional.

    Args:
        page: Numero de pagina (1-based).
        page_size: Tamano de la pagina.
        numero_controle_pncp: Filtro opcional por numero de control PNCP.

    Returns:
        Dict con 'items', 'page', 'page_size', 'total' y 'total_pages'.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    documentos, total = listar_licitacoes(
        page=page,
        page_size=page_size,
        numero_controle_pncp=numero_controle_pncp,
    )

    return {
        "items": documentos,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }
