from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from src.dataBase.base import Base
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.stockMarket.models.instrument import InstrumentORM

class transactionORM(Base):
    ticker: Mapped[str] = mapped_column(ForeignKey('instrument.ticker'))
    amount: Mapped[int]
    price: Mapped[int]
    timestamp: Mapped[datetime]
    instrument: Mapped["InstrumentORM"] = relationship(back_populates='transactions')