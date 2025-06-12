from pydantic import BaseModel, UUID4, Field
from typing import Annotated

AmountInt = Annotated[int, Field(gt=0)]

class BalanceTransaction(BaseModel):
    user_id: UUID4
    ticker: str = Field(pattern=r"[A-Z]{2,10}")
    amount: AmountInt