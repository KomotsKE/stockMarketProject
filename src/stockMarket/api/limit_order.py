from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import datetime

from src.dataBase.session import async_session_factory
from src.stockMarket.models.order import OrderORM
from src.profile.api.user import get_user_by_token
from src.profile.schemas.user import User
from src.stockMarket.schemas.order import (
    LimitOrderBody,
    OrderStatus,
    OrderType,
    OperationDirection
)
from src.profile.models.balance import BalanceORM

limit_order_router = APIRouter(prefix="/api/v1/limit-order", tags=["limit-order"])

@limit_order_router.post("/create", response_model=dict)
async def create_limit_order(
    order_body: LimitOrderBody,
    user: User = Depends(get_user_by_token)
) -> dict:
    """
    Создает лимитный ордер на покупку или продажу ценных бумаг по заданной цене.
    Ордер действует до конца торгового дня.
    """
    async with async_session_factory() as session:
        # Проверяем баланс пользователя
        if order_body.direction == OperationDirection.BUY:
            # Для покупки проверяем наличие денег (с учетом комиссии 0.06%)
            required_amount = order_body.qty * order_body.price
            commission = required_amount * 0.0006  # 0.06%
            total_required = required_amount + commission
            
            balance_query = select(BalanceORM).where(
                BalanceORM.user_id == user.id,
                BalanceORM.ticker == "RUB"  # Предполагаем, что баланс в рублях
            )
            result = await session.execute(balance_query)
            balance = result.scalar_one_or_none()
            
            if not balance or balance.amount < total_required:
                raise HTTPException(
                    status_code=400,
                    detail="Недостаточно средств для выполнения операции"
                )
        else:
            # Для продажи проверяем наличие ценных бумаг
            balance_query = select(BalanceORM).where(
                BalanceORM.user_id == user.id,
                BalanceORM.ticker == order_body.ticker
            )
            result = await session.execute(balance_query)
            balance = result.scalar_one_or_none()
            
            if not balance or balance.amount < order_body.qty:
                raise HTTPException(
                    status_code=400,
                    detail="Недостаточно ценных бумаг для продажи"
                )

        # Создаем лимитный ордер
        order = OrderORM(
            id=uuid4(),
            type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            user_id=user.id,
            timestamp=datetime.datetime.now(),
            direction=order_body.direction,
            ticker=order_body.ticker,
            qty=order_body.qty,
            price=order_body.price
        )
        
        session.add(order)
        await session.commit()
        await session.refresh(order)
        
        return {
            "success": True,
            "order_id": order.id,
            "message": "Лимитный ордер успешно создан"
        }