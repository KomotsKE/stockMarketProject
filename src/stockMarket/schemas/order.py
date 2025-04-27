from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, UUID4
from typing import List

class OperationDirection(str, Enum):
    buy = "BUY"
    sell = "SELL"

class OrderStatus(str, Enum):
    new = "NEW"
    exec = "EXECUTED"
    part_exec = "PARTIALLY_EXECUTED"
    canclled = "CANCELLED"

class OrderType(str, Enum):
    market = "MARKET"
    limit = "LIMIT"
    @classmethod
    def from_order(cls, order: 'OrderBody') -> 'OrderType':
        return cls.limit if hasattr(order, 'price') and order.price is not None else cls.market

class OrderBody(BaseModel):
    direction : OperationDirection
    ticker: str = Field(pattern=r"[A-Z]{2,10}")
    qty: int = Field(ge=1)
    @property
    def type(self) -> OrderType:
        return OrderType.from_order(self)
    
class MarketOrderBody(OrderBody):
    pass

class LimitOrderBody(OrderBody):
    price : int = Field(gt=0)

class Order(BaseModel):
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

class CreateOrderResponse(BaseModel):
    success: bool = Field(default=True)
    order_id: UUID4
