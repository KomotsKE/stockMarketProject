from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import datetime
from typing import List, Dict, Any

from src.dataBase.session import async_session_factory
from src.dataBase.models.order import OrderORM
from src.dataBase.models.balance import BalanceORM
from src.api.profile.user import get_user_by_token
from src.schemas.user import User
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

order_router = APIRouter(prefix="/api/v1/order")

async def check_balance(
    session: AsyncSession, 
    user_id: UUID, 
    ticker: str, 
    qty: int, 
    price: int = None, 
    direction: OperationDirection = None
) -> bool:
    """
    Проверяет достаточно ли средств/активов для выполнения операции
    """
    if direction == OperationDirection.BUY and price is not None:
        # Для покупки проверяем наличие денег (с учетом комиссии 0.06%)
        required_amount = qty * price
        commission = required_amount * 0.0006  # 0.06%
        total_required = required_amount + commission
        
        balance_query = select(BalanceORM).where(
            BalanceORM.user_id == user_id,
            BalanceORM.ticker == "RUB"  # Предполагаем, что баланс в рублях
        )
        result = await session.execute(balance_query)
        balance = result.scalar_one_or_none()
        
        return balance is not None and balance.amount >= total_required
    
    elif direction == OperationDirection.SELL:
        # Для продажи проверяем наличие ценных бумаг
        balance_query = select(BalanceORM).where(
            BalanceORM.user_id == user_id,
            BalanceORM.ticker == ticker
        )
        result = await session.execute(balance_query)
        balance = result.scalar_one_or_none()
        
        return balance is not None and balance.amount >= qty
    
    return True  # Если не требуется проверка баланса

@order_router.post("", response_model=CreateOrderResponse, tags=["order"])
async def create_order(order_body: MarketOrderBody | LimitOrderBody,
                        user: User = Depends(get_user_by_token)) -> CreateOrderResponse:
    """
    Создает новый ордер (рыночный или лимитный)
    """
    async with async_session_factory() as session:
        # Проверяем баланс
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
        
        # Создаем ордер
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
        
        session.add(order)
        await session.commit()
        await session.refresh(order)
        
        # Если это рыночный ордер, сразу пытаемся его исполнить
        if order.type == OrderType.MARKET:
            await execute_market_order(order.id, session)
    
    return CreateOrderResponse(order_id=order.id)

async def execute_market_order(order_id: UUID, session: AsyncSession = None) -> Dict[str, Any]:
    """
    Выполняет рыночный ордер
    """
    close_session = False
    if session is None:
        session = async_session_factory()
        close_session = True
    
    try:
        # Получаем ордер
        query = select(OrderORM).where(OrderORM.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()
        
        if not order or order.type != OrderType.MARKET:
            raise HTTPException(status_code=404, detail="Рыночный ордер не найден")
        
        # Здесь должна быть логика исполнения ордера по лучшей цене
        # В реальной системе это было бы взаимодействие с биржевым API или с книгой ордеров
        
        # Для демонстрации просто меняем статус ордера
        order.status = OrderStatus.EXEC
        await session.commit()
        
        return {
            "success": True,
            "order_id": order.id,
            "message": "Рыночный ордер успешно исполнен"
        }
    finally:
        if close_session:
            await session.close()

@order_router.post("/execute/{order_id}", response_model=Dict[str, Any], tags=["order"])
async def execute_order_endpoint(
    order_id: UUID, 
    user: User = Depends(get_user_by_token)
) -> Dict[str, Any]:
    """
    Эндпоинт для принудительного исполнения ордера
    """
    async with async_session_factory() as session:
        # Проверяем, что ордер принадлежит пользователю
        query = select(OrderORM).where(
            OrderORM.id == order_id,
            OrderORM.user_id == user.id
        )
        result = await session.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="Ордер не найден")
        
        if order.status != OrderStatus.NEW:
            raise HTTPException(status_code=400, detail="Ордер не может быть исполнен в текущем статусе")
        
        if order.type == OrderType.MARKET:
            return await execute_market_order(order_id, session)
        else:
            return await execute_limit_order(order_id, session)

