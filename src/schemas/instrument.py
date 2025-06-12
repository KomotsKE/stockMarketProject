from pydantic import BaseModel, Field
from src.schemas.balance import BalanceTransaction
from datetime import datetime
from typing import Annotated

TickerStr = Annotated[str, Field(pattern=r"^[A-Z]{2,10}$")]
LimitInt = Annotated[int, Field(gt=0)]

class Instrument(BaseModel):
    name: str
    ticker: TickerStr

class Transaction(BalanceTransaction):
    timestamp: datetime