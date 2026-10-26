from __future__ import annotations

import os

from repositories import buscar_por_id
from services.licitacao_service import processar_resumo_edital


def main() -> None:
    for variable in ("MONGO_URI", "OPENROUTER_API_KEY"):
        if not os.getenv(variable):
            raise RuntimeError(
                f"A variável obrigatória {variable} não foi definida."
            )

    numero_controle_pncp = os.environ["NUMERO_CONTROLE_PNCP"].strip()
    if not numero_controle_pncp:
        raise ValueError("NUMERO_CONTROLE_PNCP não pode ser vazio.")

    documento = buscar_por_id(numero_controle_pncp)
    if documento is None:
        raise LookupError(
            f"Licitação {numero_controle_pncp} não encontrada no MongoDB."
        )
    if documento.get("status") != "PENDENTE":
        raise ValueError(
            f"Licitação {numero_controle_pncp} não está PENDENTE; "
            f"status atual: {documento.get('status', 'ausente')}."
        )

    licitacao = documento.get("licitacao")
    arquivo = documento.get("arquivo")
    if not isinstance(licitacao, dict) or not isinstance(arquivo, dict):
        raise ValueError(
            f"Licitação {numero_controle_pncp} não possui dados "
            "de licitação e arquivo válidos."
        )

    processar_resumo_edital(
        {
            "numero_controle_pncp": numero_controle_pncp,
            "licitacao": licitacao,
            "arquivo": arquivo,
        }
    )


if __name__ == "__main__":
    main()
