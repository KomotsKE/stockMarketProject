from pydantic import BaseModel, Field
from src.profile.schemas.balance import BalanceTransaction
from datetime import datetime

class Instrument(BaseModel):
    name: str
    ticker: str = Field(pattern=r"[A-Z]{2,10}")

class Transaction(BalanceTransaction):
    timestamp: datetime