async def execute_limit_order(order_id: UUID, session: AsyncSession = None) -> Dict[str, Any]:
    """
    Выполняет лимитный ордер
    """
    close_session = False
    if session is None:
        session = async_session_factory()
        close_session = True
    
    try:
        # Получаем ордер
        query = select(OrderORM).where(OrderORM.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()
        
        if not order or order.type != OrderType.LIMIT:
            raise HTTPException(status_code=404, detail="Лимитный ордер не найден")
        
        # Здесь должна быть логика проверки, можно ли исполнить лимитный ордер
        # по текущей рыночной цене
        
        # Для демонстрации просто меняем статус ордера
        order.status = OrderStatus.EXEC
        await session.commit()
        
        return {
            "success": True,
            "order_id": order.id,
            "message": "Лимитный ордер успешно исполнен"
        }
    finally:
        if close_session:
            await session.close()

@order_router.get("", response_model=List[LimitOrder | MarketOrder], tags=["order"])
async def list_orders(user: User = Depends(get_user_by_token)) -> List[LimitOrder | MarketOrder]:
    """
    Возвращает список всех ордеров пользователя
    """
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
    """
    Возвращает информацию о конкретном ордере
    """
    async with async_session_factory() as session:
        query = select(OrderORM).where(OrderORM.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Ордер не найден")

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
        
        order.status = OrderStatus.CANCELLED
        await session.commit()
    
    return succesMessage

@order_router.get("/public/orderbook/{ticker}", response_model=L2OrderBook, tags=["public"])
async def get_orderbook(ticker: str, limit: int = 10) -> L2OrderBook:
    """
    Возвращает книгу ордеров (стакан) для указанного тикера
    """
    ask_levels : List[Level] = []
    bid_levels : List[Level]= []
    async with async_session_factory() as session:
        # Получаем только активные лимитные ордера
        query = select(OrderORM).where(
            OrderORM.ticker == ticker,
            OrderORM.type == OrderType.LIMIT,
            OrderORM.status == OrderStatus.NEW
        ).order_by(OrderORM.price, OrderORM.timestamp).limit(limit)
        
        result = await session.execute(query)
        orders = result.scalars().all()
        
        # Группируем ордера по цене для формирования уровней стакана
        price_levels = {}
        for order in orders:
            price = order.price
            if price not in price_levels:
                price_levels[price] = 0
            price_levels[price] += order.qty - (order.filled or 0)
        
        # Формируем уровни стакана
        for order in orders:
            if order.price in price_levels and price_levels[order.price] > 0:
                level = Level(price=order.price, qty=price_levels[order.price])
                price_levels[order.price] = 0  # Отмечаем, что уровень уже добавлен
                
                if order.direction == OperationDirection.BUY:
                    bid_levels.append(level)
                else:
                    ask_levels.append(level)
        
        # Сортируем уровни
        ask_levels.sort(key=lambda x: x.price)  # Продажи от низкой к высокой цене
        bid_levels.sort(key=lambda x: x.price, reverse=True)  # Покупки от высокой к низкой цене
        
    return L2OrderBook(ask_levels=ask_levels, bid_levels=bid_levels)

@order_router.post("/match", response_model=Dict[str, Any], tags=["order"])
async def match_orders() -> Dict[str, Any]:
    """
    Запускает процесс сопоставления ордеров (matching engine)
    """
    matched_count = 0
    
    async with async_session_factory() as session:
        # Получаем все активные лимитные ордера, сгруппированные по тикеру
        query = select(OrderORM).where(
            OrderORM.status == OrderStatus.NEW,
            OrderORM.type == OrderType.LIMIT
        ).order_by(OrderORM.ticker, OrderORM.timestamp)
        
        result = await session.execute(query)
        orders = result.scalars().all()
        
        # Группируем ордера по тикеру
        orders_by_ticker = {}
        for order in orders:
            if order.ticker not in orders_by_ticker:
                orders_by_ticker[order.ticker] = []
            orders_by_ticker[order.ticker].append(order)
        
        # Для каждого тикера пытаемся сопоставить ордера
        for ticker, ticker_orders in orders_by_ticker.items():
            # Разделяем на ордера на покупку и продажу
            buy_orders = [o for o in ticker_orders if o.direction == OperationDirection.BUY]
            sell_orders = [o for o in ticker_orders if o.direction == OperationDirection.SELL]
            
            # Сортируем ордера на покупку по убыванию цены (лучшая цена покупки - самая высокая)
            buy_orders.sort(key=lambda x: (-x.price, x.timestamp))
            # Сортируем ордера на продажу по возрастанию цены (лучшая цена продажи - самая низкая)
            sell_orders.sort(key=lambda x: (x.price, x.timestamp))
            
            # Пытаемся сопоставить ордера
            for buy_order in buy_orders:
                if buy_order.status != OrderStatus.NEW:
                    continue
                    
                for sell_order in sell_orders:
                    if sell_order.status != OrderStatus.NEW:
                        continue
                        
                    # Если цена покупки >= цены продажи, можем сопоставить ордера
                    if buy_order.price >= sell_order.price:
                        # Определяем количество для сделки (минимум из двух ордеров)
                        buy_available = buy_order.qty - (buy_order.filled or 0)
                        sell_available = sell_order.qty - (sell_order.filled or 0)
                        match_qty = min(buy_available, sell_available)
                        
                        if match_qty > 0:
                            # Обновляем заполненное количество
                            buy_order.filled = (buy_order.filled or 0) + match_qty
                            sell_order.filled = (sell_order.filled or 0) + match_qty
                            
                            # Обновляем статусы ордеров
                            if buy_order.filled >= buy_order.qty:
                                buy_order.status = OrderStatus.EXEC
                            else:
                                buy_order.status = OrderStatus.PART_EXEC
                                
                            if sell_order.filled >= sell_order.qty:
                                sell_order.status = OrderStatus.EXEC
                            else:
                                sell_order.status = OrderStatus.PART_EXEC
                            
                            matched_count += 1
                            
                            # Здесь должна быть логика обновления балансов пользователей
                            # и создания записей о транзакциях
                            
                            # Если ордер на покупку полностью исполнен, переходим к следующему
                            if buy_order.status == OrderStatus.EXEC:
                                break
        
        await session.commit()
    
    return {
        "success": True,
        "matched_orders": matched_count,
        "message": f"Сопоставлено {matched_count} ордеров"
    }
