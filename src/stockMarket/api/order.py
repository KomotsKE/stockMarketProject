from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import datetime

from src.dataBase.session import async_session_factory
from src.stockMarket.models.order import OrderORM
from src.profile.api.user import get_user_by_token
from src.profile.schemas.user import User
from src.stockMarket.schemas.order import (
    MarketOrderBody,
    LimitOrderBody,
    CreateOrderResponse,
    MarketOrder,
    LimitOrder,
    OrderStatus,
    OrderType
)

from src.public.schemas import succesMessage

order_router = APIRouter(prefix="/api/v1/order", tags=["order"])

@order_router.post("", response_model=CreateOrderResponse)
async def create_order(order_body: MarketOrderBody | LimitOrderBody,
                        user: User = Depends(get_user_by_token)) -> CreateOrderResponse:
    order = OrderORM(
        id = uuid4(),
        type=order_body.type,
        status=OrderStatus.new,
        user_id= user.id,
        timestamp = datetime.datetime.now(),
        direction=order_body.direction,
        ticker=order_body.ticker,
        qty=order_body.qty,
        price=getattr(order_body, 'price', None)
    )
    async with async_session_factory() as session:
        session.add(order)
        await session.commit()
        await session.refresh(order)
    
    return CreateOrderResponse(order_id=order.id)

@order_router.get("", response_model=list[LimitOrder | MarketOrder])
async def list_orders(user: User = Depends(get_user_by_token)) -> list[LimitOrder | MarketOrder]:
    response : list[LimitOrder | MarketOrder] = []
    async with async_session_factory() as session:
        query = select(OrderORM).where(OrderORM.user_id == user.id)
        result = await session.execute(query)
        orders = result.scalars().all()
        for order in orders:
            base_order_data = {
                "id": order.id,
                "status": order.status,
                "user_id": order.user_id,
                "timestamp": order.timestamp,
            }
            
            if order.type == OrderType.market:
                body = MarketOrderBody(
                    direction=order.direction,
                    ticker=order.ticker,
                    qty=order.qty
                )
                response.append(MarketOrder(**base_order_data, body=body))
            else:
                body = LimitOrderBody(
                    direction=order.direction,
                    ticker=order.ticker,
                    qty=order.qty,
                    price=order.price
                )
                response.append(LimitOrder(**base_order_data, body=body, filled=order.filled))
                
    return response

@order_router.get("/{order_id}")
async def get_order(order_id: UUID, user: User = Depends(get_user_by_token)):
    async with async_session_factory() as session:
        query = select(OrderORM).where(OrderORM.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()
        base_order_data = {
                "id": order.id,
                "status": order.status,
                "user_id": order.user_id,
                "timestamp": order.timestamp,
            }
        if order.type == OrderType.market:
            body = MarketOrderBody(
                direction=order.direction,
                ticker=order.ticker,
                qty=order.qty
            )
            return MarketOrder(**base_order_data, body=body)
        else:
            body = LimitOrderBody(
                direction=order.direction,
                ticker=order.ticker,
                qty=order.qty,
                price=order.price
            )
            return LimitOrder(**base_order_data, body=body, filled=order.filled)

@order_router.delete("/{order_id}", response_model=succesMessage)
async def cancel_order(order_id: UUID, user: User = Depends(get_user_by_token)):
    async with async_session_factory() as session:
        query = select(OrderORM).where(
            OrderORM.id == order_id,
            OrderORM.user_id == user.id
        )
        result = await session.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order.status in [OrderStatus.canclled, OrderStatus.exec]:
            raise HTTPException(status_code=400, detail="Cannot cancel order in current status")
        
        order.status = OrderStatus.canclled
        await session.commit()
    
    return succesMessage