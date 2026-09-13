"""
Hashing de contraseñas, política de contraseñas y tokens JWT.

Regla de oro de este archivo: la contraseña en claro nunca se guarda, nunca se
loguea y nunca se regresa en una respuesta. Solo entra a hash_password() y a
verify_password(); de ahí no sale.
"""

import base64
import hashlib
import time

import bcrypt
import jwt

from app.config import get_settings

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

# "Largo + mayúscula + minúscula + dígito" NO basta: es exactamente la forma que
# ya tienen las contraseñas más usadas del mundo (Password123, Qwerty12345...).
# Como no hay límite de intentos en /auth/login, la política es el único control
# contra el adivinado en línea, así que se bloquean las bases más comunes.
#
# Se compara el "núcleo" alfabético (quitando dígitos y símbolos): así Password1,
# Password123 y P@ssword2026 caen todas con una sola entrada de la lista.
_COMMON_PASSWORD_BASES = frozenset({
    "password", "passwd", "pass", "contrasena", "contraseña", "clave", "secreta",
    "qwerty", "qwertyuiop", "asdf", "asdfgh", "zxcvbn", "abc", "abcd", "abcdef",
    "admin", "administrador", "root", "usuario", "user", "guest", "invitado",
    "iloveyou", "teamo", "welcome", "bienvenido", "hola", "hello", "letmein",
    "monkey", "dragon", "football", "futbol", "baseball", "princess", "princesa",
    "sunshine", "master", "shadow", "superman", "batman", "trustno", "login",
    "capitalone", "capital", "hackmty", "banco", "negocio", "mexico", "monterrey",
})


def _password_core(password: str) -> str:
    """Solo las letras, en minúsculas. 'P@ssw0rd123' -> 'pssword'."""
    return "".join(c for c in password.lower() if c.isalpha())


def _prehash(password: str) -> bytes:
    """bcrypt ignora todo lo que pase de 72 bytes (y bcrypt 4.x truena si te
    pasas). La política permite hasta 128 caracteres, que en UTF-8 pueden ser
    muchos más bytes, así que primero se comprime con SHA-256 y se pasa a
    base64: 44 caracteres fijos, siempre dentro del límite, y sin perder
    entropía de la cola de la contraseña."""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    # Un hash corrupto o de otro formato no debe tirar la request: es un 401,
    # no un 500.
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# Hash de relleno, calculado una sola vez al importar el módulo.
_DUMMY_HASH = bcrypt.hashpw(_prehash("usuario-inexistente"), bcrypt.gensalt()).decode("utf-8")


def dummy_verify() -> None:
    """Se llama cuando el usuario no existe, para que el login tarde más o menos
    lo mismo que con un usuario real y no se puedan enumerar cuentas midiendo el
    tiempo de respuesta."""
    verify_password("password-que-no-existe", _DUMMY_HASH)


def validate_password(password: str, username: str = "") -> list[str]:
    """Regresa la lista de códigos de problema; vacía = contraseña aceptable.

    Los códigos son parte del contrato con el frontend, no cambiarlos sin avisar.
    """
    problems: list[str] = []

    if len(password) < MIN_PASSWORD_LENGTH:
        problems.append("too_short")
    if len(password) > MAX_PASSWORD_LENGTH:
        problems.append("too_long")
    if not any(c.islower() for c in password):
        problems.append("missing_lowercase")
    if not any(c.isupper() for c in password):
        problems.append("missing_uppercase")
    if not any(c.isdigit() for c in password):
        problems.append("missing_digit")
    if username and username.strip().lower() in password.lower():
        problems.append("contains_username")

    if _password_core(password) in _COMMON_PASSWORD_BASES:
        problems.append("too_common")

    return problems


def create_access_token(subject: str) -> tuple[str, int]:
    """Regresa (token, expires_in_segundos). `sub` = user_id, no el username:
    el username podría cambiar y el token seguiría apuntando al usuario correcto.
    """
    settings = get_settings()
    expires_in = settings.jwt_expire_minutes * 60
    issued_at = int(time.time())
    token = jwt.encode(
        {"sub": subject, "iat": issued_at, "exp": issued_at + expires_in},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def decode_access_token(token: str) -> dict | None:
    """None si el token es inválido, expirado o viene firmado con otro secreto.
    El router traduce ese None a 401 sin detallar el motivo: decirle al cliente
    "expirado" vs "firma mala" solo le sirve a quien está atacando."""
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
    except jwt.InvalidTokenError:
        return None
