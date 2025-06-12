import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import CheckConstraint, ForeignKey
from typing import List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from src.dataBase.models.user import UserORM
    from src.dataBase.models.instrument import InstrumentORM

from src.dataBase.base import Base
from src.schemas.order import OrderType, OrderStatus, OperationDirection

# Решил не разделять ордеры на разные табличны, чтобы не делать лишних джоинов, а все поля храню в 1 таблице, при этом указывая тип ордера. 
# Те поля которые встречаются не во всех ордерах могут быть null - nullable.
class OrderORM(Base):
    __tablename__ = 'order'

    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('qty >= 1', name='check_qty_positive'),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    type: Mapped[OrderType]
    status: Mapped[OrderStatus]
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('user.id', ondelete="CASCADE"))
    timestamp: Mapped[datetime]
    direction: Mapped[OperationDirection]
    ticker: Mapped[str] = mapped_column(ForeignKey('instrument.ticker', ondelete="CASCADE"))
    qty: Mapped[int]
    price: Mapped[int] = mapped_column(nullable=True)
    filled: Mapped[int] = mapped_column(nullable=True, default=0)
    user: Mapped["UserORM"] = relationship(back_populates='orders')
    instrument: Mapped["InstrumentORM"] = relationship(back_populates='orders')