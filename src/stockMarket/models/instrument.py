from sqlalchemy.orm import Mapped, mapped_column
from src.dataBase.base import Base

class InstrumentORM(Base):
    __tablename__ = "instrument"

    name: Mapped[str]
    ticker: Mapped[str] = mapped_column(primary_key=True)