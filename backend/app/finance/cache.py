"""
Caché en memoria con TTL para lecturas que casi nunca cambian y que se piden
en CADA request: el catálogo de cuentas del negocio, el perfil del onboarding
y el usuario del token. En Snowflake cada una cuesta ~0.4 s de ida y vuelta.

Las llaves incluyen la identidad del store/base (id()) para que dos bases
distintas en el mismo proceso (tests) nunca compartan entradas. Toda
escritura que afecte una entrada la invalida explícitamente.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

_lock = threading.Lock()
_entries: dict[tuple, tuple[float, Any]] = {}

DEFAULT_TTL = 120.0


def get(key: tuple, loader: Callable[[], Any], ttl: float = DEFAULT_TTL) -> Any:
    """Regresa el valor cacheado o lo carga. `None` nunca se cachea (un
    usuario/perfil inexistente puede aparecer en el siguiente request)."""
    now = time.monotonic()
    with _lock:
        hit = _entries.get(key)
        if hit and hit[0] > now:
            return hit[1]
    value = loader()
    if value is not None:
        with _lock:
            _entries[key] = (now + ttl, value)
    return value


def invalidate(key: tuple) -> None:
    with _lock:
        _entries.pop(key, None)


def invalidate_prefix(prefix: tuple) -> None:
    with _lock:
        for k in [k for k in _entries if k[: len(prefix)] == prefix]:
            _entries.pop(k, None)


def clear() -> None:
    with _lock:
        _entries.clear()
