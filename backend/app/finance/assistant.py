"""
Asistente financiero híbrido: "pregúntale lo que sea a tu negocio".

    pregunta (cada una independiente: el asistente no guarda conversación)
      -> detección de intención (determinista, español e inglés)
      -> herramientas gobernadas sobre el motor financiero (datos estructurados,
         SIEMPRE acotados al negocio del token: el asistente nace con un
         FinanceContext y no puede pedir otro)
      -> recuperación de conocimiento (conceptos, contexto del onboarding)
      -> redacción: plantilla determinista, o LLM que SOLO redacta los hechos

El LLM nunca produce cifras: todas las cantidades de la respuesta vienen de
`evidence`, que se calcula antes de llamarlo.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Any

from app.finance import knowledge
from app.finance.analytics import AnalyticsService
from app.finance.catalog import CatalogService
from app.finance.common import ZERO, D, fmt_money, q2
from app.finance.inventory import InventoryService
from app.finance.llm import LLMProvider, NoLLM
from app.finance.purchases import PurchaseService
from app.finance.sales import SalesService


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    # "¿Qué es…?" -> "que es…": los signos de apertura estorban a los anclajes.
    return re.sub(r"^[¿¡\s\"']+", "", text).strip()


def _money(v: Any) -> str:
    return fmt_money(v)


def _pct(v: Any) -> str:
    return f"{q2(v)}%"


# Las etiquetas de las razones y de los factores de utilidad salen del motor en
# español (la UI es en español); el asistente las traduce cuando responde en inglés.
RATIO_LABELS_EN = {
    "current_ratio": "Current ratio",
    "quick_ratio": "Quick ratio",
    "cash_ratio": "Cash ratio",
    "working_capital": "Working capital",
    "gross_margin": "Gross margin",
    "net_margin": "Net margin",
    "return_on_assets": "Return on assets",
    "debt_to_equity": "Debt to equity",
    "debt_ratio": "Debt ratio",
    "inventory_turnover": "Inventory turnover",
    "days_inventory": "Days of inventory",
}
DRIVER_LABELS_EN = {"revenue": "Sales", "cogs": "Cost of goods", "expenses": "Operating expenses"}


def _ratio_label(ratio: dict[str, Any], lang: str) -> str:
    return RATIO_LABELS_EN.get(ratio["key"], ratio["label"]) if lang == "en" else ratio["label"]


def _ratio_value(ratio: dict[str, Any], lang: str) -> str:
    if not ratio["available"]:
        return "n/a"
    if ratio["unit"] == "%":
        return _pct(ratio["value"])
    if ratio["unit"] == "$":
        return _money(ratio["value"])
    if ratio["unit"] == "días":
        return f"{q2(ratio['value'])} {'days' if lang == 'en' else 'días'}"
    return f"{q2(ratio['value'])}"


def _knowledge_source(doc: dict[str, Any], lang: str) -> dict[str, Any]:
    title = doc.get("title_en", doc["title"]) if lang == "en" else doc["title"]
    return {"type": "knowledge", "id": doc["id"], "title": title}


PERIOD_PATTERNS: list[tuple[str, str]] = [
    (r"\bhoy\b|\btoday\b", "today"),
    (r"\bayer\b|\byesterday\b", "yesterday"),
    (r"semana pasada|last week|previous week", "last_week"),
    (r"esta semana|this week|\bsemana\b|\bweek\b", "week"),
    (r"mes pasado|last month|previous month", "last_month"),
    (r"este mes|this month|\bmes\b|\bmonth\b", "month"),
    (r"ultimos 7 dias|last 7 days|7 dias|7 days", "7d"),
    (r"ultimos 30 dias|last 30 days|30 dias|30 days", "30d"),
    (r"ultimos 90 dias|last 90 days|trimestre|quarter", "90d"),
    (r"este ano|this year|\bano\b|\byear\b", "year"),
    (r"desde el inicio|all time|historico|siempre", "all"),
]

INTENT_PATTERNS: list[tuple[str, str]] = [
    ("profit_drivers", r"por que (bajo|cayo|subio|cambio).*(utilidad|ganancia|profit)|why did .*profit|why (is|was) .*profit|que paso con (mi|la) (utilidad|ganancia)|explica.*(caida|baja).*utilidad"),
    # Preguntas de concepto van antes que las de datos: "¿qué es el capital
    # de trabajo?" pide una explicación, no el cálculo (que se agrega como evidencia).
    ("concept", r"\b(que es|que son|que significa|what is|what are|what does|explica|explain|explicame|define)\b|como se calcula|how is .*calculated|para que sirve|por que es (importante|peligroso)|why is .*dangerous|que quiere decir"),
    ("liquidity", r"liquidez|liquidity|razon circulante|current ratio|prueba acida|quick ratio|capital de trabajo|working capital|puedo pagar|alcanza para pagar"),
    ("cash", r"\bcaja\b|\bcash\b|efectivo|flujo|cuanto dinero tengo|how much money do i have|cuanto tengo en el banco|banco"),
    ("capacity", r"cuantos? .*(puedo|puedes|podria).*(hacer|producir|preparar|vender)|how many .*(can|could) i (make|produce|sell)|para cuantos"),
    ("runout", r"se (va a )?(acabar|agotar|terminar)|run out|se me acaba|primero se acaba|que insumo|bajo de stock|por agotarse|reorden"),
    ("inventory", r"inventario|inventory|existencias|insumos|stock|almacen|cuanta harina|cuantos huevos|cuanto (tengo|queda) de|how much .* (do i have|is left|left)"),
    ("top_products", r"(que|cual|cuales) (producto|productos|platillo|servicio).*(mas|mejor|menos)|which product|best.?sell|mas vendid|mas ganancia|mas utilidad|mas rentable|top product"),
    ("expenses", r"gast[eo]|gastos|expense|spend|spent|cuanto (pague|he pagado|compre)|compras|purchases|what were my biggest|mayores gastos|en que se fue"),
    ("customers", r"cliente|customer|quien me compra|compradores"),
    ("profit", r"utilidad|ganancia|ganado|gane|profit|margen|margin|net income|cuanto me quedo|rentabilidad"),
    ("sales", r"venta|ventas|vendi|vendido|sales|sold|\bsell\b|revenue|ingreso|ingresos|cuanto cobre|facture"),
    ("ratios", r"razon|razones|ratio|ratios|indicador|indicadores|deuda sobre capital|debt|apalancamiento|leverage|rotacion|turnover|dias de inventario"),
    ("statements", r"balance general|balance sheet|estado de resultados|income statement|estados financieros|financial statements|libro diario|journal|libro mayor|ledger|balanza"),
    ("business_context", r"que te (dije|conte)|what did i tell you|mi semana normal|mi perfil|que sabes de mi negocio"),
    ("concept", r"que es|que significa|what is|what does|explica|explain|explicame|que quiere decir"),
]

ENGLISH_HINTS = re.compile(r"\b(what|when|how|which|why|my|the|is|are|was|were|did|do|does|i|you|will|can|have|of|show|tell|about|sales|profit|inventory|cash|week|month|explain|much|many)\b")
SPANISH_HINTS = re.compile(r"\b(que|cuando|como|cual|cuales|por que|mi|mis|el|la|los|las|de|del|es|son|hay|puedo|tengo|ventas|utilidad|inventario|caja|semana|mes|explica|cuanto|cuantos|cuanta)\b")
# "What are my financial ratios?" o "¿Cuál es mi capital de trabajo?" piden el
# dato del negocio, no la definición. "Explain my current ratio" sí es concepto.
ASKS_FOR_OWN_FIGURE = re.compile(r"\b(what (is|are|was|were) my|cual(es)? (es|son) mis?)\b")

# Guardia anti-alucinación: TODA cifra que el LLM escriba (montos con o sin
# centavos, porcentajes, cantidades, días) tiene que existir ya en los hechos o
# en la respuesta base. Se compara por valor, no por texto: "$7,989.04",
# "$7989.04" y "7989.040" son la misma cifra.
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
# Cantidades escritas con palabras: "un millón" no tiene dígitos que comparar.
_MAGNITUDE_WORDS = re.compile(r"\b(mil|miles|millon|millones|billon|billones|thousands?|millions?|billions?)\b")


def _numbers(text: str) -> set[Decimal]:
    found: set[Decimal] = set()
    for token in _NUMBER.findall(text):
        token = token.rstrip(",")
        # "79,27" (coma decimal, 1-2 dígitos) vs "1,234" (miles, 3 dígitos).
        token = token.replace(",", ".") if re.fullmatch(r"\d+,\d{1,2}", token) else token.replace(",", "")
        try:
            found.add(Decimal(token).normalize())
        except ArithmeticError:  # pragma: no cover - el regex sólo deja dígitos
            continue
    return found


def _ungrounded(text: str, grounded_in: str) -> list[str]:
    """Cifras y magnitudes de `text` que no aparecen en `grounded_in`."""
    missing = [str(n) for n in _numbers(text) - _numbers(grounded_in)]
    words = set(_MAGNITUDE_WORDS.findall(_norm(text))) - set(_MAGNITUDE_WORDS.findall(_norm(grounded_in)))
    return missing + sorted(words)


class Assistant:
    def __init__(
        self,
        *,
        analytics: AnalyticsService,
        sales: SalesService,
        inventory: InventoryService,
        catalog: CatalogService,
        purchases: PurchaseService,
        profile: dict[str, Any] | None,
        business_name: str | None,
        llm: LLMProvider | None = None,
    ):
        self.analytics = analytics
        self.sales = sales
        self.inventory = inventory
        self.catalog = catalog
        self.purchases = purchases
        self.profile = profile
        self.business_name = business_name or "tu negocio"
        self.llm = llm or NoLLM()

    # ------------------------------------------------------------- entrada --

    def ask(self, question: str) -> dict[str, Any]:
        """Responde UNA pregunta, sin conversación: cada llamada es
        independiente y el servidor no guarda estado entre ellas."""
        text = _norm(question.strip())
        lang = self._language(text)
        period = self._period(text)
        intent = self._intent(text)
        if intent == "concept":
            data_intent = self._intent(text, exclude={"concept"})
            if not knowledge.search(text, knowledge.business_context_documents(self.profile, self.business_name), k=1):
                # "Explícame cómo van mis ventas": no es un concepto, es un dato.
                intent = data_intent
            elif data_intent not in {"unknown", "business_context"} and ASKS_FOR_OWN_FIGURE.search(text):
                intent = data_intent
        handler = getattr(self, f"_tool_{intent}")
        try:
            result = handler(text, period, lang)
        except Exception as exc:  # noqa: BLE001 - una herramienta rota no debe tumbar la conversación
            result = self._fallback(text, lang, f"{exc}")
        answer = result["answer"]
        llm_used = False
        if self.llm.available and result.get("allow_llm", True):
            rewritten = self._rewrite(question, lang, result)
            if rewritten:
                answer, llm_used = rewritten, True
        return {
            "question": question,
            "answer": answer,
            "intent": intent,
            "language": lang,
            "period": period,
            "evidence": result.get("evidence", []),
            "sources": result.get("sources", []),
            "tool_calls": result.get("tools", [intent]),
            "suggestions": result.get("suggestions", self._default_suggestions(lang)),
            "llm_used": llm_used,
            "llm_provider": self.llm.name if llm_used else None,
        }

    # ------------------------------------------------------ enrutamiento --

    @staticmethod
    def _language(text: str) -> str:
        en = len(ENGLISH_HINTS.findall(text))
        es = len(SPANISH_HINTS.findall(text))
        return "en" if en > es else "es"

    @staticmethod
    def _period(text: str) -> str:
        for pattern, key in PERIOD_PATTERNS:
            if re.search(pattern, text):
                return key
        return "month"

    @staticmethod
    def _intent(text: str, exclude: set[str] | None = None) -> str:
        for intent, pattern in INTENT_PATTERNS:
            if exclude and intent in exclude:
                continue
            if re.search(pattern, text):
                return intent
        return "unknown"

    def _default_suggestions(self, lang: str) -> list[str]:
        if lang == "en":
            return ["How were my sales this week?", "How is my liquidity doing?", "Which product made me the most profit?", "What is working capital?"]
        return ["¿Cómo van mis ventas esta semana?", "¿Cómo está mi liquidez?", "¿Qué producto me deja más ganancia?", "¿Qué es el capital de trabajo?"]

    # ----------------------------------------------------- herramientas --

    def _period_label(self, period: str, lang: str) -> str:
        _, _, label = self.analytics.resolve_period(period)
        if lang == "en":
            return {
                "today": "today", "yesterday": "yesterday", "week": "this week", "last_week": "last week", "month": "this month",
                "last_month": "last month", "7d": "the last 7 days", "30d": "the last 30 days", "90d": "the last 90 days", "year": "this year", "all": "since the beginning",
            }.get(period, period)
        return label

    def _tool_sales(self, text: str, period: str, lang: str) -> dict[str, Any]:
        start, end, _ = self.analytics.resolve_period(period)
        s = self.sales.sales_summary(start, end)
        label = self._period_label(period, lang)
        prev = self.analytics.health(period)["revenue"]
        change = prev["change_pct"]
        evidence = [
            {"label": "Ventas" if lang == "es" else "Sales", "value": _money(s["revenue"]), "detail": f"{start} → {end}"},
            {"label": "Órdenes pagadas" if lang == "es" else "Paid orders", "value": str(s["order_count"])},
            {"label": "Ticket promedio" if lang == "es" else "Average ticket", "value": _money(s["average_ticket"] or 0)},
            {"label": "Impuesto cobrado" if lang == "es" else "Sales tax collected", "value": _money(s["tax_collected"])},
        ]
        if change is not None:
            evidence.append({"label": "Vs. periodo anterior" if lang == "es" else "Vs. previous period", "value": f"{'+' if change >= 0 else ''}{_pct(change)}", "detail": _money(prev["previous"])})
        if s["order_count"] == 0:
            answer = f"No hay ventas pagadas {label}." if lang == "es" else f"There are no paid sales {label}."
        else:
            top = s["by_item"][0]["name"] if s["by_item"] else None
            if lang == "es":
                answer = f"Vendiste {_money(s['revenue'])} {label} en {s['order_count']} órdenes (ticket promedio {_money(s['average_ticket'] or 0)})."
                if change is not None:
                    answer += f" Eso es {'+' if change >= 0 else ''}{_pct(change)} frente al periodo anterior."
                if top:
                    answer += f" Lo que más ganancia dejó fue {top}."
            else:
                answer = f"You sold {_money(s['revenue'])} {label} across {s['order_count']} orders (average ticket {_money(s['average_ticket'] or 0)})."
                if change is not None:
                    answer += f" That is {'+' if change >= 0 else ''}{_pct(change)} versus the previous period."
                if top:
                    answer += f" Your most profitable item was {top}."
        return {"answer": answer, "evidence": evidence, "tools": ["sales_summary", "health"], "sources": [{"type": "structured", "title": "sales_orders / order_lines"}]}

    def _tool_profit(self, text: str, period: str, lang: str) -> dict[str, Any]:
        h = self.analytics.health(period)
        label = self._period_label(period, lang)
        gm = h["margin"]
        evidence = [
            {"label": "Ventas" if lang == "es" else "Revenue", "value": _money(h["revenue"]["value"])},
            {"label": "Utilidad bruta" if lang == "es" else "Gross profit", "value": _money(h["gross_profit"]["value"])},
            {"label": "Gastos" if lang == "es" else "Operating expenses", "value": _money(h["expenses"]["value"])},
            {"label": "Utilidad neta" if lang == "es" else "Net income", "value": _money(h["net_income"]["value"])},
        ]
        if gm["available"]:
            evidence.append({"label": "Margen bruto" if lang == "es" else "Gross margin", "value": _pct(gm["value"])})
        ch = h["net_income"]["change_pct"]
        if lang == "es":
            answer = f"{label.capitalize()} tu utilidad neta fue {_money(h['net_income']['value'])}: vendiste {_money(h['revenue']['value'])}, los insumos costaron {_money(h['revenue']['value'] - h['gross_profit']['value'])} y los gastos fueron {_money(h['expenses']['value'])}."
            if gm["available"]:
                answer += f" Tu margen bruto es {_pct(gm['value'])}."
            if ch is not None:
                answer += f" La utilidad {'subió' if ch >= 0 else 'bajó'} {_pct(abs(ch))} frente al periodo anterior."
        else:
            answer = f"Your net income {label} was {_money(h['net_income']['value'])}: revenue {_money(h['revenue']['value'])}, cost of goods {_money(h['revenue']['value'] - h['gross_profit']['value'])}, expenses {_money(h['expenses']['value'])}."
            if gm["available"]:
                answer += f" Gross margin is {_pct(gm['value'])}."
            if ch is not None:
                answer += f" Profit went {'up' if ch >= 0 else 'down'} {_pct(abs(ch))} versus the previous period."
        return {"answer": answer, "evidence": evidence, "tools": ["income_statement", "health"], "sources": [{"type": "structured", "title": "journal_lines (estado de resultados)"}]}

    def _tool_profit_drivers(self, text: str, period: str, lang: str) -> dict[str, Any]:
        d = self.analytics.profit_drivers(period)
        label = self._period_label(period, lang)
        evidence = [
            {"label": "Utilidad neta" if lang == "es" else "Net income", "value": _money(d["net_income"]), "detail": f"antes {_money(d['previous_net_income'])}" if lang == "es" else f"before {_money(d['previous_net_income'])}"},
            {"label": "Ventas" if lang == "es" else "Revenue", "value": _money(d["revenue"]), "detail": f"antes {_money(d['previous_revenue'])}" if lang == "es" else f"before {_money(d['previous_revenue'])}"},
            {"label": "Costo de insumos" if lang == "es" else "Cost of goods", "value": _money(d["cogs"]), "detail": f"antes {_money(d['previous_cogs'])}" if lang == "es" else f"before {_money(d['previous_cogs'])}"},
            {"label": "Gastos" if lang == "es" else "Expenses", "value": _money(d["operating_expenses"]), "detail": f"antes {_money(d['previous_operating_expenses'])}" if lang == "es" else f"before {_money(d['previous_operating_expenses'])}"},
        ]
        if d["gross_margin_pct"] is not None and d["previous_gross_margin_pct"] is not None:
            evidence.append({"label": "Margen bruto" if lang == "es" else "Gross margin", "value": f"{_pct(d['previous_gross_margin_pct'])} → {_pct(d['gross_margin_pct'])}"})
        delta = d["delta"]
        if lang == "es":
            if delta == 0:
                answer = f"Tu utilidad {label} es igual a la del periodo anterior ({_money(d['net_income'])})."
            else:
                answer = f"Tu utilidad {label} {'bajó' if delta < 0 else 'subió'} {_money(abs(delta))} ({_money(d['previous_net_income'])} → {_money(d['net_income'])})."
                parts = []
                for drv in d["drivers"][:3]:
                    parts.append(f"{drv['label'].lower()} ({'+' if drv['impact'] >= 0 else '−'}{_money(abs(drv['impact']))}): {drv['detail']}")
                if parts:
                    answer += " Los factores, del más al menos importante: " + " ".join(parts)
                if d["product_changes"]:
                    pc = d["product_changes"][0]
                    answer += f" El producto que más cambió fue {pc['name']} ({pc['previous_units']:.0f} → {pc['units']:.0f} unidades)."
        else:
            if delta == 0:
                answer = f"Your profit {label} equals the previous period ({_money(d['net_income'])})."
            else:
                answer = f"Your profit {label} went {'down' if delta < 0 else 'up'} by {_money(abs(delta))} ({_money(d['previous_net_income'])} → {_money(d['net_income'])})."
                parts = [f"{DRIVER_LABELS_EN.get(drv['driver'], drv['label'])} ({'+' if drv['impact'] >= 0 else '−'}{_money(abs(drv['impact']))})" for drv in d["drivers"][:3]]
                if parts:
                    answer += " Main drivers: " + "; ".join(parts) + "."
        return {"answer": answer, "evidence": evidence, "tools": ["profit_drivers", "income_statement", "sales_summary"], "sources": [{"type": "structured", "title": "journal_lines + order_lines (comparación de periodos)"}]}

    def _tool_liquidity(self, text: str, period: str, lang: str) -> dict[str, Any]:
        r = self.analytics.ratios(period)
        by = {x["key"]: x for x in r["ratios"]}
        cr, qr, wc = by["current_ratio"], by["quick_ratio"], by["working_capital"]
        status_es = {"good": "buena", "attention": "necesita atención", "critical": "crítica", "neutral": "sin deuda a corto plazo"}
        status_en = {"good": "good", "attention": "needs attention", "critical": "critical", "neutral": "no short-term debt"}
        evidence = [
            {"label": "Razón circulante" if lang == "es" else "Current ratio", "value": f"{q2(cr['value'])}" if cr["available"] else "n/a", "detail": cr["formula"]},
            {"label": "Prueba ácida" if lang == "es" else "Quick ratio", "value": f"{q2(qr['value'])}" if qr["available"] else "n/a"},
            {"label": "Capital de trabajo" if lang == "es" else "Working capital", "value": _money(wc["value"])},
            {"label": "Efectivo" if lang == "es" else "Cash", "value": _money(r["position"]["cash"])},
            {"label": "Debes pronto" if lang == "es" else "Due soon", "value": _money(r["position"]["current_liabilities"])},
        ]
        if lang == "es":
            answer = f"Tu liquidez está {status_es[cr['status']]}. {cr['explanation']} {wc['explanation']}"
            if qr["available"]:
                answer += f" {qr['explanation']}"
        else:
            answer = f"Your liquidity is {status_en[cr['status']]}. You have about {fmt_money(cr['value']) if cr['available'] else '—'} in short-term resources for every $1.00 due soon; working capital is {_money(wc['value'])}."
        return {"answer": answer, "evidence": evidence, "tools": ["ratios", "balance_sheet"], "sources": [{"type": "structured", "title": "balance general (v_general_ledger)"}, {"type": "knowledge", "id": "liquidez", "title": "Liquidez y razón circulante" if lang == "es" else "Liquidity and the current ratio"}], "suggestions": ["¿Qué es la razón circulante?", "¿Cuánto debo de la tarjeta?", "¿Cómo va mi caja este mes?"] if lang == "es" else ["What is the current ratio?", "How much do I owe on the card?", "How is my cash this month?"]}

    def _tool_cash(self, text: str, period: str, lang: str) -> dict[str, Any]:
        c = self.analytics.cash_intelligence(period)
        label = self._period_label(period, lang)
        evidence = [
            {"label": "Efectivo disponible" if lang == "es" else "Cash available", "value": _money(c["cash_available"])},
            {"label": "Entradas" if lang == "es" else "Inflows", "value": _money(c["inflows"]), "detail": label},
            {"label": "Salidas" if lang == "es" else "Outflows", "value": _money(c["outflows"]), "detail": label},
            {"label": "Debes pronto" if lang == "es" else "Due soon", "value": _money(c["short_term_obligations"]), "detail": f"tarjeta {_money(c['card_balance'])}, impuestos {_money(c['tax_payable'])}" if lang == "es" else f"card {_money(c['card_balance'])}, taxes {_money(c['tax_payable'])}"},
            {"label": "En inventario" if lang == "es" else "Tied up in inventory", "value": _money(c["inventory_tied_up"])},
        ]
        if lang == "es":
            answer = f"{c['headline']}. {c['explanation']} Además tienes {_money(c['inventory_tied_up'])} invertidos en inventario."
        else:
            answer = f"You have {_money(c['cash_available'])} available and owe {_money(c['short_term_obligations'])} soon (card {_money(c['card_balance'])}, sales tax {_money(c['tax_payable'])}). {label.capitalize()} {_money(c['inflows'])} came in and {_money(c['outflows'])} went out, with {_money(c['inventory_tied_up'])} tied up in inventory."
        return {"answer": answer, "evidence": evidence, "tools": ["cash_intelligence"], "sources": [{"type": "structured", "title": "cuentas de caja/banco en el mayor"}]}

    def _find_inventory_item(self, text: str) -> dict[str, Any] | None:
        for item in self.inventory.list_items():
            if _norm(item["name"]) in text or any(len(w) > 3 and w in text for w in _norm(item["name"]).split()):
                return item
        return None

    def _find_product(self, text: str) -> dict[str, Any] | None:
        for item in self.catalog.list_items():
            if _norm(item["name"]) in text or any(len(w) > 4 and w in text for w in _norm(item["name"]).split()):
                return item
        return None

    def _tool_inventory(self, text: str, period: str, lang: str) -> dict[str, Any]:
        item = self._find_inventory_item(text)
        s = self.inventory.summary()
        if item:
            unit = item["unit_of_measure"]
            evidence = [
                {"label": item["name"], "value": f"{D(item['quantity_on_hand']).normalize():f} {unit}"},
                {"label": "Costo promedio" if lang == "es" else "Average cost", "value": f"{_money(item['average_unit_cost'])}/{unit}"},
                {"label": "Valor" if lang == "es" else "Value", "value": _money(item["inventory_value"])},
            ]
            low = " Está por debajo de su punto de reorden." if item["low_stock"] else ""
            answer = (
                f"Tienes {D(item['quantity_on_hand']).normalize():f} {unit} de {item['name']}, que valen {_money(item['inventory_value'])} a costo promedio.{low}"
                if lang == "es"
                else f"You have {D(item['quantity_on_hand']).normalize():f} {unit} of {item['name']}, worth {_money(item['inventory_value'])} at average cost.{' It is below its reorder point.' if item['low_stock'] else ''}"
            )
            return {"answer": answer, "evidence": evidence, "tools": ["inventory_item"], "sources": [{"type": "structured", "title": "inventory_items / inventory_movements"}]}
        evidence = [{"label": "Valor del inventario" if lang == "es" else "Inventory value", "value": _money(s["total_value"])}, {"label": "Insumos" if lang == "es" else "Items", "value": str(s["item_count"])}]
        top = sorted(s["items"], key=lambda i: D(i["inventory_value"]), reverse=True)[:3]
        for i in top:
            evidence.append({"label": i["name"], "value": f"{D(i['quantity_on_hand']).normalize():f} {i['unit_of_measure']}", "detail": _money(i["inventory_value"])})
        low = [i["name"] for i in s["low_stock_items"]]
        if lang == "es":
            answer = f"Tienes {s['item_count']} insumos con un valor total de {_money(s['total_value'])}."
            if top:
                answer += " Lo que más pesa: " + ", ".join(f"{i['name']} ({_money(i['inventory_value'])})" for i in top) + "."
            if low:
                answer += f" Por agotarse: {', '.join(low)}."
        else:
            answer = f"You have {s['item_count']} inventory items worth {_money(s['total_value'])} in total."
            if top:
                answer += " Largest: " + ", ".join(f"{i['name']} ({_money(i['inventory_value'])})" for i in top) + "."
            if low:
                answer += f" Running low: {', '.join(low)}."
        return {"answer": answer, "evidence": evidence, "tools": ["inventory_summary"], "sources": [{"type": "structured", "title": "inventory_items"}]}

    def _tool_capacity(self, text: str, period: str, lang: str) -> dict[str, Any]:
        product = self._find_product(text)
        items = [product] if product else [i for i in self.catalog.list_items() if i["components"]]
        if not items:
            return self._tool_inventory(text, period, lang)
        evidence = []
        parts = []
        for it in items[:5]:
            cap = it["producible_units"]
            if cap is None:
                continue
            limiting = min(it["components"], key=lambda c: (D(c["quantity_on_hand"]) / D(c["quantity_per_unit"])) if D(c["quantity_per_unit"]) else Decimal("1e9"))
            evidence.append({"label": it["name"], "value": f"{cap}", "detail": (f"limita: {limiting['inventory_item_name']}" if lang == "es" else f"limited by {limiting['inventory_item_name']}")})
            parts.append(f"{cap} {it['name']}" + (f" (te limita {limiting['inventory_item_name']})" if lang == "es" else f" (limited by {limiting['inventory_item_name']})"))
        if lang == "es":
            answer = "Con lo que tienes en inventario puedes preparar " + "; ".join(parts) + "." if parts else "Ese producto no tiene receta registrada."
        else:
            answer = "With current inventory you can make " + "; ".join(parts) + "." if parts else "That product has no recipe yet."
        return {"answer": answer, "evidence": evidence, "tools": ["catalog_capacity"], "sources": [{"type": "structured", "title": "item_components × inventory_items"}]}

    def _tool_runout(self, text: str, period: str, lang: str) -> dict[str, Any]:
        start, _, _ = self.analytics.resolve_period("30d")
        rows = self.inventory.repo.query(
            "SELECT inventory_item_id, COALESCE(SUM(-quantity_delta), 0) AS consumed FROM inventory_movements "
            "WHERE business_id = :business_id AND movement_type = 'SALE_CONSUMPTION' AND occurred_at >= :start "
            "GROUP BY inventory_item_id",
            {"start": start},
        )
        consumed = {r["inventory_item_id"]: D(r["consumed"]) for r in rows}
        projections = []
        for item in self.inventory.list_items():
            daily = consumed.get(item["inventory_item_id"], ZERO) / 30
            on_hand = D(item["quantity_on_hand"])
            days = None
            if on_hand <= 0:
                days = ZERO
            elif daily > 0:
                days = on_hand / daily
            projections.append({"item": item, "daily": daily, "days": days})
        with_days = sorted([p for p in projections if p["days"] is not None], key=lambda p: p["days"])

        def row(p: dict[str, Any]) -> dict[str, Any]:
            qty = f"{D(p['item']['quantity_on_hand']).normalize():f} {p['item']['unit_of_measure']}"
            if p["days"] is None:
                return {"label": p["item"]["name"], "value": "sin consumo" if lang == "es" else "no usage", "detail": qty}
            return {"label": p["item"]["name"], "value": (f"~{q2(p['days'])} días" if lang == "es" else f"~{q2(p['days'])} days"), "detail": f"{qty}, {q2(p['daily'])}/día" if lang == "es" else f"{qty}, {q2(p['daily'])}/day"}

        asked = self._find_inventory_item(text)
        if asked:
            # "¿Cuándo se me acaba la harina?": la pregunta nombra un insumo,
            # así que la respuesta es sobre ÉSE; los demás quedan de contexto.
            target = next((p for p in projections if p["item"]["inventory_item_id"] == asked["inventory_item_id"]), None)
            if target is not None:
                it = target["item"]
                qty = f"{D(it['quantity_on_hand']).normalize():f} {it['unit_of_measure']}"
                others = [p for p in with_days if p["item"]["inventory_item_id"] != it["inventory_item_id"]][:4]
                evidence = [row(target)] + [row(p) for p in others]
                if target["days"] is None:
                    answer = f"{it['name']} no se ha consumido en ventas en los últimos 30 días: tienes {qty} y no hay ritmo para proyectar cuándo se acaba." if lang == "es" else f"{it['name']} has not been used in sales over the last 30 days: you have {qty}, so there is no pace to project from."
                elif target["days"] == 0:
                    answer = f"{it['name']} ya se acabó: no queda nada en inventario." if lang == "es" else f"{it['name']} is already out: nothing left in inventory."
                else:
                    low = " Ya está por debajo de su punto de reorden." if it["low_stock"] else ""
                    answer = (
                        f"Al ritmo de los últimos 30 días, {it['name']} se acaba en unos {q2(target['days'])} días: quedan {qty} y consumes {q2(target['daily'])} {it['unit_of_measure']} al día.{low}"
                        if lang == "es"
                        else f"At the pace of the last 30 days, {it['name']} runs out in about {q2(target['days'])} days: {qty} left, using {q2(target['daily'])} {it['unit_of_measure']} per day.{' It is below its reorder point.' if it['low_stock'] else ''}"
                    )
                return {"answer": answer, "evidence": evidence, "tools": ["inventory_runout"], "sources": [{"type": "structured", "title": "inventory_movements (consumo por ventas)"}]}

        evidence = [row(p) for p in with_days[:5]]
        if not with_days:
            answer = "Todavía no hay consumo suficiente para proyectar cuándo se acaba cada insumo." if lang == "es" else "There is not enough consumption history yet to project run-out dates."
        else:
            first = with_days[0]
            out_now = [p for p in with_days if p["days"] == 0]
            if lang == "es":
                if out_now:
                    answer = "Ya se acabó: " + ", ".join(p["item"]["name"] for p in out_now[:3]) + "."
                    rest = [p for p in with_days if p["days"] > 0]
                    if rest:
                        answer += f" Lo siguiente en acabarse es {rest[0]['item']['name']} (~{q2(rest[0]['days'])} días)."
                else:
                    answer = f"Al ritmo de los últimos 30 días, lo primero que se acaba es {first['item']['name']}: quedan {D(first['item']['quantity_on_hand']).normalize():f} {first['item']['unit_of_measure']}, unos {q2(first['days'])} días."
                    if len(with_days) > 1:
                        answer += " Después: " + ", ".join(f"{p['item']['name']} (~{q2(p['days'])} días)" for p in with_days[1:4]) + "."
            else:
                if out_now:
                    answer = "Already out: " + ", ".join(p["item"]["name"] for p in out_now[:3]) + "."
                else:
                    answer = f"At the pace of the last 30 days, {first['item']['name']} runs out first: {D(first['item']['quantity_on_hand']).normalize():f} {first['item']['unit_of_measure']} left, about {q2(first['days'])} days."
        return {"answer": answer, "evidence": evidence, "tools": ["inventory_runout"], "sources": [{"type": "structured", "title": "inventory_movements (consumo por ventas)"}]}

    def _tool_top_products(self, text: str, period: str, lang: str) -> dict[str, Any]:
        start, end, _ = self.analytics.resolve_period(period if period != "month" or re.search(r"mes|month", text) else "30d")
        s = self.sales.sales_summary(start, end)
        label = self._period_label(period, lang)
        by_units = sorted(s["by_item"], key=lambda i: i["units"], reverse=True)
        evidence = [{"label": i["name"], "value": _money(i["gross_profit"]), "detail": f"{i['units']:.0f} uds · {_money(i['revenue'])}" if lang == "es" else f"{i['units']:.0f} units · {_money(i['revenue'])}"} for i in s["by_item"][:5]]
        if not s["by_item"]:
            answer = f"No hay ventas {label}." if lang == "es" else f"No sales {label}."
        else:
            best, most = s["by_item"][0], by_units[0]
            if lang == "es":
                answer = f"El producto que más ganancia te dejó {label} fue {best['name']}: {_money(best['gross_profit'])} de utilidad bruta con {best['units']:.0f} unidades."
                if most["name"] != best["name"]:
                    answer += f" El más vendido en unidades fue {most['name']} ({most['units']:.0f})."
            else:
                answer = f"Your most profitable item {label} was {best['name']}: {_money(best['gross_profit'])} gross profit on {best['units']:.0f} units."
                if most["name"] != best["name"]:
                    answer += f" The best seller by units was {most['name']} ({most['units']:.0f})."
        return {"answer": answer, "evidence": evidence, "tools": ["sales_summary"], "sources": [{"type": "structured", "title": "order_lines (ganancia por producto)"}]}

    def _tool_expenses(self, text: str, period: str, lang: str) -> dict[str, Any]:
        start, end, _ = self.analytics.resolve_period(period)
        label = self._period_label(period, lang)
        sp = self.purchases.spending(start, end)
        merchant_match = None
        for m in sp["by_merchant"]:
            if _norm(m["merchant"]) in text:
                merchant_match = m
                break
        if merchant_match:
            evidence = [{"label": merchant_match["merchant"], "value": _money(merchant_match["amount"]), "detail": label}]
            answer = (f"{label.capitalize()} gastaste {_money(merchant_match['amount'])} en {merchant_match['merchant']}." if lang == "es" else f"You spent {_money(merchant_match['amount'])} at {merchant_match['merchant']} {label}.")
            return {"answer": answer, "evidence": evidence, "tools": ["spending"], "sources": [{"type": "structured", "title": "card_transactions"}]}
        income = self.analytics.accounting.income_statement(start, end)
        evidence = [{"label": "Compras con tarjeta" if lang == "es" else "Card purchases", "value": _money(sp["total"]), "detail": f"{sp['transaction_count']} transacciones" if lang == "es" else f"{sp['transaction_count']} transactions"}]
        for a in sp["by_account"][:4]:
            evidence.append({"label": a["account_name"], "value": _money(a["amount"])})
        top_m = sp["by_merchant"][:3]
        if lang == "es":
            answer = f"{label.capitalize()} tu tarjeta de negocio registró {_money(sp['total'])} en {sp['transaction_count']} compras."
            if sp["by_account"]:
                answer += " Por tipo: " + ", ".join(f"{a['account_name'].lower()} {_money(a['amount'])}" for a in sp["by_account"][:3]) + "."
            if top_m:
                answer += " Comercios principales: " + ", ".join(f"{m['merchant']} ({_money(m['amount'])})" for m in top_m) + "."
            answer += f" Los gastos de operación en el estado de resultados suman {_money(income['total_operating_expenses'])}."
            if sp["pending_review"]:
                answer += f" Hay {sp['pending_review']} compra(s) por confirmar."
        else:
            answer = f"{label.capitalize()} your business card recorded {_money(sp['total'])} across {sp['transaction_count']} purchases."
            if top_m:
                answer += " Top merchants: " + ", ".join(f"{m['merchant']} ({_money(m['amount'])})" for m in top_m) + "."
            answer += f" Operating expenses on the income statement total {_money(income['total_operating_expenses'])}."
        return {"answer": answer, "evidence": evidence, "tools": ["spending", "income_statement"], "sources": [{"type": "structured", "title": "card_transactions + journal_lines"}]}

    def _tool_customers(self, text: str, period: str, lang: str) -> dict[str, Any]:
        rows = self.sales.customers_summary(limit=5)
        evidence = [{"label": r["display_name"], "value": _money(r["lifetime_revenue"]), "detail": f"{r['purchase_count']} compras" if lang == "es" else f"{r['purchase_count']} purchases"} for r in rows]
        if not rows:
            answer = "Todavía no hay clientes identificados: las ventas fueron anónimas." if lang == "es" else "No identified customers yet: sales were anonymous."
        else:
            best = rows[0]
            answer = (f"Tienes {len(rows)} clientes identificados. El que más te ha comprado es {best['display_name']}: {best['purchase_count']} compras por {_money(best['lifetime_revenue'])}." if lang == "es" else f"You have {len(rows)} identified customers. Your top customer is {best['display_name']}: {best['purchase_count']} purchases totaling {_money(best['lifetime_revenue'])}.")
        return {"answer": answer, "evidence": evidence, "tools": ["customers_summary"], "sources": [{"type": "structured", "title": "customers × sales_orders"}]}

    def _tool_ratios(self, text: str, period: str, lang: str) -> dict[str, Any]:
        r = self.analytics.ratios(period)
        wanted = [x for x in r["ratios"] if any(w in text for w in _norm(x["label"]).split() if len(w) > 4) or x["key"].replace("_", " ") in text]
        rows = wanted or [x for x in r["ratios"] if x["available"]]
        evidence = [{"label": _ratio_label(x, lang), "value": _ratio_value(x, lang), "detail": x["formula"]} for x in rows[:6]]
        if lang == "es":
            answer = " ".join(f"{x['label']}: {x['explanation']}" for x in rows[:4]) or "Todavía no hay datos suficientes para calcular razones."
        else:
            answer = "; ".join(f"{_ratio_label(x, lang)} = {_ratio_value(x, lang)} ({x['status']})" for x in rows[:5] if x["available"]) or "Not enough data to compute ratios yet."
        return {"answer": answer, "evidence": evidence, "tools": ["ratios"], "sources": [{"type": "structured", "title": "razones financieras (backend)"}]}

    def _tool_statements(self, text: str, period: str, lang: str) -> dict[str, Any]:
        start, end, _ = self.analytics.resolve_period(period)
        income = self.analytics.accounting.income_statement(start, end)
        bs = self.analytics.accounting.balance_sheet(end)
        evidence = [
            {"label": "Ventas" if lang == "es" else "Revenue", "value": _money(income["total_revenue"])},
            {"label": "Utilidad neta" if lang == "es" else "Net income", "value": _money(income["net_income"])},
            {"label": "Activos" if lang == "es" else "Assets", "value": _money(bs["total_assets"])},
            {"label": "Pasivos" if lang == "es" else "Liabilities", "value": _money(bs["total_liabilities"])},
            {"label": "Capital" if lang == "es" else "Equity", "value": _money(bs["total_equity"])},
        ]
        answer = (
            f"Tu estado de resultados {self._period_label(period, lang)} muestra ventas de {_money(income['total_revenue'])} y utilidad neta de {_money(income['net_income'])}. Tu balance general al {end} tiene activos por {_money(bs['total_assets'])}, pasivos por {_money(bs['total_liabilities'])} y capital de {_money(bs['total_equity'])}{' (cuadra)' if bs['balanced'] else ' (¡no cuadra!)'}. Puedes verlos completos en Análisis → Libros."
            if lang == "es"
            else f"Your income statement {self._period_label(period, lang)} shows revenue of {_money(income['total_revenue'])} and net income of {_money(income['net_income'])}. Your balance sheet as of {end} has assets of {_money(bs['total_assets'])}, liabilities of {_money(bs['total_liabilities'])} and equity of {_money(bs['total_equity'])}."
        )
        return {"answer": answer, "evidence": evidence, "tools": ["income_statement", "balance_sheet"], "sources": [{"type": "structured", "title": "estados financieros derivados del diario"}]}

    def _tool_business_context(self, text: str, period: str, lang: str) -> dict[str, Any]:
        docs = knowledge.business_context_documents(self.profile, self.business_name)
        if not docs:
            return {"answer": "Todavía no tengo tu perfil de negocio: complétalo desde el onboarding." if lang == "es" else "I don't have your business profile yet.", "evidence": [], "tools": ["business_context"], "sources": []}
        week = next((d for d in docs if d["id"] == "profile_week"), None)
        summary = next(d for d in docs if d["id"] == "profile_summary")
        if lang == "es":
            answer = (f"Me contaste esto de tu semana: “{week['text']}” " if week else "") + summary["text"]
        else:
            answer = (f"You told me this about your week: “{week['text']}” " if week else "") + summary["text_en"]
        return {"answer": answer, "evidence": [], "tools": ["business_context"], "sources": [_knowledge_source(d, lang) for d in docs], "allow_llm": False}

    def _tool_concept(self, text: str, period: str, lang: str) -> dict[str, Any]:
        docs = knowledge.search(text, knowledge.business_context_documents(self.profile, self.business_name), k=2)
        if not docs:
            return self._fallback(text, lang, "concepto no encontrado")
        doc = docs[0]
        evidence = []
        # Si el concepto tiene una razón asociada, se agrega el valor real del negocio.
        r = self.analytics.ratios("30d")
        by = {x["key"]: x for x in r["ratios"]}
        link = {"liquidez": "current_ratio", "prueba_acida": "quick_ratio", "capital_trabajo": "working_capital", "margen_bruto": "gross_margin", "margen_neto": "net_margin", "inventario": "days_inventory", "deuda": "debt_to_equity"}.get(doc["id"])
        answer = doc["text"] if lang == "es" else doc.get("text_en", doc["text"])
        if link and by[link]["available"]:
            x = by[link]
            evidence.append({"label": _ratio_label(x, lang), "value": _ratio_value(x, lang), "detail": x["formula"]})
            answer += f" En tu negocio, hoy: {x['explanation']}" if lang == "es" else f" In your business today: {_ratio_label(x, lang)} = {_ratio_value(x, lang)}."
        return {"answer": answer, "evidence": evidence, "tools": ["knowledge_search"] + (["ratios"] if link else []), "sources": [_knowledge_source(d, lang) for d in docs], "suggestions": [f"¿Cómo está mi {doc['title'].split(' ')[0].lower()}?", "¿Qué debería hacer al respecto?"] if lang == "es" else ["How is mine doing?", "What should I do about it?"]}

    def _tool_unknown(self, text: str, period: str, lang: str) -> dict[str, Any]:
        docs = knowledge.search(text, knowledge.business_context_documents(self.profile, self.business_name), k=1)
        if docs and docs[0]["score"] >= 3:
            return self._tool_concept(text, period, lang)
        return self._fallback(text, lang, "sin intención")

    def _fallback(self, text: str, lang: str, reason: str) -> dict[str, Any]:
        h = self.analytics.health("month")
        evidence = [
            {"label": "Ventas este mes" if lang == "es" else "Sales this month", "value": _money(h["revenue"]["value"])},
            {"label": "Utilidad neta" if lang == "es" else "Net income", "value": _money(h["net_income"]["value"])},
            {"label": "Efectivo" if lang == "es" else "Cash", "value": _money(h["cash"]["cash_available"])},
        ]
        answer = (
            f"No estoy seguro de qué me preguntas, pero esto es lo más importante de {self.business_name} este mes: ventas {_money(h['revenue']['value'])}, utilidad neta {_money(h['net_income']['value'])}, efectivo {_money(h['cash']['cash_available'])}. Puedes preguntarme por ventas, utilidad, inventario, liquidez, gastos o qué significa un término."
            if lang == "es"
            else f"I'm not sure what you're asking, but here is the big picture for {self.business_name} this month: sales {_money(h['revenue']['value'])}, net income {_money(h['net_income']['value'])}, cash {_money(h['cash']['cash_available'])}. Ask me about sales, profit, inventory, liquidity, expenses, or what a term means."
        )
        return {"answer": answer, "evidence": evidence, "tools": ["health"], "sources": [], "allow_llm": True}

    # ---------------------------------------------------------- redacción --

    def _rewrite(self, question: str, lang: str, result: dict[str, Any]) -> str | None:
        facts = "\n".join(f"- {e['label']}: {e['value']}" + (f" ({e['detail']})" if e.get("detail") else "") for e in result.get("evidence", []))
        system = (
            "Eres el asistente financiero de Capital One Business para dueños de micro-negocios sin formación contable. "
            "Reescribe la respuesta base en un tono claro, cálido y breve (máximo 4 oraciones), en el idioma de la pregunta. "
            "REGLAS: usa únicamente las cifras de los HECHOS; no inventes ni recalcules números; no des consejos de inversión; "
            "distingue hechos de sugerencias ('tus datos muestran…', 'podrías revisar…'). Sin markdown, sin listas."
        )
        prompt = f"PREGUNTA: {question}\n\nHECHOS:\n{facts or '- (sin cifras)'}\n\nRESPUESTA BASE: {result['answer']}\n\nIdioma de salida: {'inglés' if lang == 'en' else 'español'}."
        text = self.llm.complete(system, prompt, max_tokens=400)
        if not text:
            return None
        # Guardia: toda cifra de la respuesta del LLM debe existir en los hechos
        # o en la respuesta base (nunca en la pregunta: "dime que gané un
        # millón" no convierte ese millón en un dato). Si no, se descarta la
        # redacción y se responde con la plantilla.
        if _ungrounded(text, facts + " " + result["answer"]):
            return None
        return text
