"""
Motor analítico: razones financieras, salud de caja, tendencias e insights.

Regla: los números salen de aquí (backend, desde el diario), nunca de React
ni del LLM. Cada razón trae `available`, y cuando no se puede calcular dice
por qué, en vez de inventar un cero.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.finance import coa
from app.finance.accounting import AccountingService
from app.finance.common import (
    ZERO,
    D,
    fmt_money,
    period_bounds,
    previous_period,
    q2,
    safe_div,
    today,
)
from app.finance.inventory import InventoryService
from app.finance.purchases import PurchaseService
from app.finance.repo import Repo
from app.finance.sales import SalesService

PERIOD_LABELS = {
    "today": "hoy",
    "yesterday": "ayer",
    "week": "esta semana",
    "last_week": "la semana pasada",
    "month": "este mes",
    "last_month": "el mes pasado",
    "7d": "los últimos 7 días",
    "30d": "los últimos 30 días",
    "90d": "los últimos 90 días",
    "year": "este año",
    "all": "desde el inicio",
}


def _status(value: Decimal | None, good: Decimal, attention: Decimal, higher_is_better: bool = True) -> str:
    if value is None:
        return "neutral"
    if higher_is_better:
        return "good" if value >= good else "attention" if value >= attention else "critical"
    return "good" if value <= good else "attention" if value <= attention else "critical"


def _pct_change(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return (current - previous) / abs(previous) * 100


class AnalyticsService:
    def __init__(
        self,
        repo: Repo,
        accounting: AccountingService,
        inventory: InventoryService,
        sales: SalesService,
        purchases: PurchaseService,
        category: str | None = None,
    ):
        self.repo = repo
        self.accounting = accounting
        self.inventory = inventory
        self.sales = sales
        self.purchases = purchases
        self.category = (category or "").lower()

    # ------------------------------------------------------- utilidades --

    def resolve_period(self, period: str) -> tuple[str, str, str]:
        start, end = period_bounds(period)
        return start.isoformat(), end.isoformat(), PERIOD_LABELS.get(period, period)

    def _subtype_total(self, balances: dict[str, dict[str, Decimal]], subtypes: set[str]) -> Decimal:
        total = ZERO
        for acc in self.accounting.list_accounts():
            if acc["account_subtype"] in subtypes:
                total += balances.get(acc["account_id"], {}).get("balance", ZERO)
        return total

    def position(self, as_of: str | None = None) -> dict[str, Decimal]:
        """Saldos clave del balance a una fecha."""
        bal = self.accounting.balances(None, as_of)
        bs = self.accounting.balance_sheet(as_of)
        cash = self._subtype_total(bal, coa.CASH_SUBTYPES)
        receivables = self._subtype_total(bal, {"RECEIVABLE"})
        inventory = self._subtype_total(bal, {"INVENTORY"})
        current_assets = self._subtype_total(bal, coa.CURRENT_ASSET_SUBTYPES)
        current_liabilities = self._subtype_total(bal, coa.CURRENT_LIABILITY_SUBTYPES)
        card = self._subtype_total(bal, {"CARD"})
        tax = self._subtype_total(bal, {"TAX_PAYABLE"})
        return {
            "cash": cash,
            "receivables": receivables,
            "inventory": inventory,
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
            "card_balance": card,
            "tax_payable": tax,
            "total_assets": bs["total_assets"],
            "total_liabilities": bs["total_liabilities"],
            "total_equity": bs["total_equity"],
            "working_capital": current_assets - current_liabilities,
        }

    # -------------------------------------------------------------- razones --

    def ratios(self, period: str = "30d") -> dict[str, Any]:
        start, end, label = self.resolve_period(period)
        pos = self.position(end)
        pos_start = self.position((date.fromisoformat(start)).isoformat())
        income = self.accounting.income_statement(start, end)
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        out: list[dict[str, Any]] = []

        def add(key: str, label_es: str, group: str, value: Decimal | None, *, status: str, formula: str, explanation: str, reason: str | None = None, unit: str = "x", inputs: dict[str, Any] | None = None):
            out.append(
                {
                    "key": key,
                    "label": label_es,
                    "group": group,
                    "value": value,
                    "unit": unit,
                    "available": value is not None,
                    "reason": reason,
                    "status": status if value is not None else "neutral",
                    "formula": formula,
                    "explanation": explanation,
                    "inputs": inputs or {},
                }
            )

        # Liquidez
        cl = pos["current_liabilities"]
        cr = safe_div(pos["current_assets"], cl)
        add(
            "current_ratio", "Razón circulante", "liquidez", cr,
            status=_status(cr, D("1.5"), D("1.0")),
            formula="Activo circulante ÷ Pasivo a corto plazo",
            explanation=(f"Tienes {fmt_money(cr)} en recursos a corto plazo por cada $1.00 que debes pronto." if cr is not None else "No debes nada a corto plazo, así que la razón no aplica."),
            reason=None if cl else "sin pasivos a corto plazo",
            inputs={"current_assets": pos["current_assets"], "current_liabilities": cl},
        )
        quick_assets = pos["cash"] + pos["receivables"]
        qr = safe_div(quick_assets, cl)
        add(
            "quick_ratio", "Prueba ácida", "liquidez", qr,
            status=_status(qr, D("1.0"), D("0.5")),
            formula="(Efectivo + Cuentas por cobrar) ÷ Pasivo a corto plazo",
            explanation=(f"Sin contar inventario, cubres {fmt_money(qr)} por cada $1.00 de deuda cercana." if qr is not None else "No hay deuda a corto plazo que cubrir."),
            reason=None if cl else "sin pasivos a corto plazo",
            inputs={"cash": pos["cash"], "receivables": pos["receivables"], "current_liabilities": cl},
        )
        cashr = safe_div(pos["cash"], cl)
        add(
            "cash_ratio", "Razón de efectivo", "liquidez", cashr,
            status=_status(cashr, D("0.5"), D("0.2")),
            formula="Efectivo ÷ Pasivo a corto plazo",
            explanation=(f"Con el efectivo de hoy pagarías el {q2(cashr * 100)}% de lo que debes pronto." if cashr is not None else "No hay deuda a corto plazo."),
            reason=None if cl else "sin pasivos a corto plazo",
        )
        wc = pos["working_capital"]
        add(
            "working_capital", "Capital de trabajo", "liquidez", wc,
            status="good" if wc > 0 else "critical",
            formula="Activo circulante − Pasivo a corto plazo",
            explanation=(f"Después de pagar todo lo que debes pronto te quedarían {fmt_money(wc)} para operar." if wc >= 0 else f"Te faltarían {fmt_money(-wc)} para cubrir lo que debes pronto."),
            unit="$",
        )

        # Rentabilidad
        rev = income["total_revenue"]
        gm = safe_div(income["gross_profit"], rev)
        gm_pct = gm * 100 if gm is not None else None
        good_gm = D("55") if self.category in {"comida", "belleza", "servicios"} else D("40")
        add(
            "gross_margin", "Margen bruto", "rentabilidad", gm_pct,
            status=_status(gm_pct, good_gm, good_gm - 20),
            formula="(Ventas − Costo de ventas) ÷ Ventas",
            explanation=(f"De cada $100 vendidos, {fmt_money(gm_pct)} quedan después de pagar los insumos." if gm_pct is not None else "Todavía no hay ventas en el periodo."),
            reason=None if rev else "sin ventas en el periodo", unit="%",
            inputs={"revenue": rev, "cogs": income["total_cogs"]},
        )
        om = safe_div(income["net_income"], rev)
        om_pct = om * 100 if om is not None else None
        add(
            "net_margin", "Margen neto", "rentabilidad", om_pct,
            status=_status(om_pct, D("10"), D("0")),
            formula="Utilidad neta ÷ Ventas",
            explanation=(f"De cada $100 vendidos, {fmt_money(om_pct)} son ganancia después de todos los gastos." if om_pct is not None else "Todavía no hay ventas en el periodo."),
            reason=None if rev else "sin ventas en el periodo", unit="%",
            inputs={"revenue": rev, "net_income": income["net_income"]},
        )
        roa = safe_div(income["net_income"], pos["total_assets"])
        roa_pct = roa * 100 if roa is not None else None
        add(
            "return_on_assets", "Rendimiento sobre activos", "rentabilidad", roa_pct,
            status=_status(roa_pct, D("5"), D("0")),
            formula="Utilidad neta ÷ Activos totales",
            explanation=(f"Cada $100 invertidos en el negocio produjeron {fmt_money(roa_pct)} de utilidad en {label}." if roa_pct is not None else "Sin activos registrados."),
            reason=None if pos["total_assets"] else "sin activos", unit="%",
        )

        # Apalancamiento
        eq = pos["total_equity"]
        de = safe_div(pos["total_liabilities"], eq) if eq > 0 else None
        add(
            "debt_to_equity", "Deuda sobre capital", "apalancamiento", de,
            status=_status(de, D("1.0"), D("2.0"), higher_is_better=False),
            formula="Pasivo total ÷ Capital",
            explanation=(f"Debes {fmt_money(de)} por cada $1.00 que es tuyo en el negocio." if de is not None else "El capital es cero o negativo: la deuda supera lo que es tuyo."),
            reason=None if eq > 0 else "capital no positivo",
        )
        dr = safe_div(pos["total_liabilities"], pos["total_assets"])
        add(
            "debt_ratio", "Razón de deuda", "apalancamiento", dr,
            status=_status(dr, D("0.5"), D("0.7"), higher_is_better=False),
            formula="Pasivo total ÷ Activos totales",
            explanation=(f"El {q2(dr * 100)}% de lo que tiene el negocio está financiado con deuda." if dr is not None else "Sin activos registrados."),
            reason=None if pos["total_assets"] else "sin activos",
        )

        # Eficiencia
        avg_inventory = (pos["inventory"] + pos_start["inventory"]) / 2
        turnover = safe_div(income["total_cogs"], avg_inventory) if avg_inventory > 0 else None
        dio = (D(days) / turnover) if turnover and turnover > 0 else None
        good_dio = D("14") if self.category == "comida" else D("45")
        add(
            "inventory_turnover", "Rotación de inventario", "eficiencia", turnover,
            status=_status(turnover, D("2") if self.category == "comida" else D("1"), D("1") if self.category == "comida" else D("0.5")),
            formula="Costo de ventas ÷ Inventario promedio",
            explanation=(f"Vendiste el inventario completo {q2(turnover)} veces en {label}." if turnover is not None else "No hay inventario o costo de ventas suficiente para medirlo."),
            reason=None if turnover is not None else "sin inventario o sin costo de ventas en el periodo",
            inputs={"cogs": income["total_cogs"], "avg_inventory": avg_inventory, "days": days},
        )
        add(
            "days_inventory", "Días de inventario", "eficiencia", dio,
            status=_status(dio, good_dio, good_dio * 3, higher_is_better=False),
            formula="Días del periodo ÷ Rotación",
            explanation=(f"En promedio, un insumo pasa {q2(dio)} días en el almacén antes de venderse." if dio is not None else "No se puede medir todavía."),
            reason=None if dio is not None else "sin rotación medible", unit="días",
        )
        return {"period": {"key": period, "start": start, "end": end, "label": label}, "ratios": out, "position": pos}

    # ------------------------------------------------------- caja --

    def cash_intelligence(self, period: str = "30d") -> dict[str, Any]:
        start, end, label = self.resolve_period(period)
        pos = self.position(end)
        flows = self._cash_flows(start, end)
        prev_start, prev_end = previous_period(date.fromisoformat(start), date.fromisoformat(end))
        prev_flows = self._cash_flows(prev_start.isoformat(), prev_end.isoformat())
        obligations = pos["current_liabilities"]
        cash = pos["cash"]
        coverage = safe_div(cash, obligations)
        if obligations == 0:
            status, headline = "good", "No debes nada a corto plazo"
        elif coverage is not None and coverage >= 1:
            status, headline = "good", "Tu efectivo cubre lo que debes pronto"
        elif coverage is not None and coverage >= D("0.5"):
            status, headline = "attention", "Tu efectivo cubre sólo una parte de lo que debes pronto"
        else:
            status, headline = "critical", "Tu efectivo no alcanza para lo que debes pronto"
        inventory_share = safe_div(pos["inventory"], pos["current_assets"])
        return {
            "period": {"key": period, "start": start, "end": end, "label": label},
            "cash_available": cash,
            "inflows": flows["inflows"],
            "outflows": flows["outflows"],
            "net_change": flows["inflows"] - flows["outflows"],
            "previous_net_change": prev_flows["inflows"] - prev_flows["outflows"],
            "short_term_obligations": obligations,
            "card_balance": pos["card_balance"],
            "tax_payable": pos["tax_payable"],
            "working_capital": pos["working_capital"],
            "inventory_tied_up": pos["inventory"],
            "inventory_share_of_current_assets": inventory_share * 100 if inventory_share is not None else None,
            "coverage": coverage,
            "status": status,
            "headline": headline,
            "explanation": (
                f"Tienes {fmt_money(cash)} disponibles y debes {fmt_money(obligations)} a corto plazo "
                f"(tarjeta {fmt_money(pos['card_balance'])}, impuestos {fmt_money(pos['tax_payable'])}). "
                f"En {label} entraron {fmt_money(flows['inflows'])} y salieron {fmt_money(flows['outflows'])}."
            ),
            "operating_flows": flows["by_source"],
        }

    def _cash_flows(self, start: str, end: str) -> dict[str, Any]:
        return self.accounting.cash_flows(start, end)

    # ---------------------------------------------------- panel de salud --

    def health(self, period: str = "month") -> dict[str, Any]:
        start, end, label = self.resolve_period(period)
        prev_start, prev_end = previous_period(date.fromisoformat(start), date.fromisoformat(end))
        income = self.accounting.income_statement(start, end)
        prev_income = self.accounting.income_statement(prev_start.isoformat(), prev_end.isoformat())
        sales_now = self.sales.sales_summary(start, end)
        sales_prev = self.sales.sales_summary(prev_start.isoformat(), prev_end.isoformat())
        cash = self.cash_intelligence(period)
        ratios = self.ratios(period)
        by_key = {r["key"]: r for r in ratios["ratios"]}
        inventory = self.inventory.summary()
        tb = self.accounting.trial_balance(end)
        bs = self.accounting.balance_sheet(end)
        pending = int(
            self.repo.scalar(
                "SELECT COUNT(*) FROM card_transactions WHERE business_id = :business_id AND classification_status = 'NEEDS_REVIEW'"
            )
            or 0
        )

        attention: list[dict[str, Any]] = []
        if cash["status"] != "good":
            attention.append({"id": "cash", "severity": cash["status"], "title": cash["headline"], "body": cash["explanation"], "route": "/analisis", "lesson": "cash"})
        gm = by_key["gross_margin"]
        if gm["available"] and gm["status"] != "good":
            attention.append({"id": "margin", "severity": gm["status"], "title": "Tu margen por venta está bajo", "body": gm["explanation"], "route": "/vender", "lesson": "margin"})
        if inventory["low_stock_items"]:
            names = ", ".join(i["name"] for i in inventory["low_stock_items"][:3])
            attention.append({"id": "stock", "severity": "attention", "title": "Insumos por agotarse", "body": f"Revisa {names}: están en o por debajo de su punto de reorden.", "route": "/inventario", "lesson": "inventory"})
        dio = by_key["days_inventory"]
        if dio["available"] and dio["status"] == "critical":
            attention.append({"id": "overstock", "severity": "attention", "title": "Hay efectivo atrapado en inventario", "body": dio["explanation"], "route": "/inventario", "lesson": "inventory"})
        if pending:
            attention.append({"id": "review", "severity": "info", "title": f"{pending} compra(s) por confirmar", "body": "Dinos qué fueron y el libro se ajusta solo.", "route": "/compras", "lesson": None})
        net_change = _pct_change(income["net_income"], prev_income["net_income"])
        if net_change is not None and net_change < -15:
            attention.append({"id": "profit_drop", "severity": "attention", "title": "Tu utilidad bajó frente al periodo anterior", "body": "Pregúntale al asistente por qué: compara ventas, costos y gastos.", "route": "/asistente", "lesson": "margin"})

        return {
            "period": {"key": period, "start": start, "end": end, "label": label},
            "revenue": {"value": income["total_revenue"], "previous": prev_income["total_revenue"], "change_pct": _pct_change(income["total_revenue"], prev_income["total_revenue"])},
            "gross_profit": {"value": income["gross_profit"], "previous": prev_income["gross_profit"], "change_pct": _pct_change(income["gross_profit"], prev_income["gross_profit"])},
            "net_income": {"value": income["net_income"], "previous": prev_income["net_income"], "change_pct": net_change},
            "expenses": {"value": income["total_operating_expenses"], "previous": prev_income["total_operating_expenses"], "change_pct": _pct_change(income["total_operating_expenses"], prev_income["total_operating_expenses"])},
            "orders": {"value": sales_now["order_count"], "previous": sales_prev["order_count"]},
            "average_ticket": sales_now["average_ticket"],
            "cash": cash,
            "liquidity": by_key["current_ratio"],
            "margin": gm,
            "inventory": {"value": inventory["total_value"], "item_count": inventory["item_count"], "low_stock": [i["name"] for i in inventory["low_stock_items"]], "days_inventory": dio},
            "top_items": sales_now["by_item"][:5],
            "attention": attention,
            "ratios": ratios["ratios"],
            "integrity": {"trial_balance_balanced": tb["balanced"], "balance_sheet_balanced": bs["balanced"]},
        }

    # -------------------------------------------------- por qué cambió --

    def profit_drivers(self, period: str = "month") -> dict[str, Any]:
        start, end, label = self.resolve_period(period)
        prev_start, prev_end = previous_period(date.fromisoformat(start), date.fromisoformat(end))
        now = self.accounting.income_statement(start, end)
        prev = self.accounting.income_statement(prev_start.isoformat(), prev_end.isoformat())
        sales_now = self.sales.sales_summary(start, end)
        sales_prev = self.sales.sales_summary(prev_start.isoformat(), prev_end.isoformat())

        def by_name(rows: list[dict[str, Any]]) -> dict[str, Decimal]:
            return {r["account_name"]: r["amount"] for r in rows}

        opex_now, opex_prev = by_name(now["operating_expenses"]), by_name(prev["operating_expenses"])
        expense_changes = []
        for name in set(opex_now) | set(opex_prev):
            delta = opex_now.get(name, ZERO) - opex_prev.get(name, ZERO)
            if delta != 0:
                expense_changes.append({"account_name": name, "current": opex_now.get(name, ZERO), "previous": opex_prev.get(name, ZERO), "delta": delta})
        expense_changes.sort(key=lambda x: abs(x["delta"]), reverse=True)

        items_now = {i["name"]: i for i in sales_now["by_item"]}
        items_prev = {i["name"]: i for i in sales_prev["by_item"]}
        product_changes = []
        for name in set(items_now) | set(items_prev):
            cur, pre = items_now.get(name), items_prev.get(name)
            product_changes.append(
                {
                    "name": name,
                    "units": cur["units"] if cur else ZERO,
                    "previous_units": pre["units"] if pre else ZERO,
                    "gross_profit": cur["gross_profit"] if cur else ZERO,
                    "previous_gross_profit": pre["gross_profit"] if pre else ZERO,
                    "delta": (cur["gross_profit"] if cur else ZERO) - (pre["gross_profit"] if pre else ZERO),
                }
            )
        product_changes.sort(key=lambda x: abs(x["delta"]), reverse=True)

        gm_now = safe_div(now["gross_profit"], now["total_revenue"])
        gm_prev = safe_div(prev["gross_profit"], prev["total_revenue"])
        drivers = []
        rev_delta = now["total_revenue"] - prev["total_revenue"]
        cogs_delta = now["total_cogs"] - prev["total_cogs"]
        opex_delta = now["total_operating_expenses"] - prev["total_operating_expenses"]
        if rev_delta != 0:
            drivers.append({"driver": "revenue", "label": "Ventas", "impact": rev_delta, "detail": f"Las ventas pasaron de {fmt_money(prev['total_revenue'])} a {fmt_money(now['total_revenue'])}."})
        if cogs_delta != 0:
            drivers.append({"driver": "cogs", "label": "Costo de insumos", "impact": -cogs_delta, "detail": f"El costo de lo vendido pasó de {fmt_money(prev['total_cogs'])} a {fmt_money(now['total_cogs'])}" + (f" (margen bruto {q2(gm_prev * 100)}% → {q2(gm_now * 100)}%)." if gm_now is not None and gm_prev is not None else ".")})
        if opex_delta != 0:
            top = expense_changes[0] if expense_changes else None
            drivers.append({"driver": "expenses", "label": "Gastos de operación", "impact": -opex_delta, "detail": f"Los gastos pasaron de {fmt_money(prev['total_operating_expenses'])} a {fmt_money(now['total_operating_expenses'])}" + (f"; el mayor cambio fue {top['account_name']} ({'+' if top['delta'] > 0 else ''}{fmt_money(top['delta'])})." if top else ".")})
        drivers.sort(key=lambda d: abs(d["impact"]), reverse=True)
        return {
            "period": {"key": period, "start": start, "end": end, "label": label},
            "previous_period": {"start": prev_start.isoformat(), "end": prev_end.isoformat()},
            "net_income": now["net_income"],
            "previous_net_income": prev["net_income"],
            "delta": now["net_income"] - prev["net_income"],
            "revenue": now["total_revenue"],
            "previous_revenue": prev["total_revenue"],
            "cogs": now["total_cogs"],
            "previous_cogs": prev["total_cogs"],
            "operating_expenses": now["total_operating_expenses"],
            "previous_operating_expenses": prev["total_operating_expenses"],
            "gross_margin_pct": gm_now * 100 if gm_now is not None else None,
            "previous_gross_margin_pct": gm_prev * 100 if gm_prev is not None else None,
            "orders": sales_now["order_count"],
            "previous_orders": sales_prev["order_count"],
            "drivers": drivers,
            "expense_changes": expense_changes[:6],
            "product_changes": product_changes[:6],
        }

    # ------------------------------------------------- educación contextual --

    def insights(self) -> list[dict[str, Any]]:
        """Disparadores de educación basados en los datos reales, en el mismo
        formato que los del onboarding (frontend/src/financial-literacy)."""
        health = self.health("month")
        out = []
        cash = health["cash"]
        if cash["status"] in {"attention", "critical"}:
            out.append({"id": "data_low_liquidity", "lesson": "cash", "title": "Tu caja necesita atención esta semana", "body": cash["explanation"], "action": "Ver mi caja de los próximos 7 días", "evidence": {"cash": cash["cash_available"], "obligations": cash["short_term_obligations"]}})
        gm = health["margin"]
        if gm["available"] and gm["status"] != "good":
            out.append({"id": "data_low_margin", "lesson": "margin", "title": "Cada venta te está dejando poco", "body": gm["explanation"] + " Revisa el precio o el costo de tus productos más vendidos.", "action": "Calcular mi margen por producto", "evidence": {"gross_margin_pct": gm["value"]}})
        dio = health["inventory"]["days_inventory"]
        if dio["available"] and dio["status"] != "good":
            out.append({"id": "data_overstock", "lesson": "inventory", "title": "Tu efectivo también se queda atrapado en el almacén", "body": dio["explanation"] + f" Hoy tienes {fmt_money(health['inventory']['value'])} en inventario.", "action": "Ver qué se está moviendo lento", "evidence": {"days_inventory": dio["value"], "inventory_value": health["inventory"]["value"]}})
        if health["inventory"]["low_stock"]:
            out.append({"id": "data_stockout", "lesson": "inventory", "title": "Cuándo volver a pedir", "body": "Estos insumos ya tocaron su punto de reorden: " + ", ".join(health["inventory"]["low_stock"][:4]) + ". Pedir a tiempo evita perder ventas.", "action": "Calcular mi punto de reorden", "evidence": {"low_stock": health["inventory"]["low_stock"]}})
        ratios = {r["key"]: r for r in health["ratios"]}
        de = ratios.get("debt_to_equity")
        if de and de["available"] and de["status"] != "good":
            out.append({"id": "data_leverage", "lesson": "cash", "title": "La tarjeta está financiando tu operación", "body": de["explanation"] + " Pagarla a tiempo evita intereses que se comen tu margen.", "action": "Revisar cómo y cuándo pago", "evidence": {"debt_to_equity": de["value"]}})
        return out

    # -------------------------------------------------- serie temporal --

    def timeseries(self, period: str = "30d") -> list[dict[str, Any]]:
        start, end, _ = self.resolve_period(period)
        return self.sales.sales_by_day(start, end)

    def as_of_today(self) -> str:
        return today().isoformat()
