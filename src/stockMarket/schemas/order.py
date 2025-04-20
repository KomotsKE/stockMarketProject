from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, UUID4
from typing import List

class OperationDirection(int, Enum):
    0 = "BUY"
    1 = "SELL"

class OrderStatus(int, Enum):
    0 = "NEW"
    1 = "EXECUTED"
    2 = "PARTIALLY_EXECUTED"
    3 = "CANCELLED"

class OrderBody(BaseModel):
    direction : OperationDirection
    ticker: str = Field(pattern=r"[A-Z]{2,10}")
    qty: int = Field(ge=1)

class MarketOrderBody(OrderBody):
    pass

class LimitOrderBody(OrderBody):
    price : int = Field(gt=0)

class Order():
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime

class MarketOrder(Order):
    body: MarketOrderBody

class LimitOrder(Order):
    body: LimitOrderBody
    filled: int = Field(default=0)

class Level(BaseModel):
    price: int
    qty: int

class L2OrderBook(BaseModel):
    bid_levels : List[Level]
    ask_levels : List[Level]