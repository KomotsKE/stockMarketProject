from pydantic import BaseModel, Field
from datetime import datetime

class Transaction(BaseModel):
    ticker: str = Field(pattern=r"[A-Z]{2,10}")
    amount: int
    price: int
    timestamp: datetime