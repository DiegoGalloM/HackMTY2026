"""
Base de conocimiento del asistente (la parte "RAG").

Contenido de educación financiera para micro-negocios (basado en el material
que ya usa la app: FDIC Money Smart, SBA, CFPB) más el contexto que el dueño
dio en el onboarding. Recuperación léxica sencilla y determinista: sin
vectores, sin servicio externo, y con papel claro: EXPLICA conceptos. Nunca
calcula ventas ni saldos; eso es del motor financiero.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "liquidez",
        "title": "Liquidez y razón circulante",
        "tags": "liquidez liquidity razon circulante current ratio corto plazo deudas pagar pronto solvencia",
        "lesson": "cash",
        "text": (
            "La liquidez es qué tan fácil puedes pagar lo que debes pronto con lo que tienes a la mano. "
            "La razón circulante compara tus recursos a corto plazo (efectivo, lo que te deben, inventario) con "
            "tus deudas a corto plazo (tarjeta, proveedores, impuestos). Arriba de 1.5 vas cómodo; entre 1 y 1.5 "
            "vigila; debajo de 1 significa que si todo se cobrara hoy no alcanzaría. Para un micro-negocio, tener "
            "un colchón de 2 a 4 semanas de gastos en efectivo es la regla práctica."
        ),
    },
    {
        "id": "prueba_acida",
        "title": "Prueba ácida (quick ratio)",
        "tags": "prueba acida quick ratio inventario efectivo cobrar",
        "lesson": "cash",
        "text": (
            "La prueba ácida es la liquidez sin contar el inventario, porque el inventario todavía hay que venderlo. "
            "Suma efectivo y cuentas por cobrar y divídelo entre lo que debes pronto. Si es menor a 1, dependes de "
            "vender inventario para pagar tus deudas cercanas."
        ),
    },
    {
        "id": "capital_trabajo",
        "title": "Capital de trabajo",
        "tags": "capital de trabajo working capital operar dinero disponible circulante",
        "lesson": "cash",
        "text": (
            "El capital de trabajo es lo que te queda después de restar tus deudas a corto plazo de tus recursos a "
            "corto plazo. Es el dinero con el que realmente operas: compras insumos, pagas ayudantes y aguantas los "
            "días flojos. Si es negativo, estás financiando la operación con la tarjeta o con proveedores, y cualquier "
            "retraso en ventas se vuelve un problema de pagos."
        ),
    },
    {
        "id": "margen_bruto",
        "title": "Margen bruto",
        "tags": "margen bruto gross margin ganancia por venta costo de ventas insumos precio",
        "lesson": "margin",
        "text": (
            "El margen bruto es lo que te queda de cada venta después de pagar SOLO los insumos directos de ese "
            "producto (harina, huevo, tinte, material). No incluye renta ni sueldos. Un margen bruto bajo casi "
            "siempre viene de precios que no se actualizaron cuando subieron los insumos, o de recetas que usan más "
            "de lo que cobras. Revisa primero tus productos más vendidos: ahí un cambio pequeño de precio o de "
            "receta mueve más dinero."
        ),
    },
    {
        "id": "margen_neto",
        "title": "Margen neto y utilidad",
        "tags": "margen neto net margin utilidad ganancia profit gastos fijos renta",
        "lesson": "margin",
        "text": (
            "El margen neto es la ganancia real después de TODOS los gastos: insumos, renta, luz, sueldos, "
            "comisiones, depreciación. Puedes vender mucho y tener margen neto negativo si los gastos fijos son "
            "altos para tu volumen. Cuando la utilidad baja, separa tres causas: vendiste menos, los insumos "
            "costaron más, o los gastos fijos subieron."
        ),
    },
    {
        "id": "costo_ventas",
        "title": "Costo de ventas y costo promedio",
        "tags": "costo de ventas cogs costo promedio ponderado receta inventario consumo",
        "lesson": "margin",
        "text": (
            "El costo de ventas es lo que costaron los insumos de lo que vendiste. Capital One Business lo calcula "
            "solo: cada producto tiene una receta, y al pagarse una venta se descuentan los insumos a su costo "
            "promedio ponderado (el promedio de lo que pagaste en tus compras). Si un proveedor te sube el precio, "
            "el costo promedio sube poco a poco conforme repones inventario, y tu margen baja aunque vendas igual."
        ),
    },
    {
        "id": "inventario",
        "title": "Inventario: efectivo que espera",
        "tags": "inventario inventory rotacion dias sobrecompra comprar de mas exceso almacen atrapado mermas",
        "lesson": "inventory",
        "text": (
            "Todo lo que tienes guardado sin vender es dinero que ya gastaste y que no puedes usar. La rotación dice "
            "cuántas veces vendiste tu inventario en un periodo; los días de inventario dicen cuánto tarda un insumo "
            "en salir. En comida, más de 10 a 15 días suele significar sobrecompra y merma; en retail, 30 a 60 días "
            "puede ser normal. Comprar al mayoreo sólo conviene si el ahorro es mayor que el costo de tener el "
            "efectivo congelado semanas."
        ),
    },
    {
        "id": "punto_reorden",
        "title": "Punto de reorden",
        "tags": "punto de reorden reorder stockout quedarse sin stock agotar pedir proveedor tiempo de entrega",
        "lesson": "inventory",
        "text": (
            "El punto de reorden es la cantidad a la que debes volver a pedir. Se calcula con lo que consumes por "
            "día multiplicado por los días que tarda tu proveedor, más un colchón pequeño. Quedarte sin un insumo "
            "que sí se vende es dinero que dejaste de ganar; en la app puedes fijar el punto de reorden por insumo "
            "y te avisamos cuando lo tocas."
        ),
    },
    {
        "id": "flujo_efectivo",
        "title": "Flujo de efectivo",
        "tags": "flujo de efectivo cash flow entradas salidas caja semana pagos cobros",
        "lesson": "cash",
        "text": (
            "El flujo de efectivo es lo que entra y sale de tu caja y tu banco en un periodo. Es distinto de la "
            "utilidad: puedes tener utilidad y quedarte sin efectivo si compraste mucho inventario o si te pagan "
            "tarde. La regla práctica: mira cada semana lo que entrará, lo que debes pagar y con cuánto cierras."
        ),
    },
    {
        "id": "deuda",
        "title": "Deuda, tarjeta de negocio y apalancamiento",
        "tags": "deuda apalancamiento leverage tarjeta credito intereses debt to equity pasivo",
        "lesson": "cash",
        "text": (
            "Usar la tarjeta de negocio para las compras es útil porque cada compra queda registrada automáticamente "
            "y separas lo personal de lo del negocio. La deuda sobre capital compara lo que debes con lo que es tuyo; "
            "arriba de 1 significa que hay más dinero de otros que tuyo en el negocio. Paga la tarjeta completa cada "
            "mes: los intereses son un gasto que no produce nada."
        ),
    },
    {
        "id": "impuesto_ventas",
        "title": "Impuesto sobre ventas",
        "tags": "impuesto sobre ventas sales tax cobrar impuesto pasivo pagar al estado",
        "lesson": "cash",
        "text": (
            "El impuesto que cobras en cada venta NO es ingreso tuyo: lo recibes para entregarlo al estado. Por eso "
            "en tus libros aparece como una deuda (impuesto por pagar) y no como venta. Sepáralo mentalmente del "
            "efectivo disponible para no gastarlo."
        ),
    },
    {
        "id": "cuentas_cobrar",
        "title": "Cuentas por cobrar",
        "tags": "cuentas por cobrar receivables fiado anticipo cobrar despues clientes deben",
        "lesson": "cash",
        "text": (
            "Una venta no es dinero hasta que te pagan. Si trabajas y cobras después, ese trabajo ya hecho es una "
            "cuenta por cobrar: aparece como recurso pero no lo puedes gastar. Pedir un anticipo o cobrar por avances "
            "cambia mucho tu flujo de efectivo aunque vendas lo mismo."
        ),
    },
    {
        "id": "depreciacion",
        "title": "Depreciación y equipo",
        "tags": "depreciacion equipo horno maquina activo fijo ajuste",
        "lesson": "margin",
        "text": (
            "Cuando compras equipo (un horno, una batidora, herramienta) no es un gasto del mes: es un activo que "
            "usarás años. La depreciación reparte su costo en el tiempo con un asiento de ajuste mensual, así tu "
            "utilidad refleja el desgaste real y no un golpe de un solo mes."
        ),
    },
    {
        "id": "retiros",
        "title": "Retiros del dueño y compras personales",
        "tags": "retiro del dueño personal compra personal owner draw capital separar dinero",
        "lesson": "cash",
        "text": (
            "Lo que sacas del negocio para ti (o una compra personal con la tarjeta del negocio) no es un gasto del "
            "negocio: es un retiro del dueño y reduce tu capital. Registrarlo así evita que tu utilidad se vea peor "
            "de lo que es y mantiene claro cuánto vale realmente tu negocio."
        ),
    },
    {
        "id": "precio",
        "title": "Cómo fijar precios con margen",
        "tags": "precio pricing fijar precios cuanto cobrar margen objetivo costo",
        "lesson": "margin",
        "text": (
            "Un precio sano cubre el costo directo del producto, deja margen para los gastos fijos y todavía "
            "gana. Regla rápida: precio = costo directo ÷ (1 − margen bruto objetivo). Si tu pastel cuesta $8 en "
            "insumos y quieres 60% de margen bruto, el precio mínimo es $20. Revisa precios cada vez que un insumo "
            "clave suba más de 10%."
        ),
    },
]

_STOP = {"de", "la", "el", "los", "las", "un", "una", "y", "o", "en", "por", "para", "con", "del", "al", "que", "como", "es", "mi", "mis", "tu", "tus", "se", "lo", "the", "a", "an", "of", "to", "in", "on", "for", "and", "is", "are", "my", "what", "how"}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", _norm(text))
    return [w[:6] for w in words if w not in _STOP and len(w) > 2]


def search(query: str, extra_documents: list[dict[str, Any]] | None = None, k: int = 3) -> list[dict[str, Any]]:
    """Documentos ordenados por coincidencia de términos. `extra_documents`
    permite sumar el contexto del negocio (perfil del onboarding)."""
    q = set(tokens(query))
    if not q:
        return []
    scored = []
    for doc in [*DOCUMENTS, *(extra_documents or [])]:
        doc_tokens = tokens(f"{doc['title']} {doc.get('tags', '')} {doc['text']}")
        tag_tokens = set(tokens(f"{doc['title']} {doc.get('tags', '')}"))
        overlap = q & set(doc_tokens)
        if not overlap:
            continue
        score = len(overlap) + 2 * len(q & tag_tokens)
        scored.append((score, doc))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [{**doc, "score": score} for score, doc in scored[:k]]


def business_context_documents(profile: dict[str, Any] | None, business_name: str | None) -> list[dict[str, Any]]:
    """El perfil del onboarding como documentos consultables."""
    if not profile:
        return []
    docs = []
    week = profile.get("week_description_text")
    if week:
        docs.append({"id": "profile_week", "title": "Lo que contaste de tu semana", "tags": "semana normal rutina contar dije negocio", "text": week, "source": "onboarding"})
    answers = profile.get("answers") or {}
    yes = [k.replace("_", " ") for k, v in answers.items() if v]
    docs.append(
        {
            "id": "profile_summary",
            "title": f"Perfil de {business_name or 'tu negocio'}",
            "tags": "perfil negocio categoria giro ciudad empleados dias",
            "text": (
                f"Giro: {profile.get('category')}{(' (' + profile['category_detail'] + ')') if profile.get('category_detail') else ''}. "
                f"Ciudad: {profile.get('city')}. Equipo: {profile.get('employees')}. "
                f"Días de operación: {', '.join(profile.get('operating_days') or [])}. "
                f"Respondiste que sí a: {', '.join(yes) if yes else 'ninguna pregunta'}."
            ),
            "source": "onboarding",
        }
    )
    return docs
