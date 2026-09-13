"""
Capa de lenguaje del asistente: OPCIONAL y nunca autoritativa.

El LLM recibe hechos ya calculados por el motor y sólo los redacta. Si no hay
proveedor disponible (sin API key, sin Snowflake), el asistente responde con
plantillas deterministas y sigue funcionando igual.

Proveedores:
  AnthropicLLM   ANTHROPIC_API_KEY (SDK oficial `anthropic`, modelo claude-opus-5)
  CortexLLM      SNOWFLAKE.CORTEX.COMPLETE, sin credenciales extra si Snowflake ya está activo
  NoLLM          plantillas
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.config import Settings
from app.db.base import Database

log = logging.getLogger(__name__)


class LLMProvider(ABC):
    name: str = "none"

    @abstractmethod
    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str | None:
        """Texto, o None si el proveedor falló (el llamador cae a plantillas)."""

    @property
    def available(self) -> bool:
        return True


class NoLLM(LLMProvider):
    name = "none"

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str | None:
        return None

    @property
    def available(self) -> bool:
        return False


class AnthropicLLM(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic  # import perezoso: la dependencia es opcional

            self._client = anthropic.Anthropic(api_key=self._api_key, timeout=30.0, max_retries=1)
        return self._client

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str | None:
        try:
            client = self._get_client()
            response = client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
                output_config={"effort": "low"},
            )
            if response.stop_reason == "refusal":
                return None
            return "".join(block.text for block in response.content if block.type == "text").strip() or None
        except Exception as exc:  # noqa: BLE001 - cualquier fallo del proveedor => plantillas
            log.warning("Anthropic no disponible: %s", exc)
            return None


class CortexLLM(LLMProvider):
    """Snowflake Cortex: el modelo corre dentro de Snowflake, junto a los
    datos. Se usa la misma conexión del motor financiero."""

    name = "cortex"

    def __init__(self, db: Database, model: str):
        self._db = db
        self._model = model

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str | None:
        try:
            full = f"{system}\n\n---\n\n{prompt}"
            row = self._db.fetchone("SELECT SNOWFLAKE.CORTEX.COMPLETE(:model, :prompt)", {"model": self._model, "prompt": full})
            text = (row[0] if row else "") or ""
            return text.strip() or None
        except Exception as exc:  # noqa: BLE001 - igual: sin Cortex, plantillas
            log.warning("Cortex no disponible: %s", exc)
            return None


def build_llm(settings: Settings, db: Database) -> LLMProvider:
    choice = (settings.llm_provider or "auto").lower()
    if choice in {"auto", "anthropic"} and settings.anthropic_api_key:
        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
    if choice in {"auto", "cortex"} and db.dialect == "snowflake":
        return CortexLLM(db, settings.cortex_model)
    return NoLLM()
