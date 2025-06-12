from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, List
from src.dataBase.base import Base

if TYPE_CHECKING:
    from src.dataBase.models.balance import BalanceORM
    from src.dataBase.models.order import OrderORM
    from src.dataBase.models.balance import TransactionORM

class InstrumentORM(Base):
    __tablename__ = "instrument"

    name: Mapped[str]
    ticker: Mapped[str] = mapped_column(primary_key=True)
    balance: Mapped[List["BalanceORM"]] = relationship(back_populates="instrument")
    orders: Mapped[List["OrderORM"]] = relationship(back_populates="instrument")
    transactions: Mapped[List["TransactionORM"]] = relationship(back_populates="instrument")