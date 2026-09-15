"""
Endurecimiento HTTP de la API (Fase 7, checklist OWASP API Security Top 10).

  - BodySizeLimitMiddleware: tope global al tamaño del cuerpo (API4, consumo de
    recursos). Sin él, cualquiera podía mandar cientos de MB a /auth/login o a
    /pay/{token} y el proceso los leía completos en memoria.
  - SecurityHeadersMiddleware: headers que ninguna respuesta de la API debería
    omitir (API8, configuración). La API sólo sirve JSON y /docs.
  - require_legacy_nessie_routes: las rutas /accounts/... de la plantilla
    original (passthrough a Nessie) son públicas, sin token, y el frontend no
    las usa. En producción responden 404 (API9, inventario de endpoints).

Middlewares ASGI puros: no dependen de FastAPI y funcionan también para las
respuestas que genera Starlette antes de llegar a una ruta.
"""

from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.config import get_settings

_PAYLOAD_TOO_LARGE = json.dumps({"detail": "payload_too_large"}).encode()
_METHODS_WITH_BODY = {"POST", "PUT", "PATCH", "DELETE"}

SECURITY_HEADERS = {
    b"x-content-type-options": b"nosniff",
    b"x-frame-options": b"DENY",
    b"referrer-policy": b"no-referrer",
    # Respuestas con datos financieros de un negocio: que ningún proxy ni el
    # navegador las guarde en disco.
    b"cache-control": b"no-store",
}


async def _reject_too_large(send) -> None:
    await send({
        "type": "http.response.start",
        "status": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(_PAYLOAD_TOO_LARGE)).encode())],
    })
    await send({"type": "http.response.body", "body": _PAYLOAD_TOO_LARGE})


class BodySizeLimitMiddleware:
    """413 si el cuerpo pasa de `max_bytes`.

    Con Content-Length se decide sin leer nada. Sin Content-Length (envío por
    partes) se lee hasta el tope y se reenvía a la app; si lo pasa, 413 antes de
    que la ruta vea un solo byte.
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") not in _METHODS_WITH_BODY:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                too_large = int(declared) > self.max_bytes
            except ValueError:
                too_large = True
            if too_large:
                await _reject_too_large(send)
                return
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":  # el cliente se fue
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                await _reject_too_large(send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                present = {name.lower() for name, _ in message.get("headers", [])}
                extra = [(name, value) for name, value in SECURITY_HEADERS.items() if name not in present]
                message = {**message, "headers": [*message.get("headers", []), *extra]}
            await send(message)

        await self.app(scope, receive, send_with_headers)


def require_legacy_nessie_routes() -> None:
    """Dependencia de las rutas /accounts/...: 404 si están apagadas."""
    if not get_settings().legacy_nessie_routes_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
