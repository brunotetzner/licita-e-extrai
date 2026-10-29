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


def _normalizar_licitacao_search(item: dict[str, Any]) -> dict[str, Any]:
    """
    Convierte un item de la API de búsqueda de PNCP al formato Licitacao
    (snake_case) que espera el resto del codigo.

    La API /search/ ya devuelve items con claves snake_case compatibles;
    este mapeo selecciona y renombra los campos para que coincidan con el
    shape producido por ``_normalizar_licitacao_consulta``, de modo que el
    flujo downstream no se entere del origen de los datos.
    """
    ano = item.get("ano") or item.get("anoCompra")
    sequencial = item.get("numero_sequencial") or item.get("sequencialCompra")
    cnpj = item.get("orgao_cnpj") or item.get("cnpj")
    descricao = item.get("description") or item.get("objeto_compra")

    return {
        "id": item.get("id"),
        "title": item.get("title") or descricao,
        "description": descricao,
        "item_url": (
            f"/compras/{cnpj}/{ano}/{sequencial}"
            if cnpj and ano and sequencial is not None
            else None
        ),
        "document_type": "edital",
        "ano": str(ano) if ano is not None else None,
        "numero_sequencial": str(sequencial) if sequencial is not None else None,
        "numero_controle_pncp": item.get("numero_controle_pncp")
        or item.get("numeroControlePNCP"),
        "orgao_cnpj": cnpj,
        "orgao_nome": item.get("orgao_nome") or item.get("orgaoEntidade", {}).get("razaoSocial"),
        "modalidade_licitacao_nome": item.get("modalidade_licitacao_nome"),
        "municipio_nome": item.get("municipio_nome"),
        "data_publicacao_pncp": item.get("data_publicacao_pncp")
        or item.get("dataPublicacaoPncp"),
        "data_inicio_vigencia": item.get("data_inicio_vigencia")
        or item.get("dataAberturaProposta"),
        "data_fim_vigencia": item.get("data_fim_vigencia")
        or item.get("dataEncerramentoProposta"),
        "objeto_compra": descricao,
        "situacao_compra_nome": item.get("situacao_nome"),
    }


# Limites para o fallback pela API de busca (/search/).
MAX_PAGINAS_BUSCA = 5
TAM_PAGINA_BUSCA_Q = 10  # Estrategia 1 (q = numero de controle).
TAM_PAGINA_BUSCA_ANO = 100  # Estrategia 2 (filtro por ano).


def _normalizar_numero_controle(valor: Any) -> str:
    """
    Normaliza un numero de control para comparacion exacta.

    Alinea el formato de ambos lados con lo que hace la consulta individual:
    elimina ceros a la izquierda del secuencial de la compra. Asi un candidato
    proveniente de la busqueda con ``-1-023280/2026`` se compara igual al
    solicitado ``-1-23280/2026``.
    """
    import re

    texto = "".join(str(valor).split())
    match = re.fullmatch(r"(\d{8,14})-(\d+)-(\d+)/(\d{4})", texto)
    if not match:
        return texto
    return (
        f"{match.group(1)}-{int(match.group(2))}-"
        f"{int(match.group(3))}/{match.group(4)}"
    )


def _buscar_item_no_resultado(
    itens: list[dict[str, Any]],
    alvo_normalizado: str,
) -> dict[str, Any] | None:
    """Retorna o item cujo numero de controle coincide com o solicitado."""
    for item in itens:
        candidato = item.get("numero_controle_pncp")
        if candidato and _normalizar_numero_controle(candidato) == alvo_normalizado:
            return item
    return None


def _buscar_por_q(q: str, alvo_normalizado: str) -> dict[str, Any] | None:
    """
    Estrategia 1: busca passando o numero de controle no parametro ``q``.

    So retorna o item se houver coincidencia exata do numero de controle,
    mesma forma que a consulta individual.
    """
    for pagina in range(1, MAX_PAGINAS_BUSCA + 1):
        try:
            itens = _get_json(
                f"{PNCP_API_URL}/search/",
                params={
                    "q": q,
                    "tipos_documento": "edital",
                    "ordenacao": "-data",
                    "pagina": pagina,
                    "tam_pagina": TAM_PAGINA_BUSCA_Q,
                },
            )
        except requests.RequestException:
            # Tolerante: se esta estrategia falhar, cai para a proxima.
            return None

        item = _buscar_item_no_resultado(itens, alvo_normalizado)
        if item is not None:
            return item

        # Os resultados sao ordenados por data descrescente; se ja chegou a
        # licitacoes mais antigas que o ano do alvo nao ha mais o que procurar.
        if itens and int(itens[-1].get("ano") or 0) < int(
            alvo_normalizado.rsplit("/", 1)[1]
        ):
            break
    return None


