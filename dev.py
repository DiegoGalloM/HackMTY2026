#!/usr/bin/env python3
"""
Levanta backend y frontend en UNA sola terminal.

    python dev.py

Cada linea de salida sale prefijada con [api] o [web] para saber quien la
escribio. Ctrl+C una vez mata los dos (incluyendo los procesos hijos de node,
que en Windows se quedan vivos y agarrados al puerto si solo matas a npm).

Si uno de los dos se cae, el otro se baja tambien — asi no te quedas con medio
stack corriendo sin darte cuenta.

Detalle de la doc: docs/DEV.md
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"

# Vite imprime flechas y cajas Unicode. Si la consola de Windows quedo en cp1252
# (pasa sobre todo al redirigir a un archivo), escribir esos caracteres revienta
# el hilo que va reimprimiendo la salida y te quedas ciego con el server vivo.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover
        pass

# [api] azul, [web] magenta. Se apagan solos si la salida no es una terminal
# o si NO_COLOR esta puesto (https://no-color.org/).
_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
COLORS = {"api": "\033[36m", "web": "\033[35m", "dev": "\033[32m", "err": "\033[31m"}
RESET = "\033[0m"

_print_lock = threading.Lock()


def log(tag: str, line: str) -> None:
    prefix = f"[{tag}]"
    if _USE_COLOR:
        prefix = f"{COLORS.get(tag, '')}{prefix}{RESET}"
    with _print_lock:
        sys.stdout.write(f"{prefix} {line}\n")
        sys.stdout.flush()


def die(message: str, hint: str | None = None) -> None:
    log("err" if _USE_COLOR else "dev", message)
    if hint:
        log("dev", hint)
    sys.exit(1)


# --------------------------------------------------------------- resolvers --

def can_import_uvicorn(python: Path) -> bool:
    return subprocess.run(
        [str(python), "-c", "import uvicorn, fastapi"],
        capture_output=True,
    ).returncode == 0


def find_backend_python() -> Path:
    """
    El primer interprete que de verdad pueda importar uvicorn.

    No basta con que exista python.exe: un venv se puede quedar apuntando a un
    interprete que ya no ve su propio site-packages (pasa si reinstalas Python
    o si corres `python -m venv` encima con otro interprete — el pyvenv.cfg se
    reescribe y las dependencias viejas quedan invisibles). Por eso probamos
    cada candidato en vez de confiar en que el archivo este ahi.
    """
    subdir = "Scripts" if IS_WINDOWS else "bin"
    exe = "python.exe" if IS_WINDOWS else "python"
    candidates = [venv / subdir / exe for venv in (BACKEND / ".venv", ROOT / ".venv")]

    existing = [c for c in candidates if c.exists()]
    for candidate in existing:
        if can_import_uvicorn(candidate):
            return candidate

    if not existing:
        die(
            "No encontre ningun venv para el backend.",
            "Crealo con:  py -3.12 -m venv backend\\.venv"
            if IS_WINDOWS
            else "Crealo con:  python3.12 -m venv backend/.venv",
        )

    # Hay venv(s) pero ninguno sirve. Decir cual y con que version, porque el
    # caso tipico es una mezcla de versiones y el mensaje de pip no lo aclara.
    log("dev", "Encontre venv(s) pero ninguno puede importar uvicorn:")
    for candidate in existing:
        version = subprocess.run(
            [str(candidate), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
            capture_output=True,
            text=True,
        ).stdout.strip() or "?"
        log("dev", f"  - {candidate}  (Python {version})")
    die(
        "El venv no tiene las dependencias, o quedo apuntando a otro Python.",
        "Rehazlo:  rmdir /s /q backend\\.venv && py -3.12 -m venv backend\\.venv "
        "&& backend\\.venv\\Scripts\\pip install -r backend\\requirements.txt"
        if IS_WINDOWS
        else "Rehazlo:  rm -rf backend/.venv && python3.12 -m venv backend/.venv "
        "&& backend/.venv/bin/pip install -r backend/requirements.txt",
    )
    raise AssertionError("unreachable")


def find_npm() -> str:
    # En Windows npm es un .cmd; Popen sin shell no lo encuentra por nombre pelon.
    return "npm.cmd" if IS_WINDOWS else "npm"


def check_frontend_deps() -> None:
    if not (FRONTEND / "node_modules").is_dir():
        die(
            "frontend/node_modules no existe.",
            "Instala con:  cd frontend && npm install",
        )


# ----------------------------------------------------------------- procesos --

def spawn(tag: str, cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    """
    Arranca un proceso con su salida redirigida a nuestro stdout.

    El grupo de procesos aparte es a proposito: asi el Ctrl+C de la terminal NO
    le llega directo a los hijos, llega aqui, y nosotros decidimos como bajarlos
    (primero bonito, luego a la fuerza). Sin esto cada quien se muere por su lado
    y el arbol de node queda huerfano.
    """
    kwargs: dict = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    log("dev", f"{tag}: {' '.join(cmd)}  (cwd={cwd.relative_to(ROOT)})")
    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **kwargs,
    )


def pump(tag: str, proc: subprocess.Popen) -> None:
    """Lee la salida del proceso linea por linea y la reimprime con prefijo."""
    assert proc.stdout is not None
    for line in proc.stdout:
        log(tag, line.rstrip("\n"))


def stop(tag: str, proc: subprocess.Popen) -> None:
    """Baja un proceso y TODO su arbol de hijos."""
    if proc.poll() is not None:
        return

    log("dev", f"bajando {tag}...")
    try:
        if IS_WINDOWS:
            # CTRL_BREAK_EVENT es lo unico que cruza a un grupo aparte en Windows.
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (OSError, ValueError):
        pass

    try:
        proc.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass

    # No se murio por las buenas. En Windows taskkill /T es la unica forma
    # confiable de llevarse a los hijos de node junto con npm.
    log("dev", f"{tag} no cerro solo, matando el arbol")
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
        )
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ValueError):
            proc.kill()


# --------------------------------------------------------------------- main --

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Levanta backend y frontend juntos en una sola terminal.",
    )
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=5173)
    parser.add_argument("--host", default="127.0.0.1", help="host de uvicorn")
    parser.add_argument("--no-reload", action="store_true", help="apaga --reload de uvicorn")
    parser.add_argument("--only", choices=["api", "web"], help="corre solo uno de los dos")
    args = parser.parse_args()

    want_api = args.only != "web"
    want_web = args.only != "api"

    procs: dict[str, subprocess.Popen] = {}

    if want_api:
        python = find_backend_python()
        cmd = [
            str(python), "-m", "uvicorn", "app.main:app",
            "--host", args.host,
            "--port", str(args.api_port),
        ]
        if not args.no_reload:
            cmd.append("--reload")
        # uvicorn se corre DESDE backend/ a proposito: config.py lee env_file=".env"
        # relativo al cwd, y desde la raiz no encuentra las credenciales — se va
        # a memoria en silencio. Es el error mas repetido del RUNBOOK.
        procs["api"] = spawn("api", cmd, BACKEND, os.environ.copy())

    if want_web:
        check_frontend_deps()
        env = os.environ.copy()
        if want_api:
            # Que el front le pegue al backend que acabamos de levantar, aunque
            # alguien tenga otro puerto en .env.local.
            env["VITE_API_URL"] = f"http://{args.host}:{args.api_port}"
        cmd = [find_npm(), "run", "dev", "--", "--port", str(args.web_port), "--strictPort"]
        procs["web"] = spawn("web", cmd, FRONTEND, env)

    for tag, proc in procs.items():
        threading.Thread(target=pump, args=(tag, proc), daemon=True).start()

    log("dev", "listo — Ctrl+C baja los dos")
    if want_api:
        log("dev", f"api  http://{args.host}:{args.api_port}/docs")
    if want_web:
        log("dev", f"web  http://localhost:{args.web_port}")

    exit_code = 0
    try:
        while True:
            for tag, proc in procs.items():
                code = proc.poll()
                if code is not None:
                    log("dev", f"{tag} termino con codigo {code} — bajando el resto")
                    exit_code = code or 1
                    raise SystemExit
            time.sleep(0.3)
    except KeyboardInterrupt:
        log("dev", "Ctrl+C recibido")
    except SystemExit:
        pass
    finally:
        for tag, proc in procs.items():
            stop(tag, proc)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
