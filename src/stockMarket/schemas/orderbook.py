from pydantic import BaseModel
from typing import List

class Level(BaseModel):
    price: int
    qty: int

class L2OrderBook(BaseModel):
    bid_levels : List[Level]
    ask_levels : List[Level]