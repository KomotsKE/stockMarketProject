from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.dataBase.base import Base
from src.profile.models.balance import BalanceORM

class InstrumentORM(Base):
    __tablename__ = "instrument"

    name: Mapped[str]
    ticker: Mapped[str] = mapped_column(primary_key=True)
    balance: Mapped["BalanceORM"] = relationship(back_populates="instrument")
