"""
Motor contable de partida doble.

El diario es la fuente de verdad. Todo lo demás (mayor, balanza, estados
financieros) se DERIVA de journal_lines; nunca se edita aparte.

Invariantes que este módulo impone:
  * cada asiento publicado balancea: SUM(debe) = SUM(haber)
  * una línea no lleva debe y haber a la vez, ni montos negativos
  * las cuentas de un asiento pertenecen al negocio y están activas
  * el mismo evento origen (source_type, source_id) no se publica dos veces
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.finance import cache, coa
from app.finance.common import ZERO, D, iso_date, new_id, now_iso, q4
from app.finance.repo import Repo


class AccountingError(ValueError):
    """Asiento inválido: se rechaza antes de tocar la base."""


class IntegrityError(RuntimeError):
    """Los datos publicados violan un invariante: se reporta, nunca se oculta."""


@dataclass
class Line:
    account_id: str
    debit: Decimal = ZERO
    credit: Decimal = ZERO
    memo: str = ""


class AccountingService:
    def __init__(self, repo: Repo):
        self.repo = repo
        # Cachés por instancia (una instancia = una request): el catálogo de
        # cuentas y los saldos por rango se piden muchas veces al armar un
        # panel, y en Snowflake cada consulta cuesta ~100 ms.
        self._accounts_cache: dict[str, dict[str, Any]] | None = None
        self._balances_cache: dict[tuple[str | None, str | None, bool], dict[str, dict[str, Decimal]]] = {}
        self._snapshot_cache: list[dict[str, Any]] | None = None

    def _invalidate(self) -> None:
        self._accounts_cache = None
        self._balances_cache.clear()
        self._snapshot_cache = None
        cache.invalidate(self._cache_key())

    # ------------------------------------------------------------ cuentas --

    def ensure_chart_of_accounts(self, category: str | None = None) -> list[dict[str, Any]]:
        """Crea las cuentas de la plantilla que falten. Idempotente: si el
        negocio ya tiene catálogo, sólo agrega las nuevas de su categoría."""
        existing = {int(a["account_number"]) for a in self.list_accounts(include_inactive=True)}
        ts = now_iso()
        for tpl in coa.template_for(category):
            if tpl.number in existing:
                continue
            self.repo.insert(
                "accounts",
                {
                    "account_id": new_id(),
                    "account_number": tpl.number,
                    "account_name": tpl.name,
                    "account_type": tpl.type,
                    "account_subtype": tpl.subtype,
                    "normal_balance": tpl.normal_balance,
                    "financial_statement": tpl.statement,
                    "parent_account_id": None,
                    "is_active": True,
                    "created_at": ts,
                    "updated_at": ts,
                },
            )
        self._invalidate()
        return self.list_accounts()

    def list_accounts(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        accounts = sorted(self._accounts().values(), key=lambda a: int(a["account_number"]))
        if include_inactive:
            return [dict(a) for a in accounts]
        return [dict(a) for a in accounts if a["is_active"]]

    def _cache_key(self) -> tuple:
        db_token = getattr(self.repo.db, "instance_id", None) or id(self.repo.db)
        return ("accounts", db_token, self.repo.business_id)

    def _accounts(self) -> dict[str, dict[str, Any]]:
        if self._accounts_cache is None:
            # Caché compartida entre requests (TTL corto): el catálogo cambia
            # sólo al inicializarse, y en Snowflake leerlo cuesta ~0.4 s.
            self._accounts_cache = cache.get(
                self._cache_key(),
                lambda: {a["account_id"]: a for a in self.repo.find("accounts", order_by="account_number")},
            )
        return self._accounts_cache

    def account(self, account_id: str) -> dict[str, Any]:
        acc = self._accounts().get(account_id)
        if acc is None:
            raise AccountingError(f"la cuenta {account_id} no existe en este negocio")
        return acc

    def account_by_subtype(self, subtype: str) -> dict[str, Any]:
        for acc in self._accounts().values():
            if acc["account_subtype"] == subtype and acc["is_active"]:
                return acc
        raise AccountingError(f"el catálogo no tiene una cuenta de tipo {subtype}")

    def account_by_number(self, number: int) -> dict[str, Any]:
        for acc in self._accounts().values():
            if int(acc["account_number"]) == number:
                return acc
        raise AccountingError(f"no existe la cuenta {number}")

    def has_chart(self) -> bool:
        return bool(self._accounts())

    # ------------------------------------------------------------ asientos --

    def find_entry_by_source(self, source_type: str, source_id: str) -> dict[str, Any] | None:
        return self.repo.find_one(
            "journal_entries",
            "source_type = :st AND source_id = :sid AND status = 'POSTED'",
            {"st": source_type, "sid": source_id},
        )

    def validate(self, lines: list[Line]) -> tuple[Decimal, Decimal]:
        if len(lines) < 2:
            raise AccountingError("un asiento necesita al menos dos líneas")
        total_debit = ZERO
        total_credit = ZERO
        for line in lines:
            debit, credit = q4(line.debit), q4(line.credit)
            if debit < 0 or credit < 0:
                raise AccountingError("los montos de un asiento no pueden ser negativos")
            if (debit > 0) == (credit > 0):
                raise AccountingError("cada línea lleva debe O haber, nunca los dos ni ninguno")
            acc = self.account(line.account_id)
            if not acc["is_active"]:
                raise AccountingError(f"la cuenta {acc['account_name']} está inactiva")
            total_debit += debit
            total_credit += credit
        if total_debit != total_credit:
            raise AccountingError(f"el asiento no balancea: debe {total_debit} vs haber {total_credit}")
        return total_debit, total_credit

    def post_entry(
        self,
        *,
        entry_date: str | date | None,
        description: str,
        source_type: str,
        source_id: str,
        lines: list[Line],
        is_adjusting: bool = False,
        allow_duplicate_source: bool = False,
    ) -> dict[str, Any]:
        """Valida y publica. Si el evento origen ya se contabilizó, regresa el
        asiento existente en vez de duplicarlo (idempotencia)."""
        if not allow_duplicate_source:
            existing = self.find_entry_by_source(source_type, source_id)
            if existing:
                return existing

        # Líneas con cero se descartan (p. ej. impuesto 0) antes de validar.
        lines = [ln for ln in lines if q4(ln.debit) != 0 or q4(ln.credit) != 0]
        total_debit, total_credit = self.validate(lines)

        ts = now_iso()
        entry = {
            "entry_id": new_id(),
            "transaction_number": self.repo.next_number("journal_entries", "transaction_number"),
            "entry_date": iso_date(entry_date),
            "description": description[:500],
            "source_type": source_type,
            "source_id": source_id,
            "status": "POSTED",
            "is_adjusting": bool(is_adjusting),
            "total_debit": total_debit,
            "total_credit": total_credit,
            "created_at": ts,
            "posted_at": ts,
        }
        self._balances_cache.clear()  # los saldos cambian al publicar
        self._snapshot_cache = None
        with self.repo.transaction():
            self.repo.insert("journal_entries", entry)
            self.repo.insert_many(
                "journal_lines",
                [
                    {
                        "line_id": new_id(),
                        "entry_id": entry["entry_id"],
                        "account_id": line.account_id,
                        "line_order": order,
                        "debit": q4(line.debit),
                        "credit": q4(line.credit),
                        "memo": (line.memo or "")[:300],
                    }
                    for order, line in enumerate(lines, start=1)
                ],
            )
        return entry

    def entry_with_lines(self, entry_id: str) -> dict[str, Any] | None:
        entry = self.repo.get("journal_entries", entry_id)
        if not entry:
            return None
        entry["lines"] = self._lines_for([entry_id]).get(entry_id, [])
        return entry

    def _lines_for(self, entry_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not entry_ids:
            return {}
        accounts = self._accounts()
        out: dict[str, list[dict[str, Any]]] = {}
        # Lotes de 200 para no armar un IN gigante.
        for i in range(0, len(entry_ids), 200):
            chunk = entry_ids[i : i + 200]
            params = {f"e{j}": eid for j, eid in enumerate(chunk)}
            placeholders = ", ".join(f":e{j}" for j in range(len(chunk)))
            rows = self.repo.query(
                f"SELECT * FROM journal_lines WHERE business_id = :business_id AND entry_id IN ({placeholders}) "
                "ORDER BY line_order",
                params,
            )
            for r in rows:
                acc = accounts.get(r["account_id"], {})
                r["account_number"] = acc.get("account_number")
                r["account_name"] = acc.get("account_name")
                out.setdefault(r["entry_id"], []).append(r)
        return out

    def journal(
        self,
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        where, params = ["status = 'POSTED'"], {}
        if start:
            where.append("entry_date >= :start")
            params["start"] = iso_date(start)
        if end:
            where.append("entry_date <= :end")
            params["end"] = iso_date(end)
        if source_type:
            where.append("source_type = :st")
            params["st"] = source_type
        entries = self.repo.find(
            "journal_entries", " AND ".join(where), params, order_by="entry_date DESC, transaction_number DESC", limit=limit
        )
        lines = self._lines_for([e["entry_id"] for e in entries])
        for e in entries:
            e["lines"] = lines.get(e["entry_id"], [])
        return entries

    # ------------------------------------------------ saldos y balanza --

    def balances(
        self,
        start: str | None = None,
        end: str | None = None,
        adjusted: bool = True,
    ) -> dict[str, dict[str, Decimal]]:
        """{account_id: {debits, credits, balance}} desde el mayor, en el rango.
        `balance` respeta el saldo normal de la cuenta."""
        key = (iso_date(start) if start else None, iso_date(end) if end else None, adjusted)
        cached = self._balances_cache.get(key)
        if cached is not None:
            return cached
        s, e = key[0], key[1]
        totals: dict[str, list[Decimal]] = {}
        for r in self.snapshot():
            if s and r["entry_date"] < s:
                continue
            if e and r["entry_date"] > e:
                continue
            if not adjusted and r["is_adjusting"]:
                continue
            slot = totals.setdefault(r["account_id"], [ZERO, ZERO])
            slot[0] += r["debits"]
            slot[1] += r["credits"]
        out: dict[str, dict[str, Decimal]] = {}
        accounts = self._accounts()
        for account_id, (debits, credits) in totals.items():
            acc = accounts.get(account_id)
            if not acc:
                continue
            signed = debits - credits if acc["normal_balance"] == coa.DEBIT else credits - debits
            out[account_id] = {"debits": debits, "credits": credits, "balance": signed}
        self._balances_cache[key] = out
        return out

    def snapshot(self) -> list[dict[str, Any]]:
        """El mayor agregado por (cuenta, fecha, ajuste, origen): UNA consulta
        por request, y de ahí salen todos los saldos, balanzas, estados y
        flujos que pida la pantalla. Para un micro-negocio son cientos de
        filas; en Snowflake cada viaje cuesta ~0.3 s, así que esto convierte
        decenas de consultas en una."""
        if self._snapshot_cache is None:
            rows = self.repo.query(
                "SELECT account_id, entry_date, is_adjusting, source_type, "
                "COALESCE(SUM(debit), 0) AS debits, COALESCE(SUM(credit), 0) AS credits "
                "FROM v_general_ledger WHERE business_id = :business_id "
                "GROUP BY account_id, entry_date, is_adjusting, source_type"
            )
            for r in rows:
                r["debits"] = D(r["debits"])
                r["credits"] = D(r["credits"])
                r["is_adjusting"] = bool(r["is_adjusting"])
                r["entry_date"] = str(r["entry_date"])[:10]
            self._snapshot_cache = rows
        return self._snapshot_cache

    def has_postings(self) -> bool:
        return bool(self.snapshot())

    def cash_flows(self, start: str, end: str) -> dict[str, Any]:
        """Entradas (cargos) y salidas (abonos) de caja/banco en el rango,
        por tipo de evento origen. Desde el snapshot: sin consulta extra."""
        accounts = self._accounts()
        s, e = iso_date(start), iso_date(end)
        by_source: dict[str, list[Decimal]] = {}
        for r in self.snapshot():
            acc = accounts.get(r["account_id"])
            if not acc or acc["account_subtype"] not in coa.CASH_SUBTYPES:
                continue
            if r["entry_date"] < s or r["entry_date"] > e:
                continue
            slot = by_source.setdefault(r["source_type"], [ZERO, ZERO])
            slot[0] += r["debits"]
            slot[1] += r["credits"]
        inflows = sum((v[0] for v in by_source.values()), ZERO)
        outflows = sum((v[1] for v in by_source.values()), ZERO)
        return {
            "inflows": inflows,
            "outflows": outflows,
            "by_source": [{"source_type": k, "inflow": v[0], "outflow": v[1]} for k, v in by_source.items()],
        }

    def ledger(self, account_id: str, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        acc = self.account(account_id)
        where, params = ["business_id = :business_id", "account_id = :acc"], {"acc": account_id}
        if start:
            where.append("entry_date >= :start")
            params["start"] = iso_date(start)
        if end:
            where.append("entry_date <= :end")
            params["end"] = iso_date(end)
        rows = self.repo.query(
            f"SELECT * FROM v_general_ledger WHERE {' AND '.join(where)} "
            "ORDER BY entry_date, transaction_number, line_order",
            params,
        )
        running = ZERO
        sign = 1 if acc["normal_balance"] == coa.DEBIT else -1
        for r in rows:
            running += sign * (D(r["debit"]) - D(r["credit"]))
            r["running_balance"] = running
        return {
            "account": acc,
            "lines": rows,
            "total_debits": sum((D(r["debit"]) for r in rows), ZERO),
            "total_credits": sum((D(r["credit"]) for r in rows), ZERO),
            "balance": running,
        }

    def general_ledger(self, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        bal = self.balances(start, end)
        out = []
        for acc in self.list_accounts():
            b = bal.get(acc["account_id"], {"debits": ZERO, "credits": ZERO, "balance": ZERO})
            out.append({**acc, "total_debits": b["debits"], "total_credits": b["credits"], "balance": b["balance"]})
        return out

    def trial_balance(self, as_of: str | None = None, adjusted: bool = True) -> dict[str, Any]:
        bal = self.balances(None, as_of, adjusted=adjusted)
        rows, total_debit, total_credit = [], ZERO, ZERO
        for acc in self.list_accounts():
            b = bal.get(acc["account_id"])
            if not b or (b["debits"] == 0 and b["credits"] == 0):
                continue
            net = b["debits"] - b["credits"]
            debit_balance = net if net > 0 else ZERO
            credit_balance = -net if net < 0 else ZERO
            total_debit += debit_balance
            total_credit += credit_balance
            rows.append({**acc, "debit_balance": debit_balance, "credit_balance": credit_balance})
        balanced = q4(total_debit) == q4(total_credit)
        if not balanced:
            # Nunca silencioso: el frontend lo muestra como error de integridad
            # y los tests lo cazan. No se "corrige" sumando de más.
            self.repo.insert(
                "business_events",
                {
                    "event_id": new_id(),
                    "event_type": "INTEGRITY_ERROR",
                    "source_type": "TRIAL_BALANCE",
                    "source_id": as_of or "all",
                    "payload": f'{{"total_debit": "{total_debit}", "total_credit": "{total_credit}"}}',
                    "journal_entry_id": None,
                    "created_at": now_iso(),
                },
            )
        return {
            "as_of": iso_date(as_of) if as_of else None,
            "adjusted": adjusted,
            "rows": rows,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balanced": balanced,
        }

    # ------------------------------------------------ estados financieros --

    def income_statement(self, start: str | None, end: str | None, adjusted: bool = True) -> dict[str, Any]:
        bal = self.balances(start, end, adjusted=adjusted)
        revenue, cogs, opex = [], [], []
        for acc in self.list_accounts():
            if acc["financial_statement"] != coa.INCOME_STATEMENT:
                continue
            b = bal.get(acc["account_id"])
            if not b or b["balance"] == 0:
                continue
            row = {**acc, "amount": b["balance"]}
            if acc["account_type"] == coa.REVENUE:
                revenue.append(row)
            elif acc["account_subtype"] in coa.COGS_SUBTYPES:
                cogs.append(row)
            else:
                opex.append(row)
        total_revenue = sum((r["amount"] for r in revenue), ZERO)
        total_cogs = sum((r["amount"] for r in cogs), ZERO)
        total_opex = sum((r["amount"] for r in opex), ZERO)
        gross_profit = total_revenue - total_cogs
        net_income = gross_profit - total_opex
        return {
            "start": iso_date(start) if start else None,
            "end": iso_date(end) if end else None,
            "adjusted": adjusted,
            "revenue": revenue,
            "cogs": cogs,
            "operating_expenses": opex,
            "total_revenue": total_revenue,
            "total_cogs": total_cogs,
            "gross_profit": gross_profit,
            "total_operating_expenses": total_opex,
            "net_income": net_income,
        }

    def balance_sheet(self, as_of: str | None = None, adjusted: bool = True) -> dict[str, Any]:
        bal = self.balances(None, as_of, adjusted=adjusted)
        assets, liabilities, equity = [], [], []
        for acc in self.list_accounts():
            if acc["financial_statement"] != coa.BALANCE_SHEET:
                continue
            b = bal.get(acc["account_id"])
            if not b or b["balance"] == 0:
                continue
            row = {**acc, "amount": b["balance"]}
            {coa.ASSET: assets, coa.LIABILITY: liabilities, coa.EQUITY: equity}[acc["account_type"]].append(row)

        def signed_total(rows: list[dict[str, Any]], account_type: str) -> Decimal:
            base = coa.NORMAL_BALANCE[account_type]
            return sum(((r["amount"] if r["normal_balance"] == base else -r["amount"]) for r in rows), ZERO)

        total_assets = signed_total(assets, coa.ASSET)
        total_liabilities = signed_total(liabilities, coa.LIABILITY)
        equity_accounts = signed_total(equity, coa.EQUITY)
        # Sin asientos de cierre, la utilidad acumulada vive en las cuentas de
        # resultados: se presenta como "utilidad del periodo" dentro del capital.
        earnings = self.income_statement(None, as_of, adjusted=adjusted)["net_income"]
        total_equity = equity_accounts + earnings
        difference = q4(total_assets - (total_liabilities + total_equity))
        return {
            "as_of": iso_date(as_of) if as_of else None,
            "adjusted": adjusted,
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "current_earnings": earnings,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "balanced": difference == 0,
            "difference": difference,
        }

    # ------------------------------------------------------- ajustes --

    def post_adjustment(
        self,
        *,
        description: str,
        lines: list[Line],
        entry_date: str | None = None,
    ) -> dict[str, Any]:
        return self.post_entry(
            entry_date=entry_date,
            description=description,
            source_type="ADJUSTMENT",
            source_id=new_id(),
            lines=lines,
            is_adjusting=True,
        )

    def post_depreciation(self, amount: Decimal, entry_date: str | None = None, memo: str = "") -> dict[str, Any]:
        dep = self.account_by_subtype("DEPRECIATION")
        accum = self.account_by_subtype("ACCUM_DEPRECIATION")
        return self.post_adjustment(
            description=memo or "Depreciación del equipo",
            entry_date=entry_date,
            lines=[Line(dep["account_id"], debit=D(amount)), Line(accum["account_id"], credit=D(amount))],
        )
