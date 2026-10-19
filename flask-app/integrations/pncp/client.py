from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict, cast

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from integrations.pncp.config import PNCP_API_URL, PNCP_COOKIE, REQUEST_TIMEOUT_SECONDS


PNCP_HEADERS: dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    # "Cookie": PNCP_COOKIE,
}


class Licitacao(TypedDict, total=False):
    id: str
    title: str
    description: str
    item_url: str
    document_type: str
    ano: str
    numero_sequencial: str
    numero_controle_pncp: str
    orgao_cnpj: str
    orgao_nome: str


class ArquivoLicitacao(TypedDict, total=False):
    uri: str
    url: str
    tipoDocumentoId: int
    statusAtivo: bool
    cnpj: str
    anoCompra: int
    sequencialCompra: int
    sequencialDocumento: int
    titulo: str
    tipoDocumentoNome: str
    tipoDocumentoDescricao: str


def _create_http_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(
        {
            nome: valor
            for nome, valor in PNCP_HEADERS.items()
            if valor
        }
    )
    session.mount("https://", adapter)
    return session


def _get_json(url: str, *, params: dict[str, Any]) -> list[dict[str, Any]]:
    response: requests.Response | None = None
    try:
        with _create_http_session() as session:
            response = session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        print(
            f"Erro na requisição HTTP para {url} "
            f"(status={getattr(response, 'status_code', 'desconhecido')}): {error}"
        )
        raise
    except ValueError as error:
        print(
            f"Resposta não-JSON do PNCP para {url} "
            f"(status={getattr(response, 'status_code', 'desconhecido')}): "
            f"{getattr(response, 'text', '')[:1000]}"
        )
        raise ValueError(f"Resposta inválida da API do PNCP: {url}") from error

    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    else:
        print(
            f"Resposta inesperada do PNCP para {url} "
            f"(status={response.status_code}): {response.text[:1000]}"
        )
        raise ValueError(f"Resposta inesperada da API do PNCP: {url}")

    if not all(isinstance(item, dict) for item in items):
        print(
            f"Itens inválidos na resposta do PNCP para {url}: "
            f"{getattr(response, 'text', '')[:1000]}"
        )
        raise ValueError(f"Itens inválidos na resposta da API do PNCP: {url}")

    return cast(list[dict[str, Any]], items)


def buscar_licitacoes(pagina: int = 1) -> list[Licitacao]:
    payload = _get_json(
        f"{PNCP_API_URL}/search/",
        params={
            "tipos_documento": "edital",
            "ordenacao": "-data",
            "pagina": pagina,
            "tam_pagina": 10,
            "status": "recebendo_proposta",
        },
    )
    return cast(list[Licitacao], payload)


