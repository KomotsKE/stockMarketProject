import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from typing import List, TYPE_CHECKING

from src.profile.schemas.user import Role
from src.dataBase.base import Base

if TYPE_CHECKING:
    from src.profile.models.balance import BalanceORM

class UserORM(Base):
    __tablename__ = 'user'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str]
    role: Mapped[Role]
    api_key: Mapped[str]
    balance: Mapped[List["BalanceORM"]] = relationship(back_populates="user")
    


