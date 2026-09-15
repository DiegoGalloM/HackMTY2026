"""
Límite de peticiones por IP para las rutas públicas.

El demo se va a compartir en LinkedIn: un enlace viral no debe poder usarse
para martillar lo que no pide token. Aquí se limita:

  - /pay/{token}                     (el QR: leer y pagar la orden)
  - /business-profile/stats/{cat}    (agregados públicos)
  - /demo/session                    (cada llamada puede sembrar un negocio)
  - /auth/register y /auth/login     (sin esto, el login admite adivinado en línea)

Ventana deslizante en memoria, por proceso. Es a propósito lo más simple que
cierra el hueco para un demo con una sola instancia: con varios workers cada
uno lleva su cuenta (el límite efectivo se multiplica) y para eso haría falta
un almacén compartido (Redis) o el rate limiting del proxy.

Uso: `dependencies=[Depends(rate_limit("pay", 60))]` en la ruta.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings

WINDOW_SECONDS = 60

# Peticiones por minuto por IP. Generosas para una persona usando el demo,
# cortas para un script. Ojo con las redes compartidas: en una demo presencial
# toda la sala sale a internet con la misma IP, por eso registro, login y demo
# no bajan de 20 (siguen frenando el adivinado de contraseñas en línea) y
# registro y login llevan cuentas separadas: los intentos fallidos de login
# no bloquean a quien se está registrando.
LIMITS = {
    "pay": 60,
    "stats": 30,
    "demo_session": 20,
    "auth_register": 20,
    "auth_login": 20,
    # /health/ready: un monitor de uptime pega cada minuto; esto frena a quien
    # lo use para martillar Snowflake/Nessie (además tiene caché de 30 s).
    "health": 60,
}


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, bucket: str, key: str, limit: int, window: float = WINDOW_SECONDS) -> float | None:
        """Registra una petición. Regresa None si pasa, o los segundos que
        faltan para que se libere un lugar si ya se llenó la ventana."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[(bucket, key)]
            while hits and now - hits[0] >= window:
                hits.popleft()
            if len(hits) >= limit:
                return max(0.0, window - (now - hits[0]))
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    """La IP del cliente. Detrás de un proxy de confianza (TRUST_PROXY_HEADERS)
    se toma el ÚLTIMO salto de X-Forwarded-For: es el que agregó el proxy con la
    IP que vio conectarse. Los primeros los puede escribir cualquiera, así que
    usarlos permitiría saltarse el límite cambiando el header."""
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if hops:
            return hops[-1]
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, limit: int | None = None):
    """Dependencia de FastAPI que responde 429 al pasarse del límite."""
    per_minute = limit if limit is not None else LIMITS[bucket]

    async def dependency(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        retry_after = limiter.hit(bucket, client_ip(request), per_minute)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limited",
                headers={"Retry-After": str(max(1, int(retry_after + 0.999)))},
            )

    # Etiqueta para el guard de tests/test_demo_hardening.py, que revisa que
    # ninguna ruta pública quede sin límite.
    dependency.rate_limit_bucket = bucket  # type: ignore[attr-defined]
    return dependency