def _normalizar_licitacao_consulta(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Convierte el payload de la API de consulta individual del PNCP (camelCase)
    al formato Licitacao (snake_case) que espera el resto del codigo.
    """
    orgao = payload.get("orgaoEntidade") or {}
    unidade = payload.get("unidadeOrgao") or {}
    ano = payload.get("anoCompra")
    sequencial = payload.get("sequencialCompra")

    return {
        "id": payload.get("id"),
        "title": payload.get("objetoCompra"),
        "description": payload.get("objetoCompra"),
        "item_url": (
            f"/compras/{orgao.get('cnpj')}/{ano}/{sequencial}"
            if orgao.get("cnpj") and ano and sequencial
            else None
        ),
        "document_type": "edital",
        "ano": str(ano) if ano is not None else None,
        "numero_sequencial": str(sequencial) if sequencial is not None else None,
        "numero_controle_pncp": payload.get("numeroControlePNCP"),
        "orgao_cnpj": orgao.get("cnpj"),
        "orgao_nome": orgao.get("razaoSocial"),
        "modalidade_licitacao_nome": payload.get("modalidadeNome"),
        "municipio_nome": unidade.get("municipioNome"),
        "data_publicacao_pncp": payload.get("dataPublicacaoPncp"),
        "data_inicio_vigencia": payload.get("dataAberturaProposta"),
        "data_fim_vigencia": payload.get("dataEncerramentoProposta"),
        "objeto_compra": payload.get("objetoCompra"),
        "situacao_compra_nome": payload.get("situacaoCompraNome"),
    }


def buscar_licitacao_por_numero_controle(
    numero_controle_pncp: str,
) -> Licitacao | None:
    """
    Busca uma licitação específica no PNCP pelo seu número de controle.

    O número de controle tem o formato ``{cnpj}-{seq}-{ano}``, por exemplo
    ``45116092000108-1-000124/2026``. A API de consulta individual foi movida
    a ``/consulta/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}``.

    Args:
        numero_controle_pncp: Identificador único da licitação no PNCP.

    Returns:
        A licitação encontrada ou None se não existir.
    """
    # Formato: {cnpj}-{seq_compra}-{sequencial}/{ano}
    # Ej: 45116092000108-1-000124/2026
    import re

    match = re.fullmatch(
        r"(\d{8,14})-(\d+)-(\d+)/(\d{4})",
        numero_controle_pncp.strip(),
    )
    if not match:
        raise ValueError(
            f"Número de controle inválido: {numero_controle_pncp!r}"
        )
    cnpj = match.group(1)
    sequencial = str(int(match.group(3)))
    ano = match.group(4)

    url = (
        f"{PNCP_API_URL}/consulta/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}"
    )
    print(url)
    try:
        with _create_http_session() as session:
            response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code in (400, 404):
            print('ERROR 400 OR 404')
            return None
        
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        print(
            f"Erro na requisição HTTP para {url} "
            f"(status={getattr(response, 'status_code', 'desconhecido')}): {error}"
        )
        raise
    except ValueError as error:
        print(
            f"Resposta não-JSON do PNCP para {url}: "
            f"{getattr(response, 'text', '')[:1000]}"
        )
        raise ValueError(f"Resposta inválida da API do PNCP: {url}") from error

    if not isinstance(payload, dict):
        print(
            f"Resposta inesperada do PNCP para {url}: "
            f"{getattr(response, 'text', '')[:1000]}"
        )
        raise ValueError(f"Resposta inesperada da API do PNCP: {url}")
    print('FIM', payload)
    return cast(Licitacao, _normalizar_licitacao_consulta(payload))


def buscar_licitacao_arquivos(licitacao: Licitacao) -> list[ArquivoLicitacao]:
    cnpj = licitacao.get("orgao_cnpj")
    ano = licitacao.get("ano")
    sequencial = licitacao.get("numero_sequencial")
    if not cnpj or not ano or not sequencial:
        raise ValueError("Licitação sem órgão, ano ou número sequencial.")

    payload = _get_json(
        f"{PNCP_API_URL}/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos",
        params={"pagina": 1, "tamanhoPagina": 5},
    )
    return cast(list[ArquivoLicitacao], payload)

def buscar_editais(licitacao: Licitacao) -> list[ArquivoLicitacao]:
    arquivos = buscar_licitacao_arquivos(licitacao)

    termos_referencia = [
        arquivo
        for arquivo in arquivos
        if arquivo.get("tipoDocumentoNome", "").casefold()
        == "termo de referência"
    ]

    if termos_referencia:
        return termos_referencia

    return [
        arquivo
        for arquivo in arquivos
        if arquivo.get("tipoDocumentoNome", "").casefold() == "edital"
    ]

def baixar_pdf(arquivo: ArquivoLicitacao, destino: Path) -> None:
    url = arquivo.get("url") or arquivo.get("uri")
    if not url:
        raise ValueError("Arquivo do PNCP sem URL para download.")

    try:
        with _create_http_session() as session:
            with session.get(
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                stream=True,
            ) as response:
                response.raise_for_status()
                with destino.open("wb") as pdf:
                    for bloco in response.iter_content(chunk_size=1024 * 1024):
                        if bloco:
                            pdf.write(bloco)
    except requests.RequestException as error:
        print(f"Erro ao baixar o PDF {url}: {error}")
        raise