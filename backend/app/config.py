"""
Configuración centralizada. Todo lo que cambia entre tu laptop, la de tu
compañero, y el servidor de demo debería vivir aquí — nunca hardcodeado en
el resto del código.
"""

import secrets
import warnings
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Solo HMAC: el proyecto firma y verifica con el mismo secreto. Dejar fuera las
# familias RS/ES evita de raíz la confusión de algoritmos (mandar un token RS
# firmado con la clave pública como si fuera el secreto HMAC).
_ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})
_MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    nessie_api_key: str = ""
    nessie_base_url: str = "http://api.nessieisreal.com"
    use_mock_nessie: bool = True

    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    use_snowflake: bool = False
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = ""
    snowflake_schema: str = ""
    snowflake_role: str = ""

    cors_origins: str = "http://localhost:5173"

    # Núcleo financiero sin Snowflake: sqlite en memoria por default (se
    # reinicia con el proceso, igual que los stores en memoria). Un path lo
    # vuelve persistente entre reinicios: LOCAL_DB_PATH=./data/local.db
    local_db_path: str = ""

    # Proveedor de pagos para el cobro con QR. "demo" confirma el pago sin
    # tocar ningún servicio externo, pero produce el MISMO evento autoritativo
    # que produciría un webhook real.
    payment_provider: str = "demo"

    # Fuente de transacciones de la tarjeta de negocio: "demo" | "nessie".
    transaction_provider: str = "demo"

    # Capa de explicación del asistente: "auto" prueba Anthropic (si hay key),
    # luego Snowflake Cortex (si Snowflake está activo) y si no, plantillas
    # deterministas. También: "anthropic" | "cortex" | "none".
    llm_provider: str = "auto"
    cortex_model: str = "claude-sonnet-4-5"
    anthropic_model: str = "claude-opus-5"

    # URL pública del frontend, para armar el link del QR desde el backend
    # cuando el cliente escanea desde otro dispositivo. Vacío = el frontend usa
    # su propio origen.
    public_app_url: str = ""

    # "production" en el servicio desplegado (render.yaml). Ahí los atajos de
    # desarrollo dejan de valer: sin JWT_SECRET el backend no arranca.
    environment: str = "development"

    # Auth. jwt_secret vacío = se genera uno efímero al arrancar (ver validador),
    # salvo en producción, donde es obligatorio.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # Audio de la encuesta ("narra tu semana"): es la voz de quien prueba el
    # demo, así que no vive en la fila del perfil y se borra solo a los N días
    # (tabla onboarding_audio). 0 = no se guarda nunca.
    onboarding_audio_retention_days: int = 7

    # Límite de peticiones por IP en las rutas públicas (pago por QR, stats,
    # demo, registro y login). Ver app/ratelimit.py.
    rate_limit_enabled: bool = True
    # Detrás del proxy de Render todas las peticiones llegan desde la IP del
    # proxy: con esto se toma la IP real del último salto de X-Forwarded-For.
    # Sólo debe activarse cuando el backend NO es alcanzable sin ese proxy.
    trust_proxy_headers: bool = False

    # Tope global al cuerpo de cualquier petición (413 si se pasa). 3 MB alcanzan
    # para el audio de la encuesta (MAX_AUDIO_BASE64 ≈ 2 MB) más el resto del perfil.
    max_request_body_bytes: int = 3_000_000

    # Rutas /accounts/... de la plantilla original (passthrough a Nessie):
    # públicas, sin token y sin uso en el frontend. Vacío = encendidas en
    # desarrollo y apagadas (404) en producción; true/false lo fuerza.
    enable_legacy_nessie_routes: bool | None = None

    # Tracking de errores (Sentry, capa gratuita). Vacío = apagado: los errores
    # sólo quedan en el log del proceso, con un error_id para buscarlos.
    sentry_dsn: str = ""
    # Versión que se reporta con cada error. Vacío = el commit que Render
    # expone solo en cada deploy (RENDER_GIT_COMMIT).
    release: str = ""
    render_git_commit: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def legacy_nessie_routes_enabled(self) -> bool:
        if self.enable_legacy_nessie_routes is not None:
            return self.enable_legacy_nessie_routes
        return not self.is_production

    @model_validator(mode="after")
    def _ensure_jwt_secret(self):
        # El algoritmo se valida contra una lista blanca: viene del entorno y
        # decode() confía en él. Con un valor raro (o "none") la verificación de
        # firma dejaría de proteger nada.
        if self.jwt_algorithm not in _ALLOWED_JWT_ALGORITHMS:
            raise ValueError(
                f"JWT_ALGORITHM inválido: {self.jwt_algorithm!r}. "
                f"Permitidos: {sorted(_ALLOWED_JWT_ALGORITHMS)}"
            )

        # Un secreto corto se rompe offline en minutos: cualquiera puede pedir
        # un token en /auth/register y atacarlo sin tocar el servidor. Con el
        # secreto, se firma un token para CUALQUIER user_id. 32 caracteres es el
        # mínimo razonable para HS256; el generado abajo trae 64.
        if self.jwt_secret and len(self.jwt_secret) < _MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET es demasiado corto ({len(self.jwt_secret)} caracteres): "
                f"se requieren al menos {_MIN_JWT_SECRET_LENGTH}. "
                'Genera uno con: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )

        # En producción un secreto efímero no es un atajo sino un bug: cada
        # deploy o reinicio (el plan free de Render reinicia seguido) cerraría
        # la sesión de todos, y con varios workers los tokens de uno no valen en
        # otro. Mejor no arrancar y que el deploy falle a la vista.
        if not self.jwt_secret and self.is_production:
            raise ValueError(
                "JWT_SECRET es obligatorio con ENVIRONMENT=production. "
                "Defínelo en las variables del servicio (en Render: generateValue o a mano). "
                'Genera uno con: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )

        # Nunca hay un secreto por default en el código: un literal hardcodeado
        # acabaría en producción y cualquiera con el repo podría firmar tokens.
        # Sin JWT_SECRET se usa uno aleatorio por proceso, que sirve para
        # desarrollar pero invalida los tokens en cada reinicio.
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(48)
            warnings.warn(
                "JWT_SECRET no está definido: se generó un secreto efímero. "
                "Todos los tokens se invalidan al reiniciar el backend y no "
                "funcionan entre varios procesos/workers. Definan JWT_SECRET "
                "en backend/.env para cualquier despliegue real.",
                RuntimeWarning,
                stacklevel=2,
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    # lru_cache = se lee el .env una sola vez, no en cada request.
    return Settings()
