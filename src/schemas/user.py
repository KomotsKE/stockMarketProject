from enum import Enum
from pydantic import BaseModel, UUID4, Field
from typing import Optional

class Role(str, Enum):
    ADMIN = 'ADMIN'
    USER = 'USER'

class User(BaseModel):
    id: UUID4
    name: str
    role: Role
    api_key: str

class NewUser(BaseModel):
    name: str = Field(min_length=3)
    role: Role = Field(default=Role.USER)

class CreateOrderResponse(BaseModel):
    succes: bool = Field(default=True)
    order_id: UUID4