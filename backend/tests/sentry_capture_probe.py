"""
Ayudante de tests/test_error_visibility.py: activa Sentry con un transporte en
memoria (nada sale a internet), provoca errores con datos sensibles y escribe en
stdout, como JSON, lo que Sentry habría enviado.

Corre en un subproceso a propósito: sentry_sdk.init() parchea FastAPI/Starlette
de forma global y no debe contaminar al resto de la suite.
"""

import json
import logging
import os
import sys

os.environ.setdefault("USE_SNOWFLAKE", "false")

import sentry_sdk
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sentry_sdk.transport import Transport

from app import observability
from app.config import Settings

events: list[dict] = []


class MemoryTransport(Transport):
    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.headers.get("type") == "event":
                events.append(item.payload.json)


def main() -> None:
    real_init = sentry_sdk.init
    sentry_sdk.init = lambda **kw: real_init(transport=MemoryTransport, **kw)
    settings = Settings(jwt_secret="x" * 40, sentry_dsn="https://public@o0.ingest.sentry.io/0", _env_file=None)
    enabled = observability.init_error_tracking(settings)

    app = FastAPI()
    app.add_exception_handler(Exception, observability.unhandled_exception_handler)

    @app.post("/pay/{token}")
    async def boom(token: str):
        # Un error típico de httpx: su mensaje trae la URL con ?key=.
        logging.getLogger("httpx").warning("GET http://api.nessieisreal.com/customers?key=%s", os.environ["PROBE_KEY"])
        raise RuntimeError(f"Client error for url 'http://api.nessieisreal.com/customers?key={os.environ['PROBE_KEY']}'")

    client = TestClient(app, raise_server_exceptions=False)
    responses = []
    for _ in range(2):
        r = client.post(
            f"/pay/{os.environ['PROBE_TOKEN']}?key={os.environ['PROBE_KEY']}",
            json={"password": os.environ["PROBE_PASSWORD"], "week_description_audio_base64": os.environ["PROBE_AUDIO"]},
            headers={"Authorization": f"Bearer {os.environ['PROBE_JWT']}", "Cookie": "sesion=1"},
        )
        responses.append({"status": r.status_code, "body": r.json()})
    sentry_sdk.flush()
    json.dump({"enabled": enabled, "responses": responses, "events": events}, sys.stdout)


if __name__ == "__main__":
    main()
