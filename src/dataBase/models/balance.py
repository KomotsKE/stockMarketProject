from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from typing import TYPE_CHECKING
from src.dataBase.base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint
import uuid

if TYPE_CHECKING:
    from src.dataBase.models.user import UserORM
    from dataBase.models.instrument import InstrumentORM

class BalanceORM(Base):
    __tablename__ = 'balance'
    __table_args__ = (
        UniqueConstraint('user_id', 'ticker', name='uq_user_ticker'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))
    ticker: Mapped[str] = mapped_column(ForeignKey("instrument.ticker"))
    amount: Mapped[float]
    reserved: Mapped[float] = mapped_column(default=0)
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