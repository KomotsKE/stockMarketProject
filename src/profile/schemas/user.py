from enum import Enum
from pydantic import BaseModel, UUID4, Field

class Role(str, Enum):
    admin = 'admin'
    user = 'user'

class User(BaseModel):
    id: UUID4
    name: str
    role: Role
    api_key: str

class NewUser(BaseModel):
    name: str = Field(min_length=3)