from pydantic import BaseModel, UUID4, Field

class BalanceTransaction(BaseModel):
    user_id: UUID4
    ticker: str = Field(pattern=r"[A-Z]{2,10}")
    amount: int = Field(gt=0)