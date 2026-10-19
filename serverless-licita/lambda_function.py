"""Lambda handler para gerar o resumo do edital e salvar no MongoDB.

Recebe o payload encaminhado pelo Flask (numero_controle_pncp, licitacao e
arquivo), chama ``_analizar_editais`` para extrair as informacoes do edital
via RAG e depois ``salvar_licitacao`` para persistir o resultado no MongoDB.
"""
from __future__ import annotations

from typing import Any

from services.licitacao_service import _analizar_editais
from repositories import LicitacaoDocumento, salvar_licitacao


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Ponto de entrada da lambda.

    Args:
        event: Payload com 'numero_controle_pncp', 'licitacao' e 'arquivo'.
        context: Contexto de execucao da AWS Lambda (nao utilizado).

    Returns:
        Dict com o resultado da analise e o status do salvamento.
    """
    numero_controle_pncp = event.get("numero_controle_pncp")
    licitacao = event.get("licitacao")
    arquivo = event.get("arquivo")

    if not numero_controle_pncp or not licitacao or not arquivo:
        raise ValueError(
            "Payload invalido: 'numero_controle_pncp', 'licitacao' e "
            "'arquivo' sao obrigatorios."
        )

    print(
        f"Processando licitacao {numero_controle_pncp} na lambda..."
    )

    respostas = _analizar_editais(licitacao, arquivo)

    documento: LicitacaoDocumento = {
        "numero_controle_pncp": numero_controle_pncp,
        "licitacao": dict(licitacao),
        "arquivo": dict(arquivo),
        "resumo_edital": respostas,
    }
    salvo = salvar_licitacao(documento)

    return {
        "numero_controle_pncp": numero_controle_pncp,
        "resumo_edital": respostas,
        "salvo": salvo,
    }
