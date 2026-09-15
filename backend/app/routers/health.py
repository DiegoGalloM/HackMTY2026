"""
Salud del backend, en dos niveles:

  GET /health        ¿el proceso está vivo? Rápido y sin dependencias: es el
                     health check de Render. Si revisara Snowflake, una caída de
                     Snowflake haría que Render reiniciara el servicio en bucle.
  GET /health/ready  ¿funciona de verdad? Revisa la base (sqlite o Snowflake),
                     Nessie y el LLM del asistente. Es el que conviene apuntar a
                     un monitor de uptime gratuito para enterarse de una caída.

/health/ready responde 503 sólo si falla lo indispensable (la base); si falla
algo opcional (Nessie real, el LLM) responde 200 con status "degraded", porque
la app sigue funcionando (transacciones demo, respuestas con plantillas).

En modo mock no hay servicios externos que revisar: Nessie mock y "sin LLM"
se reportan como tales, sin simular llamadas.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Response

from app.config import get_settings
from app.db import get_db
from app.finance.llm import build_llm
from app.nessie import get_nessie_client
from app.nessie.mock_client import MockNessieClient
from app.observability import error_tracking_mode
from app.ratelimit import rate_limit

router = APIRouter(tags=["health"])

CHECK_TIMEOUT_SECONDS = 5.0
# Un monitor externo pega cada minuto; sin caché, cada visita sería una
# consulta a Snowflake y una llamada a Nessie/Anthropic.
CACHE_SECONDS = 30.0
ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"

_cache: dict[str, Any] = {"at": 0.0, "report": None}

# Nunca devolver secretos en un endpoint público: la key de Nessie viaja en ?key=.
_QUERY_RE = re.compile(r"\?[^\s'\"]*")


def _safe_error(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError | asyncio.TimeoutError):
        return f"sin respuesta en {CHECK_TIMEOUT_SECONDS:.0f} s"
    message = _QUERY_RE.sub("", str(exc)).strip()
    return f"{type(exc).__name__}: {message}"[:200] if message else type(exc).__name__


async def _timed(check) -> dict[str, Any]:
    """Corre un check con timeout y le agrega la latencia."""
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - cualquier falla del check se reporta, no truena el endpoint
        result = {"status": "down", "detail": _safe_error(exc)}
    result["latency_ms"] = round((time.perf_counter() - started) * 1000)
    return result


async def check_database() -> dict[str, Any]:
    def ping() -> str:
        db = get_db()
        if db.scalar("SELECT 1") != 1:
            raise RuntimeError("SELECT 1 no regresó 1")
        return db.dialect

    dialect = await asyncio.to_thread(ping)
    settings = get_settings()
    stores = "Snowflake" if settings.use_snowflake and settings.snowflake_account else "memoria"
    return {"status": "ok", "mode": dialect, "detail": f"núcleo financiero en {dialect}; perfiles y usuarios en {stores}"}


async def check_nessie() -> dict[str, Any]:
    client = get_nessie_client()
    if isinstance(client, MockNessieClient):
        return {"status": "ok", "mode": "mock", "detail": "cliente simulado, sin llamadas externas"}
    await client.list_customers()
    return {"status": "ok", "mode": "real", "detail": "api.nessieisreal.com responde"}


async def _anthropic_reachable(api_key: str) -> None:
    # Listar modelos no gasta tokens y confirma que la key es válida.
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_SECONDS) as client:
        response = await client.get(ANTHROPIC_MODELS_URL, headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        response.raise_for_status()


async def check_llm() -> dict[str, Any]:
    settings = get_settings()
    provider = build_llm(settings, await asyncio.to_thread(get_db))
    if provider.name == "none":
        return {"status": "ok", "mode": "none", "detail": "sin LLM: el asistente redacta con plantillas deterministas"}
    if provider.name == "anthropic":
        await _anthropic_reachable(settings.anthropic_api_key)
        return {"status": "ok", "mode": "anthropic", "detail": f"key válida ({settings.anthropic_model})"}
    # Cortex corre dentro de Snowflake: si la base responde, está alcanzable.
    # No se invoca COMPLETE aquí para no gastar créditos en cada revisión.
    return {"status": "ok", "mode": provider.name, "detail": f"vía Snowflake ({settings.cortex_model}); no se invoca en la revisión"}


CRITICAL = {"database"}


async def build_report() -> dict[str, Any]:
    names = ("database", "nessie", "llm")
    results = await asyncio.gather(_timed(check_database), _timed(check_nessie), _timed(check_llm))
    checks = dict(zip(names, results, strict=True))
    failing = {name for name, result in checks.items() if result["status"] != "ok"}
    status = "down" if failing & CRITICAL else "degraded" if failing else "ok"
    return {"status": status, "checks": checks, "error_tracking": error_tracking_mode()}


async def readiness_report() -> dict[str, Any]:
    # Sin candado a propósito: dos revisiones simultáneas a lo mucho construyen
    # el reporte dos veces, y un asyncio.Lock de módulo se ata a un solo event loop.
    if _cache["report"] is not None and time.monotonic() - _cache["at"] < CACHE_SECONDS:
        return _cache["report"]
    report = await build_report()
    _cache.update(at=time.monotonic(), report=report)
    return report


def reset_cache() -> None:
    _cache.update(at=0.0, report=None)


@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "nessie_mode": "mock" if settings.use_mock_nessie or not settings.nessie_api_key else "real",
        "storage": "snowflake" if settings.use_snowflake and settings.snowflake_account else "memory",
        "payment_provider": settings.payment_provider,
        "transaction_provider": settings.transaction_provider,
        "error_tracking": error_tracking_mode(),
    }


@router.get("/health/ready", dependencies=[Depends(rate_limit("health"))])
async def ready(response: Response):
    report = await readiness_report()
    if report["status"] == "down":
        response.status_code = 503
    return report
