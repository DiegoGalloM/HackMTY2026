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
