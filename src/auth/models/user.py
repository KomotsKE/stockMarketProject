import enum
import uuid

from sqlalchemy import String, Enum, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from src.auth.schemas.user import Role
from src.dataBase.base import Base

class UserORM(Base):
    __tablename__ = 'user'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str]
    role: Mapped[Role]
    api_key: Mapped[str]


