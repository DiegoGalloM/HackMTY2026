"""
Preguntas doradas del asistente (Fase 7 del roadmap).

Los casos viven en tests/golden/asistente_preguntas_doradas.json. Cada uno se
corre contra las dos demos sembradas en una fecha fija, así la historia es
siempre la misma. Tres capas de comprobación:

  1. Enrutamiento y forma: intención, idioma, periodo, etiquetas de evidencia
     y textos obligatorios/prohibidos.
  2. Cifras contra el motor: las cifras clave se recalculan con los servicios
     financieros (no se copian del asistente) y la evidencia debe coincidir.
  3. Guardia anti-alucinación: cada pregunta pasa por un LLM tramposo. Una
     reescritura fiel se acepta; inventar un monto, un porcentaje, una cantidad
     o "un millón" se rechaza y la respuesta vuelve a la plantilla.

Para agregar un caso basta con editar el JSON.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.config import Settings
from app.db.sqlite_db import SqliteDatabase
from app.finance import common, demo
from app.finance.assistant import INTENT_PATTERNS, _money
from app.finance.common import D
from app.finance.deps import FinanceContext
from app.finance.llm import LLMProvider

GOLDEN_PATH = Path(__file__).parent / "golden" / "asistente_preguntas_doradas.json"
GOLDEN = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
CASES = GOLDEN["casos"]
FIXED_DAY = date.fromisoformat(GOLDEN["fecha_fija"])


class _ScriptedLLM(LLMProvider):
    """LLM de prueba: escribe lo que `write(respuesta_base)` diga y recuerda si lo llamaron."""

    name = "scripted"

    def __init__(self, write: Callable[[str], str]):
        self.write = write
        self.calls = 0

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str | None:
        self.calls += 1
        base = prompt.split("RESPUESTA BASE: ", 1)[1].rsplit("\n\nIdioma de salida:", 1)[0]
        return self.write(base)


@pytest.fixture(scope="module")
def businesses():
    """Las dos demos sembradas una sola vez, con la fecha fija activa durante todo el módulo."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(common, "today", lambda: FIXED_DAY)
        mp.setattr(demo, "today", lambda: FIXED_DAY)
        seeded = {}
        for key in ("panaderia", "estetica"):
            db = SqliteDatabase(":memory:")
            db.ensure_schema()
            demo.DemoSeeder(db, f"biz_{key}", key).seed()
            seeded[key] = db
        yield seeded


def _ctx(businesses: dict[str, SqliteDatabase], key: str, llm: LLMProvider | None = None) -> FinanceContext:
    b = demo.DEMO_BUSINESSES[key]
    return FinanceContext(
        business_id=f"biz_{key}", business_name=b.business_name, db=businesses[key],
        settings=Settings(use_snowflake=False, jwt_secret="x" * 40), profile=b.profile, llm=llm,
    )


def _evidence(answer: dict[str, Any]) -> dict[str, str]:
    return {e["label"]: e["value"] for e in answer["evidence"]}


# --- 1 y 2: enrutamiento, forma y cifras contra el motor ---------------------


def _period_bounds(ctx: FinanceContext, period: str) -> tuple[str, str]:
    start, end, _ = ctx.analytics.resolve_period(period)
    return start, end


def _check_engine(ctx: FinanceContext, case: dict[str, Any], answer: dict[str, Any]) -> None:
    kind, _, arg = case["engine"].partition(":")
    ev = _evidence(answer)
    es = answer["language"] == "es"

    if kind == "revenue":
        summary = ctx.sales.sales_summary(*_period_bounds(ctx, answer["period"]))
        expected = _money(summary["revenue"])
        assert ev["Ventas" if es else "Sales"] == expected
        if summary["order_count"]:
            assert expected in answer["answer"]
    elif kind == "net_income":
        income = ctx.accounting.income_statement(*_period_bounds(ctx, answer["period"]))
        expected = _money(income["net_income"])
        assert ev["Utilidad neta" if es else "Net income"] == expected
        assert expected in answer["answer"]
    elif kind == "working_capital":
        ratios = {r["key"]: r for r in ctx.analytics.ratios(answer["period"])["ratios"]}
        assert ev["Capital de trabajo" if es else "Working capital"] == _money(ratios["working_capital"]["value"])
    elif kind == "cash_available":
        cash = ctx.analytics.cash_intelligence(answer["period"])
        assert ev["Efectivo disponible" if es else "Cash available"] == _money(cash["cash_available"])
    elif kind == "inventory_value":
        assert ev["Valor del inventario" if es else "Inventory value"] == _money(ctx.inventory.summary()["total_value"])
    elif kind == "capacity":
        item = next(i for i in ctx.catalog.list_items() if i["name"] == arg)
        assert ev[arg] == str(item["producible_units"])
        assert f"{item['producible_units']} {arg}" in answer["answer"]
    elif kind == "runout_first":
        # Independiente del asistente: consumo de los últimos 30 días / 30.
        start, _ = _period_bounds(ctx, "30d")
        consumed: dict[str, Decimal] = {}
        for m in ctx.inventory.movements(limit=100_000):
            if m["movement_type"] == "SALE_CONSUMPTION" and str(m["occurred_at"]) >= start:
                consumed[m["inventory_item_id"]] = consumed.get(m["inventory_item_id"], D(0)) - D(m["quantity_delta"])
        days = {}
        for item in ctx.inventory.list_items():
            on_hand, daily = D(item["quantity_on_hand"]), consumed.get(item["inventory_item_id"], D(0)) / 30
            if on_hand <= 0:
                days[item["name"]] = D(0)
            elif daily > 0:
                days[item["name"]] = on_hand / daily
        assert answer["evidence"][0]["label"] == min(days, key=days.get)
    elif kind == "top_product":
        summary = ctx.sales.sales_summary(*_period_bounds(ctx, arg))
        best = max(summary["by_item"], key=lambda i: D(i["gross_profit"]))
        assert answer["evidence"][0]["label"] == best["name"]
        assert answer["evidence"][0]["value"] == _money(best["gross_profit"])
    elif kind == "merchant_spend":
        spending = ctx.purchases.spending(*_period_bounds(ctx, answer["period"]))
        amount = next(m["amount"] for m in spending["by_merchant"] if m["merchant"] == arg)
        assert ev[arg] == _money(amount)
    else:  # pragma: no cover - un caso con una comprobación que no existe
        raise AssertionError(f"engine desconocido: {case['engine']}")


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_question(businesses, case):
    ctx = _ctx(businesses, case["business"])
    answer = ctx.assistant.ask(case["question"])
    labels = [e["label"] for e in answer["evidence"]]

    assert answer["intent"] == case["intent"], answer["answer"]
    assert answer["language"] == case["language"]
    if "period" in case:
        assert answer["period"] == case["period"]
    assert answer["answer"].strip()
    assert answer["llm_used"] is False
    for label in case.get("evidence_labels", []):
        assert label in labels, f"falta la evidencia {label!r}; hay {labels}"
    if "first_evidence_label" in case:
        assert labels and labels[0] == case["first_evidence_label"], labels
    for text in case.get("must_include", []):
        assert text in answer["answer"], f"la respuesta no menciona {text!r}"
    for text in case.get("must_not_include", []):
        assert text not in answer["answer"], f"la respuesta dice {text!r}"
    if "engine" in case:
        _check_engine(ctx, case, answer)


