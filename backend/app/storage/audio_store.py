"""
Audio de la encuesta de onboarding, con caducidad.

La grabación de "narra tu semana" es la voz de quien prueba el demo. En vez de
guardarla como base64 dentro de business_profiles para siempre, vive en la
tabla `onboarding_audio` (migración 005) con un `expires_at`, y lo vencido se
borra. Para un demo es la versión simple de "un bucket con política de
retención": mismo efecto (el audio no sobrevive a su plazo) sin otro servicio.

Usa el `Database` del núcleo (sqlite en memoria o Snowflake), así que funciona
igual en los dos modos y en los tests.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db.base import Database

# Purgar en cada request costaría un DELETE por petición (≈0.3 s en
# Snowflake). Con esto se purga a lo mucho una vez por intervalo por proceso;
# a un audio vencido le quedan, como mucho, estos segundos de vida extra.
PURGE_INTERVAL_SECONDS = 600

_purge_lock = threading.Lock()
_last_purge: dict[int, float] = {}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


class OnboardingAudioStore:
    def __init__(self, db: Database, retention_days: int):
        self.db = db
        self.retention_days = retention_days

    def save(self, owner_id: str, audio_base64: str | None, audio_mime: str | None) -> bool:
        """Reemplaza el audio del dueño. Regresa True si quedó guardado.

        Sin audio, o con retención 0, sólo borra lo que hubiera: volver a hacer
        la encuesta escribiendo en vez de narrando no debe dejar la voz vieja.
        """
        with self.db.transaction():
            self.db.execute("DELETE FROM onboarding_audio WHERE owner_id = :owner_id", {"owner_id": owner_id})
            if not audio_base64 or self.retention_days <= 0:
                return False
            now = _now()
            self.db.execute(
                "INSERT INTO onboarding_audio (owner_id, audio_base64, audio_mime, created_at, expires_at) "
                "VALUES (:owner_id, :audio_base64, :audio_mime, :created_at, :expires_at)",
                {
                    "owner_id": owner_id,
                    "audio_base64": audio_base64,
                    "audio_mime": audio_mime,
                    "created_at": now.isoformat(),
                    "expires_at": (now + timedelta(days=self.retention_days)).isoformat(),
                },
            )
        return True

    def get(self, owner_id: str) -> dict[str, Any] | None:
        """El audio vigente del dueño, o None si no hay o ya venció."""
        return self.db.row(
            "SELECT owner_id, audio_base64, audio_mime, created_at, expires_at FROM onboarding_audio "
            "WHERE owner_id = :owner_id AND expires_at > :now",
            {"owner_id": owner_id, "now": _now().isoformat()},
        )

    def purge_expired(self) -> None:
        self.db.execute("DELETE FROM onboarding_audio WHERE expires_at <= :now", {"now": _now().isoformat()})

    def maybe_purge_expired(self) -> bool:
        """purge_expired() si ya pasó PURGE_INTERVAL_SECONDS desde la última
        purga contra esta base. Regresa True si purgó."""
        key = id(self.db)
        with _purge_lock:
            last = _last_purge.get(key)
            if last is not None and time.monotonic() - last < PURGE_INTERVAL_SECONDS:
                return False
            _last_purge[key] = time.monotonic()
        self.purge_expired()
        return True
