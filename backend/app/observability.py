"""
Visibilidad básica de errores del backend.

Dos capas, pensadas para un demo público y no para una torre de observabilidad:

  1. Siempre: un error no controlado responde 500 con un `error_id` (nunca el
     stack trace) y queda en el log con ese mismo id. Quien vea el error en
     pantalla puede pasar el id y se encuentra la traza en los logs de Render.
  2. Opcional: con SENTRY_DSN (capa gratuita de Sentry) el error además se
     manda a Sentry, que avisa por correo. Sin DSN no se importa ni se envía nada.

Lo que NUNCA sale hacia Sentry (ver `scrub_event`): cuerpos de las peticiones
(contraseñas, audio de la encuesta), cookies, headers de autenticación, query
strings (la key de Nessie viaja en ?key=) ni el token del QR en /pay/{token}.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import Settings

log = logging.getLogger("uvicorn.error")

# /pay/<token>: el token es lo único que protege una orden por cobrar.
_PAY_TOKEN_RE = re.compile(r"(/pay/)[^/?#\s\"']+")
# Query strings dentro de URLs: la key de Nessie viaja en ?key= y aparece en los
# mensajes de error de httpx y en los breadcrumbs de logging.
_URL_QUERY_RE = re.compile(r"(https?://[^\s?#\"']+)\?[^\s#\"']*")
_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-forwarded-for", "x-real-ip"}

_sentry_enabled = False


def scrub_text(value: str) -> str:
    value = _URL_QUERY_RE.sub(r"\1?[filtrado]", value)
    return _PAY_TOKEN_RE.sub(r"\1[token]", value)


def scrub_event(event: dict[str, Any], _hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """before_send de Sentry: quita todo lo que pueda identificar a alguien o
    abrir una orden, antes de que el evento salga del proceso."""
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("data", "cookies", "query_string", "env"):
            request.pop(key, None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {k: v for k, v in headers.items() if k.lower() not in _SENSITIVE_HEADERS}
        if isinstance(request.get("url"), str):
            request["url"] = scrub_text(request["url"])
    if isinstance(event.get("transaction"), str):
        event["transaction"] = scrub_text(event["transaction"])
    event.pop("user", None)
    # Variables locales de los frames: ahí viaja el request completo (token,
    # headers, query string). Ya van apagadas en init; esto es por si alguien
    # las vuelve a encender.
    for exception in (event.get("exception") or {}).get("values") or []:
        if isinstance(exception.get("value"), str):
            exception["value"] = scrub_text(exception["value"])
        for frame in (exception.get("stacktrace") or {}).get("frames") or []:
            frame.pop("vars", None)
    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        for key in ("message", "formatted"):
            if isinstance(logentry.get(key), str):
                logentry[key] = scrub_text(logentry[key])
    breadcrumbs = event.get("breadcrumbs")
    values = breadcrumbs.get("values") if isinstance(breadcrumbs, dict) else breadcrumbs
    for crumb in values or []:
        if isinstance(crumb, dict):
            if isinstance(crumb.get("message"), str):
                crumb["message"] = scrub_text(crumb["message"])
            data = crumb.get("data")
            if isinstance(data, dict) and isinstance(data.get("url"), str):
                data["url"] = scrub_text(data["url"].split("?", 1)[0])
    return event


def init_error_tracking(settings: Settings) -> bool:
    """Activa Sentry si hay DSN. Regresa True si quedó activo."""
    global _sentry_enabled
    if not settings.sentry_dsn:
        _sentry_enabled = False
        return False
    import sentry_sdk  # sólo se importa si se va a usar

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.release or settings.render_git_commit or None,
        send_default_pii=False,  # sin IPs, usuarios ni cuerpos
        max_request_body_size="never",
        # Sin esto Sentry adjunta las variables locales de cada frame, y entre
        # ellas va el request completo: token del QR, Authorization, ?key=.
        include_local_variables=False,
        traces_sample_rate=0.0,  # sólo errores: la capa gratuita alcanza
        before_send=scrub_event,
    )
    _sentry_enabled = True
    log.info("Tracking de errores activo (Sentry, entorno %s)", settings.environment)
    return True


def error_tracking_mode() -> str:
    return "sentry" if _sentry_enabled else "logs"


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """500 sin detalles internos y con un id para encontrar la traza en el log.

    Sentry (si está activo) ya captura la excepción por su integración con
    FastAPI; aquí sólo se decide qué ve el cliente y qué queda en el log.
    """
    # Con Sentry activo, el id que ve el cliente ES el event_id de Sentry: se
    # busca tal cual en su panel. La integración con FastAPI puede haber
    # capturado ya la excepción (last_event_id); si no, se captura aquí.
    event_id = None
    if _sentry_enabled:
        import sentry_sdk

        event_id = sentry_sdk.last_event_id() or sentry_sdk.capture_exception(exc)
    error_id = (event_id or uuid.uuid4().hex)[:12]
    log.error(
        "error_id=%s %s %s: %s",
        error_id,
        request.method,
        scrub_text(request.url.path),
        type(exc).__name__,
        exc_info=exc,
    )
    return JSONResponse(status_code=500, content={"detail": "internal_error", "error_id": error_id})
