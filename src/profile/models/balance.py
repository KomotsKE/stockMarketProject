from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from typing import TYPE_CHECKING
from src.dataBase.base import Base
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from src.profile.models.user import UserORM
    from profile.models.instrument import InstrumentORM

class BalanceORM(Base):
    __tablename__ = 'balance'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))
    ticker: Mapped[str] = mapped_column(ForeignKey("instrument.ticker"))
    amount: Mapped[int]
    user: Mapped["UserORM"] = relationship(back_populates='balance')
    instrument: Mapped["InstrumentORM"] = relationship(back_populates='balance')

class TransactionORM(Base):
    __tablename__ = 'transaction'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(ForeignKey('instrument.ticker'))
    amount: Mapped[int]
    price: Mapped[int]
    timestamp: Mapped[datetime]
    instrument: Mapped["InstrumentORM"] = relationship(back_populates='transactions')