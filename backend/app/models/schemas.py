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
    operating_days: list[str]
    city: str
    employees: str | None = None
    answers: dict[str, bool]