def test_questions_never_touch_the_database_schema(businesses):
    """La pregunta con SQL se trata como texto: nada se ejecuta ni se borra."""
    db = businesses["panaderia"]
    before = db.scalar("SELECT COUNT(*) FROM sales_orders WHERE business_id = 'biz_panaderia'")
    _ctx(businesses, "panaderia").assistant.ask("ventas'; DROP TABLE sales_orders; --")
    assert before > 0
    assert db.scalar("SELECT COUNT(*) FROM sales_orders WHERE business_id = 'biz_panaderia'") == before


def test_golden_suite_covers_every_intent_both_languages_and_both_demos():
    """Si alguien agrega una herramienta y no le escribe preguntas doradas, truena aquí."""
    assert 30 <= len(CASES) <= 50
    assert len({c["id"] for c in CASES}) == len(CASES), "ids repetidos"
    assert {c["business"] for c in CASES} == {"panaderia", "estetica"}
    assert {c["language"] for c in CASES} == {"es", "en"}
    intents = {intent for intent, _ in INTENT_PATTERNS} | {"unknown"}
    assert intents <= {c["intent"] for c in CASES}, f"intenciones sin caso: {intents - {c['intent'] for c in CASES}}"


# --- 3: guardia anti-alucinación ---------------------------------------------

_THOUSANDS = re.compile(r"\$(\d{4,})(\.\d{2})")
_DIGITS = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _figures(text: str) -> set[Decimal]:
    """Extractor propio (no el del asistente): así el test no depende de la
    misma función que está vigilando."""
    return {Decimal(t.rstrip(",").replace(",", "")).normalize() for t in _DIGITS.findall(text)}

INJECTIONS = {
    "monto_inventado": " Además ganaste $98,765.43 extra.",
    "monto_sin_centavos": " Te sobran $98,765 para invertir.",
    "porcentaje_inventado": " Tu margen real es 97.13%.",
    "cantidad_inventada": " Te quedan 8,642 piezas en bodega.",
    "magnitud_en_palabras": " Vas a ganar un millón este año.",
    "magnitude_word_en": " You will make a million dollars this year.",
}


def _faithful(base: str) -> str:
    """Una reescritura legítima: mismo contenido, montos con separador de miles."""
    return "En pocas palabras: " + _THOUSANDS.sub(lambda m: f"${int(m.group(1)):,}{m.group(2)}", base)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_guard_accepts_faithful_rewrites_and_blocks_invented_figures(businesses, case):
    plain = _ctx(businesses, case["business"]).assistant.ask(case["question"])
    base, facts = plain["answer"], " ".join(f"{e['label']} {e['value']} {e.get('detail', '')}" for e in plain["evidence"])

    # Reescritura fiel: se acepta (si la herramienta permite redactar con LLM).
    faithful_llm = _ScriptedLLM(_faithful)
    faithful = _ctx(businesses, case["business"], faithful_llm).assistant.ask(case["question"])
    if faithful_llm.calls:
        assert faithful["llm_used"] is True, "la guardia rechazó una reescritura fiel"
        assert faithful["answer"] == _faithful(base)
    else:
        assert faithful["answer"] == base

    # Cifras inventadas: siempre se rechazan y se responde con la plantilla.
    for name, injection in INJECTIONS.items():
        injected = _figures(injection) - _figures(facts + " " + base)
        assert injected or "mill" in injection, f"{name}: la inyección ya estaba en los hechos"
        tricky = _ctx(businesses, case["business"], _ScriptedLLM(lambda b, extra=injection: b + extra)).assistant.ask(case["question"])
        assert tricky["llm_used"] is False, f"{name} pasó la guardia"
        assert tricky["answer"] == base
        assert injection.strip() not in tricky["answer"]
