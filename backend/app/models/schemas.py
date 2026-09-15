from datetime import UTC, date, datetime

from pydantic import BaseModel, Field, field_validator


class Account(BaseModel):
    id: str
    type: str
    nickname: str | None = None
    balance: float


class Transaction(BaseModel):
    id: str
    type: str
    amount: float
    description: str
    date: str
    status: str


class NewPurchase(BaseModel):
    # Ruta heredada de Nessie: acotada aunque en producción esté apagada.
    merchant_id: str = Field(min_length=1, max_length=64)
    amount: float = Field(gt=0, le=1_000_000)
    description: str = Field(default="", max_length=300)

# Topes de tamaño del perfil. Sin ellos, cualquier usuario registrado puede
# mandar `answers` con 100 000 llaves y, como /business-profile/stats/{category}
# es público, esa respuesta gigante se la queda sirviendo a quien sea (y en
# Snowflake el FLATTEN … GROUP BY crece igual). El audio además reventaría el
# límite de 16 MB por columna con un 500.
MAX_AUDIO_BASE64 = 2_000_000  # ~1.5 MB de audio


class BusinessProfile(BaseModel):
    category: str = Field(max_length=64)
    category_detail: str | None = Field(default=None, max_length=200)
    operating_days: list[str] = Field(max_length=7)
    city: str = Field(max_length=120)
    employees: str | None = Field(default=None, max_length=40)
    answers: dict[str, bool] = Field(max_length=64)
    week_description_mode: str | None = Field(default=None, max_length=16)
    week_description_text: str | None = Field(default=None, max_length=4000)
    week_description_audio_base64: str | None = Field(default=None, max_length=MAX_AUDIO_BASE64)
    week_description_audio_mime: str | None = Field(default=None, max_length=100)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

MIN_AGE = 18
MAX_AGE = 120

# Solo minúsculas, dígitos y . _ - : el username va en URLs y en logs, así que
# se limita a un set sin sorpresas de encoding ni acentos.
USERNAME_PATTERN = r"^[a-z0-9._-]+$"


def _normalize_username(value):
    # Se normaliza ANTES de validar longitud/regex (validador mode="before"),
    # para que "  DoñaTere " y "dontere" se juzguen ya limpios y, sobre todo,
    # para que el chequeo de duplicados compare siempre la misma forma.
    return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=USERNAME_PATTERN)
    business_name: str = Field(min_length=1, max_length=120)
    full_name: str = Field(min_length=1, max_length=120)
    birthdate: str
    # La contraseña no lleva restricciones de pydantic a propósito: su política
    # se revisa en el router para poder responder 400 con los códigos de
    # problema que el frontend muestra, en vez de un 422 genérico de pydantic.
    password: str

    _normalize = field_validator("username", mode="before")(_normalize_username)

    @field_validator("business_name", "full_name", mode="before")
    @classmethod
    def _strip_text(cls, value):
        # Con el strip aquí, "   " queda en "" y truena con min_length=1.
        return value.strip() if isinstance(value, str) else value

    @field_validator("birthdate")
    @classmethod
    def _validate_birthdate(cls, value: str) -> str:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("birthdate debe tener formato YYYY-MM-DD") from exc

        # UTC y no la hora local del servidor: así la frontera de los 18 años
        # es la misma corra el backend en Render o en la laptop de quien sea.
        today = datetime.now(UTC).date()
        if parsed >= today:
            raise ValueError("birthdate tiene que estar en el pasado")

        # Se resta un año si todavía no ha pasado el cumpleaños de este año.
        age = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))
        if age < MIN_AGE:
            raise ValueError(f"hay que tener al menos {MIN_AGE} años")
        if age > MAX_AGE:
            raise ValueError(f"birthdate implica más de {MAX_AGE} años")

        # Se regresa normalizado para que la respuesta siempre sea YYYY-MM-DD.
        return parsed.isoformat()


class LoginRequest(BaseModel):
    # Sin regex ni longitudes: un username con forma inválida tiene que salir
    # como 401 invalid_credentials, no como 422, para no revelar qué usernames
    # podrían existir.
    username: str
    password: str

    _normalize = field_validator("username", mode="before")(_normalize_username)


class UserPublic(BaseModel):
    """Lo único que sale por la API. NO tiene password ni password_hash, y por eso
    es un modelo aparte de StoredUser en vez de heredar de él: así no hay forma
    de que un campo nuevo del usuario guardado se filtre solo."""

    user_id: str
    username: str
    business_name: str
    full_name: str
    birthdate: str


class StoredUser(BaseModel):
    """El usuario tal como vive en el store. Nunca se serializa a una respuesta."""

    user_id: str
    username: str
    business_name: str
    full_name: str
    birthdate: str
    password_hash: str

    def to_public(self) -> UserPublic:
        return UserPublic(
            user_id=self.user_id,
            username=self.username,
            business_name=self.business_name,
            full_name=self.full_name,
            birthdate=self.birthdate,
        )


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic
