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

# Versión en inglés de cada documento: el asistente detecta el idioma de la
# pregunta y antes respondía "What is gross margin?" en español. Mismo contenido
# y mismas cifras de ejemplo que el texto en español. Un test exige que ningún
# documento se quede sin traducción.
EN: dict[str, tuple[str, str]] = {
    "liquidez": (
        "Liquidity and the current ratio",
        (
            "Liquidity is how easily you can pay what you owe soon with what you have on hand. The current ratio "
            "compares your short-term resources (cash, what customers owe you, inventory) with your short-term debts "
            "(card, suppliers, taxes). Above 1.5 you are comfortable; between 1 and 1.5, keep an eye on it; below 1 "
            "means that even if everything were collected today it would not be enough. For a micro-business, a "
            "cushion of 2 to 4 weeks of expenses in cash is the practical rule."
        ),
    ),
    "prueba_acida": (
        "Quick ratio",
        (
            "The quick ratio is liquidity without counting inventory, because inventory still has to be sold. Add "
            "cash and receivables and divide by what you owe soon. If it is below 1, you depend on selling inventory "
            "to pay your upcoming debts."
        ),
    ),
    "capital_trabajo": (
        "Working capital",
        (
            "Working capital is what is left after subtracting your short-term debts from your short-term resources. "
            "It is the money you actually operate with: you buy supplies, pay helpers and get through slow days. If it "
            "is negative, you are financing the operation with the card or with suppliers, and any delay in sales "
            "becomes a payment problem."
        ),
    ),
    "margen_bruto": (
        "Gross margin",
        (
            "Gross margin is what you keep from each sale after paying ONLY the direct supplies of that product "
            "(flour, eggs, hair dye, materials). It does not include rent or wages. A low gross margin almost always "
            "comes from prices that were not updated when supplies got more expensive, or from recipes that use more "
            "than you charge for. Check your best sellers first: a small change in price or recipe there moves the "
            "most money."
        ),
    ),
    "margen_neto": (
        "Net margin and profit",
        (
            "Net margin is the real profit after ALL expenses: supplies, rent, utilities, wages, fees, depreciation. "
            "You can sell a lot and still have a negative net margin if fixed costs are high for your volume. When "
            "profit drops, separate three causes: you sold less, supplies cost more, or fixed costs went up."
        ),
    ),
    "costo_ventas": (
        "Cost of goods sold and average cost",
        (
            "Cost of goods sold is what the supplies of what you sold cost. Capital One Business calculates it on its "
            "own: each product has a recipe, and when a sale is paid its supplies are deducted at their weighted "
            "average cost (the average of what you paid in your purchases). If a supplier raises prices, the average "
            "cost rises little by little as you restock, and your margin drops even if you sell the same."
        ),
    ),
    "inventario": (
        "Inventory: cash that is waiting",
        (
            "Everything you keep unsold is money you already spent and cannot use. Turnover tells you how many times "
            "you sold your inventory in a period; days of inventory tell you how long a supply takes to go out. In "
            "food, more than 10 to 15 days usually means overbuying and waste; in retail, 30 to 60 days can be "
            "normal. Buying in bulk only pays off if the savings are bigger than the cost of having cash frozen for "
            "weeks."
        ),
    ),
    "punto_reorden": (
        "Reorder point",
        (
            "The reorder point is the quantity at which you should order again. It is what you use per day times the "
            "days your supplier takes to deliver, plus a small cushion. Running out of a supply that does sell is "
            "money you stopped earning; in the app you can set a reorder point per supply and we warn you when you "
            "reach it."
        ),
    ),
    "flujo_efectivo": (
        "Cash flow",
        (
            "Cash flow is what comes in and goes out of your cash box and your bank in a period. It is different from "
            "profit: you can be profitable and run out of cash if you bought a lot of inventory or customers pay you "
            "late. The practical rule: every week, look at what will come in, what you must pay and how much you end "
            "with."
        ),
    ),
    "deuda": (
        "Debt, business card and leverage",
        (
            "Using the business card for purchases helps because every purchase is recorded automatically and you "
            "keep personal and business money apart. Debt to equity compares what you owe with what is yours; above "
            "1 means there is more of other people's money than yours in the business. Pay the card in full every "
            "month: interest is an expense that produces nothing."
        ),
    ),
    "impuesto_ventas": (
        "Sales tax",
        (
            "The tax you charge on each sale is NOT your income: you collect it to hand it over to the state. That is "
            "why it shows up in your books as a debt (sales tax payable) and not as a sale. Keep it separate in your "
            "head from the cash you can spend."
        ),
    ),
    "cuentas_cobrar": (
        "Accounts receivable",
        (
            "A sale is not money until you get paid. If you work first and charge later, that finished work is a "
            "receivable: it counts as a resource but you cannot spend it. Asking for a deposit or billing by "
            "milestones changes your cash flow a lot even if you sell the same."
        ),
    ),
    "depreciacion": (
        "Depreciation and equipment",
        (
            "When you buy equipment (an oven, a mixer, tools) it is not an expense of the month: it is an asset you "
            "will use for years. Depreciation spreads its cost over time with a monthly adjusting entry, so your "
            "profit reflects the real wear and not a one-month hit."
        ),
    ),
    "retiros": (
        "Owner draws and personal purchases",
        (
            "What you take out of the business for yourself (or a personal purchase with the business card) is not a "
            "business expense: it is an owner draw and it reduces your equity. Recording it that way keeps your "
            "profit from looking worse than it is and keeps clear how much your business is really worth."
        ),
    ),
    "precio": (
        "How to set prices with margin",
        (
            "A healthy price covers the direct cost of the product, leaves margin for fixed costs and still earns. "
            "Quick rule: price = direct cost ÷ (1 − target gross margin). If your cake costs $8 in supplies and you "
            "want a 60% gross margin, the minimum price is $20. Review prices every time a key supply goes up more "
            "than 10%."
        ),
    ),
}

