from pydantic import BaseModel


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
    merchant_id: str
    amount: float
    description: str = ""

class BusinessProfile(BaseModel):
    category: str
    category_detail: str | None = None
    operating_days: list[str]
    city: str
    employees: str | None = None
    answers: dict[str, bool]
    week_description_mode: str | None = None
    week_description_text: str | None = None
    week_description_audio_base64: str | None = None
    week_description_audio_mime: str | None = None