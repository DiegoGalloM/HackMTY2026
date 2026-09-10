"""
Placeholder para la capa de "inteligencia" del proyecto — sea cual sea la
idea final, casi cualquier versión de "herramienta financiera inteligente"
necesita algo que convierta transacciones crudas en una recomendación o
alerta. Aquí es donde entraría Gemini/Claude, según lo que el equipo elija.

Ejemplo de forma de output pensado para que un frontend (web o escritorio)
lo pueda renderizar directo, sin parsear texto libre:

    {
        "summary": "Gastaste 18% más en comida este mes que el promedio.",
        "severity": "warning",  # info | warning | alert
        "suggested_action": "Revisa tus compras en restaurantes.",
    }
"""

from typing import Any


async def analyze_transactions(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    # TODO: reemplazar con una llamada real a Gemini/Claude una vez que el
    # equipo decida el ángulo del producto (alertas, metas compartidas,
    # simulador de decisiones, etc.)
    total = sum(tx.get("amount", 0.0) for tx in transactions)
    return {
        "summary": f"Analizadas {len(transactions)} transacciones por un total de ${total:,.2f}.",
        "severity": "info",
        "suggested_action": None,
    }
