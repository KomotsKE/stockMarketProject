from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import datetime
from typing import List

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
    OrderType,
    L2OrderBook,
    OperationDirection,
    Level
)

from src.public.schemas import succesMessage

order_router = APIRouter(prefix="/api/v1/order")

@order_router.post("", response_model=CreateOrderResponse, tags=["order"])
async def create_order(order_body: MarketOrderBody | LimitOrderBody,
                        user: User = Depends(get_user_by_token)) -> CreateOrderResponse:
    order = OrderORM(
        id = uuid4(),
        type=order_body.type,
        status=OrderStatus.NEW,
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

@order_router.get("", response_model=List[LimitOrder | MarketOrder], tags=["order"])
async def list_orders(user: User = Depends(get_user_by_token)) -> List[LimitOrder | MarketOrder]:
    response : List[LimitOrder | MarketOrder] = []
    async with async_session_factory() as session:
        query = select(OrderORM).where(OrderORM.user_id == user.id).order_by(OrderORM.timestamp)
        result = await session.execute(query)
        orders = result.scalars().all()
        for order in orders:
            base_order_data = {
                "id": order.id,
                "status": order.status,
                "user_id": order.user_id,
                "timestamp": order.timestamp,
            }
            
            if order.type == OrderType.MARKET:
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

@order_router.get("/{order_id}", response_model=LimitOrder | MarketOrder, tags=["order"])
async def get_order(order_id: UUID, user: User = Depends(get_user_by_token)) -> LimitOrder | MarketOrder:
    async with async_session_factory() as session:
        query = select(OrderORM).where(OrderORM.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        base_order_data = {
                "id": order.id,
                "status": order.status,
                "user_id": order.user_id,
                "timestamp": order.timestamp,
            }
        if order.type == OrderType.MARKET:
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

@order_router.delete("/{order_id}", response_model=succesMessage, tags=["order"])
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
        
        if order.status in [OrderStatus.CANCELLED, OrderStatus.EXEC]:
            raise HTTPException(status_code=400, detail="Cannot cancel order in current status")
        
        order.status = OrderStatus.CANCELLED
        await session.commit()
    
    return succesMessage

@order_router.get("/public/orderbook/{ticker}", tags=["public"])
async def get_orderbook(ticker: str, limit: int) -> L2OrderBook:
    ask_levels : List[Level] = []
    bid_levels : List[Level]= []
    async with async_session_factory() as session:
        query = select(OrderORM).where(OrderORM.ticker == ticker)\
            .order_by(OrderORM.timestamp).limit(limit)
        result = await session.execute(query)
        orders = result.scalars().all()
        for order in orders:
            level = Level(price=order.price, qty=order.qty)
            if order.direction == OperationDirection.BUY:
                bid_levels.append(level)
            else:
                ask_levels.append(level)
    return L2OrderBook(ask_levels=ask_levels, bid_levels=bid_levels)