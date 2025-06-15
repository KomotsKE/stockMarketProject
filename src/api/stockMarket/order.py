from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc
from asyncio import gather
import datetime
from typing import List, Dict, Any, Tuple, Optional, Union, overload
from src.dataBase.session import async_session_factory
from src.dataBase.models.order import OrderORM
from src.dataBase.models.balance import BalanceORM, TransactionORM
from src.api.profile.user import get_user_by_token
from src.api.profile.balance import update_balances, reserve_funds, lock_balance, release_user_reserve
from src.api.profile.instrument import get_instruments_list
from src.schemas.user import User
from src.schemas.instrument import TickerStr
from src.schemas.balance import AmountInt
from src.schemas.order import (
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

from src.schemas.schemas import succesMessage

order_router = APIRouter(prefix="/api/v1")

@overload
async def get_orderbook_orders(
    ticker: TickerStr, 
    session: AsyncSession, 
    orderSide: OperationDirection
) -> List[OrderORM]: ...

@overload
async def get_orderbook_orders(
    ticker: TickerStr, 
    session: AsyncSession, 
    orderSide: None = None
) -> Tuple[List[OrderORM], List[OrderORM]]: ...

async def get_orderbook_orders(ticker: TickerStr, session: AsyncSession, orderSide: Optional[OperationDirection] = None) -> Union[List[OrderORM], Tuple[List[OrderORM], List[OrderORM]]]:
    if orderSide is not None:
        if orderSide == OperationDirection.BUY:
            buy_query = (
                    select(OrderORM)
                        .where(
                            OrderORM.ticker == ticker,
                            OrderORM.type == OrderType.LIMIT,
                            OrderORM.status.in_([OrderStatus.NEW, OrderStatus.PART_EXEC]),
                            OrderORM.direction == OperationDirection.BUY
                        )
                    .order_by(desc(OrderORM.price), asc(OrderORM.timestamp))
                    .with_for_update()
                )
            return (await session.execute(buy_query)).scalars().all()
        else:
            sell_query = (
                    select(OrderORM)
                        .where(
                            OrderORM.ticker == ticker,
                            OrderORM.type == OrderType.LIMIT,
                            OrderORM.status.in_([OrderStatus.NEW, OrderStatus.PART_EXEC]),
                            OrderORM.direction == OperationDirection.SELL
                        )
                    .order_by(asc(OrderORM.price), asc(OrderORM.timestamp))
                    .with_for_update()
                )
            return (await session.execute(sell_query)).scalars().all()
    else:
        buy_query = (
                    select(OrderORM)
                        .where(
                            OrderORM.ticker == ticker,
                            OrderORM.type == OrderType.LIMIT,
                            OrderORM.status.in_([OrderStatus.NEW, OrderStatus.PART_EXEC]),
                            OrderORM.direction == OperationDirection.BUY
                        )
                    .order_by(desc(OrderORM.price), asc(OrderORM.timestamp))
                    .with_for_update()
                )

        sell_query = (
                        select(OrderORM)
                            .where(
                                OrderORM.ticker == ticker,
                                OrderORM.type == OrderType.LIMIT,
                                OrderORM.status.in_([OrderStatus.NEW, OrderStatus.PART_EXEC]),
                                OrderORM.direction == OperationDirection.SELL
                            )
                        .order_by(asc(OrderORM.price), asc(OrderORM.timestamp))
                        .with_for_update()
                    )

        buy_orders, sell_orders = await gather(
            session.execute(buy_query),
            session.execute(sell_query)
        )
        return buy_orders.scalars().all(), sell_orders.scalars().all()

@order_router.get("/public/orderbook/{ticker}", response_model=L2OrderBook, tags=["public"])
async def get_orderbook(ticker: TickerStr, limit: AmountInt = 10) -> L2OrderBook:
    """
    Возвращает книгу ордеров (стакан) для указанного тикера
    """
    async with async_session_factory() as session:

        ask_levels: Dict[float, int] = {}
        bid_levels: Dict[float, int] = {}

        query = select(OrderORM).where(
            OrderORM.ticker == ticker,
            OrderORM.type == OrderType.LIMIT,
            OrderORM.status.in_([OrderStatus.NEW, OrderStatus.PART_EXEC])
        )

        result = await session.execute(query)
        orders = result.scalars().all()

        for order in orders:
            remaining_qty = order.qty - (order.filled or 0)
            if remaining_qty <= 0:
                continue

            if order.direction == OperationDirection.BUY:
                bid_levels[order.price] = bid_levels.get(order.price, 0) + remaining_qty
            else:
                ask_levels[order.price] = ask_levels.get(order.price, 0) + remaining_qty

        sorted_asks = sorted(ask_levels.items())[:limit]
        sorted_bids = sorted(bid_levels.items(), reverse=True)[:limit]

        ask_result = [Level(price=p, qty=q) for p, q in sorted_asks]
        bid_result = [Level(price=p, qty=q) for p, q in sorted_bids]

    return L2OrderBook(ask_levels=ask_result, bid_levels=bid_result)

@order_router.get("/order/{order_id}", response_model=LimitOrder | MarketOrder, tags=["order"])
async def get_order(order_id: UUID, user: User = Depends(get_user_by_token)) -> LimitOrder | MarketOrder:
    """
    Возвращает информацию о конкретном ордере
    """
    async with async_session_factory() as session:
        query = select(OrderORM).where(OrderORM.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Ордер не найден")
        
        if order.user_id != user.id:
            raise HTTPException(status_code=403, detail="Нет доступа к ордеру")

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

@order_router.get("/order", response_model=List[LimitOrder | MarketOrder], tags=["order"])
async def list_orders(user: User = Depends(get_user_by_token)) -> List[LimitOrder | MarketOrder]:
    """
    Возвращает список всех ордеров пользователя
    """
    async with async_session_factory() as session:
        response : List[LimitOrder | MarketOrder] = []
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

@order_router.delete("/order/{order_id}", response_model=succesMessage, tags=["order"])
async def cancel_order(order_id: UUID, user: User = Depends(get_user_by_token)):
    """
    Отменяет ордер
    """
    async with async_session_factory() as session:
        query = select(OrderORM).where(
            OrderORM.id == order_id,
            OrderORM.user_id == user.id
        )
        result = await session.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="Ордер не найден")
        
        if order.status in [OrderStatus.CANCELLED, OrderStatus.EXEC]:
            raise HTTPException(status_code=400, detail="Невозможно отменить ордер в текущем статусе")
        
        remaining_qty = order.qty - order.filled
        if remaining_qty > 0 and order.type == OrderType.LIMIT:
            if order.direction == OperationDirection.BUY:
                rub_to_unreserve = remaining_qty * order.price
                balance = await lock_balance(session, order.user_id, "RUB")
                if balance and balance.reserved >= rub_to_unreserve:
                    balance.reserved -= rub_to_unreserve

            elif order.direction == OperationDirection.SELL:
                asset_balance = await lock_balance(session, order.user_id, order.ticker)
                if asset_balance and asset_balance.reserved >= remaining_qty:
                    asset_balance.reserved -= remaining_qty
        
        order.status = OrderStatus.CANCELLED
        await session.commit()
    
    return succesMessage

@order_router.post("/order", response_model=CreateOrderResponse, tags=["order"])
async def create_order(order_body: MarketOrderBody | LimitOrderBody,
                        user: User = Depends(get_user_by_token)) -> CreateOrderResponse:
    """
    Создает новый ордер (рыночный или лимитный)
    """
    async with async_session_factory() as session:

        instruments = await get_instruments_list()
        valid_tickers = {ticker for _, ticker in instruments}
        if order_body.ticker not in valid_tickers:
            raise HTTPException(status_code=400, detail="Неверный тикер")
        
        has_balance = await check_balance(
            session=session,
            user_id=user.id,
            ticker=order_body.ticker,
            qty=order_body.qty,
            price=getattr(order_body, 'price', None),
            direction=order_body.direction
        )
        
        if not has_balance:
            raise HTTPException(
                status_code=400,
                detail="Недостаточно средств или активов для выполнения операции"
            )
        
        order = OrderORM(
            id = uuid4(),
            type=order_body.type,
            status=OrderStatus.NEW,
            user_id= user.id,
            timestamp = datetime.datetime.now(datetime.timezone.utc),
            direction=order_body.direction,
            ticker=order_body.ticker,
            qty=order_body.qty,
            price=getattr(order_body, 'price', None)
        )

        if order.type == OrderType.LIMIT:
            await reserve_funds(session, order.user_id, order.ticker, order.qty, order.price, order.direction)
        if order.type == OrderType.MARKET:
            await execute_market_order(order, session)

        session.add(order)
        await session.commit()
        await session.refresh(order)

        match_limit_orders(order.ticker)
    
    return CreateOrderResponse(order_id=order.id)

async def check_balance(
    session: AsyncSession, 
    user_id: UUID, 
    ticker: TickerStr, 
    qty: AmountInt, 
    price: AmountInt | None, 
    direction: OperationDirection
) -> bool:
    """
    Проверяет достаточно ли средств/активов для выполнения операции
    """
    if direction == OperationDirection.BUY:
        if price is None:
            market_price = await get_market_order_execution_price(session, ticker, qty, direction)
            if market_price is None:
                return False 
            price = market_price
            
        required_amount = qty * price
        commission = required_amount * 0.0006
        total_required = required_amount + commission
        
        balance_query = select(BalanceORM).where( 
            BalanceORM.user_id == user_id,
            BalanceORM.ticker == "RUB"
        )
        result = await session.execute(balance_query)
        balance = result.scalar_one_or_none()

        if not balance:
            return False
        
        free = balance.amount - balance.reserved
        return free >= total_required
    
    elif direction == OperationDirection.SELL:
        balance_query = select(BalanceORM).where(
            BalanceORM.user_id == user_id,
            BalanceORM.ticker == ticker
        )
        result = await session.execute(balance_query)
        balance = result.scalar_one_or_none()
        if not balance:
            return False

        free = balance.amount - balance.reserved
        return free >= qty
    
    return True
        
async def execute_market_order(marketOrder: OrderORM, session: AsyncSession):
    if marketOrder.type != OrderType.MARKET:
        raise HTTPException(status_code=422, detail="Данная операция доступна только для рыночного ордера")

    opposite_side = OperationDirection.SELL if marketOrder.direction == OperationDirection.BUY else OperationDirection.BUY
    orders = await get_orderbook_orders(marketOrder.ticker, session, opposite_side)
    remaining_qty = marketOrder.qty
    executed_transactions = []

    for order in orders:
        if order.status not in {OrderStatus.NEW, OrderStatus.PART_EXEC}:
            continue

        order_available = order.qty - (order.filled or 0)
        match_qty = min(order_available, remaining_qty)

        if match_qty <= 0:
            continue

        prev_filled = order.filled or 0
        prev_status = order.status

        order.filled = prev_filled + match_qty
        order.status = OrderStatus.EXEC if order.filled >= order.qty else OrderStatus.PART_EXEC

        price = order.price or 0

        transaction = TransactionORM(
            id=uuid4(),
            ticker=marketOrder.ticker,
            amount=match_qty,
            price=price,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        await update_balances(
            session,
            orderTransaction=transaction,
            buyer_id=marketOrder.user_id if marketOrder.direction == OperationDirection.BUY else order.user_id,
            seller_id=order.user_id if marketOrder.direction == OperationDirection.BUY else marketOrder.user_id,
            isMarket=True
        )

        session.add(transaction)
        executed_transactions.append((order, prev_filled, prev_status, transaction))  # Сохраняем для отката

        remaining_qty -= match_qty

        if remaining_qty == 0:
            break

    if remaining_qty == 0:
        marketOrder.status = OrderStatus.EXEC
        marketOrder.filled = marketOrder.qty
    else:
        marketOrder.status = OrderStatus.CANCELLED
        marketOrder.filled = 0

        if executed_transactions:
            for order, prev_filled, prev_status, transaction in executed_transactions:
                order.filled = prev_filled
                order.status = prev_status
                await session.delete(transaction)

    session.add(marketOrder)
    await session.commit()

async def match_limit_orders(ticker: TickerStr):
    """
    Запускает процесс сопоставления ордеров (matching engine)
    """
    async with async_session_factory() as session:
        buy_orders, sell_orders = await get_orderbook_orders(ticker, session)

        for buy_order in buy_orders:
            if buy_order.status not in {OrderStatus.NEW, OrderStatus.PART_EXEC}:
                continue
                
            for sell_order in sell_orders:
                if sell_order.status not in {OrderStatus.NEW, OrderStatus.PART_EXEC}:
                    continue
                    
                if buy_order.price >= sell_order.price:
                    buy_available = buy_order.qty - (buy_order.filled or 0)
                    sell_available = sell_order.qty - (sell_order.filled or 0)
                    match_qty = min(buy_available, sell_available)
                    
                    if match_qty > 0:
                        buy_order.filled = (buy_order.filled or 0) + match_qty
                        sell_order.filled = (sell_order.filled or 0) + match_qty
                        
                        if buy_order.filled >= buy_order.qty:
                            buy_order.status = OrderStatus.EXEC
                            await release_user_reserve(session, user_id=buy_order.user_id, ticker="RUB")
                        else:
                            buy_order.status = OrderStatus.PART_EXEC
                            
                        if sell_order.filled >= sell_order.qty:
                            sell_order.status = OrderStatus.EXEC
                            await release_user_reserve(session, user_id=sell_order.user_id, ticker=ticker)
                        else:
                            sell_order.status = OrderStatus.PART_EXEC

                        transaction = TransactionORM(id = uuid4(), ticker = ticker, amount = match_qty, price = sell_order.price, timestamp=datetime.datetime.now(datetime.timezone.utc))
                        await update_balances(session, orderTransaction=transaction, buyer_id=buy_order.user_id, seller_id=sell_order.user_id)
                        
                        session.add(transaction)
                        if buy_order.status == OrderStatus.EXEC:
                            break
                else:
                    break

        await session.commit()

async def get_market_order_execution_price(
    session: AsyncSession,
    ticker: TickerStr,
    qty: AmountInt,
    direction: OperationDirection
) -> float | None:
    """
    Вычисляет среднюю цену исполнения рыночного ордера на основе ордербука
    """
    if direction == OperationDirection.BUY:
        sell_orders = await get_orderbook_orders(ticker, session, OperationDirection.SELL)
        if not sell_orders:
            return None
        
        remaining_qty = qty
        total_cost = 0.0
        
        for order in sell_orders:
            available_qty = order.qty - (order.filled or 0)
            if available_qty <= 0:
                continue
                
            execute_qty = min(remaining_qty, available_qty)
            total_cost += execute_qty * order.price
            remaining_qty -= execute_qty
            
            if remaining_qty <= 0:
                break
        
        if remaining_qty > 0:
            return None
            
        return total_cost / qty
    
    else:  # SELL
        buy_orders = await get_orderbook_orders(ticker, session, OperationDirection.BUY)
        if not buy_orders:
            return None
        
        remaining_qty = qty
        total_revenue = 0.0
        
        for order in buy_orders:
            available_qty = order.qty - (order.filled or 0)
            if available_qty <= 0:
                continue
                
            execute_qty = min(remaining_qty, available_qty)
            total_revenue += execute_qty * order.price
            remaining_qty -= execute_qty
            
            if remaining_qty <= 0:
                break
        
        if remaining_qty > 0:
            return None
            
        return total_revenue / qty