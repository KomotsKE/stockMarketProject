from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from src.dataBase.base import Base
from src.stockMarket.models.instrument import InstrumentORM
from src.profile.models.user import UserORM
import uuid

class BalanceORM(Base):
    __tablename__ = 'balance'

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))
    ticker: Mapped[str] # = mapped_column(ForeignKey("instrument.ticker"), primary_key=True)
    amount: Mapped[int]
    user: Mapped["UserORM"] = relationship(back_populates='balance')
    instrument: Mapped["InstrumentORM"] = relationship(back_populates='balance')