for _doc in DOCUMENTS:
    _doc["title_en"], _doc["text_en"] = EN[_doc["id"]]

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
        # Título y texto en los dos idiomas: una pregunta en inglés encuentra el
        # mismo documento que su equivalente en español.
        titles = f"{doc['title']} {doc.get('title_en', '')} {doc.get('tags', '')}"
        doc_tokens = tokens(f"{titles} {doc['text']} {doc.get('text_en', '')}")
        tag_tokens = set(tokens(titles))
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
        # El texto es lo que escribió el dueño: se cita tal cual en los dos idiomas.
        docs.append({"id": "profile_week", "title": "Lo que contaste de tu semana", "title_en": "What you told me about your week", "tags": "semana normal rutina contar dije negocio week normal told", "text": week, "text_en": week, "source": "onboarding"})
    answers = profile.get("answers") or {}
    yes = [k.replace("_", " ") for k, v in answers.items() if v]
    detail = f" ({profile['category_detail']})" if profile.get("category_detail") else ""
    days = ", ".join(profile.get("operating_days") or [])
    docs.append(
        {
            "id": "profile_summary",
            "title": f"Perfil de {business_name or 'tu negocio'}",
            "title_en": f"Profile of {business_name or 'your business'}",
            "tags": "perfil negocio categoria giro ciudad empleados dias profile business",
            "text": (
                f"Giro: {profile.get('category')}{detail}. "
                f"Ciudad: {profile.get('city')}. Equipo: {profile.get('employees')}. "
                f"Días de operación: {days}. "
                f"Respondiste que sí a: {', '.join(yes) if yes else 'ninguna pregunta'}."
            ),
            "text_en": (
                f"Business type: {profile.get('category')}{detail}. "
                f"City: {profile.get('city')}. Team: {profile.get('employees')}. "
                f"Operating days: {days}. "
                f"You answered yes to: {', '.join(yes) if yes else 'no questions'}."
            ),
            "source": "onboarding",
        }
    )
    return docs