def _buscar_por_ano(
    ano: str, alvo_normalizado: str
) -> dict[str, Any] | None:
    """
    Estrategia 2: pagina com 100 itens por pagina filtrando pelo ano.

    Usa somente o ano do numero de controle como termo e varre as paginas
    (ordenadas por data descrescente), ate encontrar o numero exato ou ate
    ultrapassar as licitacoes do ano informado.
    """
    for pagina in range(1, MAX_PAGINAS_BUSCA + 1):
        try:
            itens = _get_json(
                f"{PNCP_API_URL}/search/",
                params={
                    "q": ano,
                    "tipos_documento": "edital",
                    "ordenacao": "-data",
                    "pagina": pagina,
                    "tam_pagina": TAM_PAGINA_BUSCA_ANO,
                },
            )
        except requests.RequestException:
            return None

        item = _buscar_item_no_resultado(itens, alvo_normalizado)
        if item is not None:
            return item

        # Se a pagina ja saiu do ano alvo, a licitacao nao esta no indice.
        if itens and int(itens[-1].get("ano") or 0) < int(ano):
            break
    return None


def buscar_licitacao_por_numero_controle_via_search(
    numero_controle_pncp: str,
) -> Licitacao | None:
    """
    Busca una licitacion en la API de busqueda de PNCP filtrando por el
    numero de control.

    Estrategia 1: busca sacrificando el propio numero de control en ``q``.
    Si no encuentra, Estrategia 2: pagina con 100 itens por pagina filtrando
    solo por el ano del numero de control. En ambos casos solo se retorna la
    licitacion ante coincidencia exacta del numero de control, manteniendo el
    mismo shape ``Licitacao`` producido por la consulta individual.

    Args:
        numero_controle_pncp: Identificador unico de la licitacion en el PNCP.

    Returns:
        La licitacion encontrada o None si no existe en el indice de busqueda.
    """
    alvo = _normalizar_numero_controle(numero_controle_pncp)
    if not alvo:
        return None

    import re

    match = re.fullmatch(r"(\d{8,14})-(\d+)-(\d+)/(\d{4})", alvo)
    if not match:
        return None
    ano = match.group(4)
    cnpj = match.group(1)
    sequencial_compra = str(int(match.group(2)))
    sequencial = str(int(match.group(3)))

    # Estrategia 1: q = numero de controle completo, como fornecido.
    q_1 = f"{cnpj}-{sequencial_compra}-{sequencial}/{ano}"
    item = _buscar_por_q(q_1, alvo)
    print(item, q_1, alvo)
    if item is None:
        # Reforco usando apenas as partes que o indice costuma tokenizar bem.
        q_variancia = f"{cnpj} {ano} {sequencial}"
        item = _buscar_por_q(q_variancia, alvo)

    # Estrategia 2: pagina por ano caso nenhuma variante de ``q`` funcione.
    if item is None:
        item = _buscar_por_ano(ano, alvo)

    if item is None:
        return None

    return cast(Licitacao, _normalizar_licitacao_search(item))


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
            # A consulta individual pode retornar 404 quando a licitacao ainda
            # nao tem todos os dados publicados no PNCP. Nesse caso tenta
            # localizar pelo indice de busca antes de desistir.
            print(
                f"A consulta individual retornou HTTP "
                f"{response.status_code}; tentando fallback pela busca..."
            )
            return buscar_licitacao_por_numero_controle_via_search(
                numero_controle_pncp
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
    return cast(Licitacao, _normalizar_licitacao_consulta(payload))


def buscar_licitacao_arquivos(licitacao: Licitacao) -> list[ArquivoLicitacao]:
    try:
        cnpj = licitacao.get("orgao_cnpj")
        ano = licitacao.get("ano")
        sequencial = licitacao.get("numero_sequencial")
        if not cnpj or not ano or not sequencial:
            raise ValueError("Licitação sem órgão, ano ou número sequencial.")

        payload = _get_json(
            f"{PNCP_API_URL}/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos",
            params={"pagina": 1, "tamanhoPagina": 5},
        )
    except requests.RequestException as error:
        print(f"Erro ao buscar arquivos da licitação {licitacao.get('numero_controle')}: {error}")
        raise
    return cast(list[ArquivoLicitacao], payload)

def buscar_editais(licitacao: Licitacao) -> list[ArquivoLicitacao]:
    arquivos = buscar_licitacao_arquivos(licitacao)
    print('arquivo', arquivos)
    termos_referencia = [
        arquivo
        for arquivo in arquivos
        if arquivo.get("tipoDocumentoNome", "").casefold()
        == "termo de referência"
    ]

    if termos_referencia:
        return termos_referencia

    edital = [
        arquivo
        for arquivo in arquivos
        if arquivo.get("tipoDocumentoNome", "").casefold() == "edital"
    ]
    if edital:
        return edital

    return [arquivos[0]]

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