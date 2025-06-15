from ast import Tuple
import asyncio
from operator import and_
from fastapi import Depends, HTTPException, status, APIRouter
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from src.api.profile.user import get_user_by_token, is_admin, UserORM
from src.dataBase.models.instrument import InstrumentORM
from src.api.profile.instrument import get_instruments_list
from src.dataBase.models.balance import BalanceORM, TransactionORM
from src.dataBase.session import async_session_factory
from src.schemas.schemas import succesMessage, OK
from src.schemas.instrument import TickerStr
from src.schemas.order import OperationDirection
from src.schemas.user import User
from src.schemas.balance import BalanceTransaction, AmountInt
from typing import Dict, List

balance_router = APIRouter(prefix='/api/v1')

@balance_router.get("/balance", tags=["balance"])
async def get_balances(user: User = Depends(get_user_by_token)) -> Dict[str, int]:
    user_balance: Dict[str, int] = {}
    async with async_session_factory() as session:
        instruments = await get_instruments_list()
        for _, ticker in instruments:
            user_balance[ticker] = 0

        balances_result = await session.execute(
            select(BalanceORM.ticker, BalanceORM.amount)
            .where(BalanceORM.user_id == user.id, BalanceORM.amount > 0)
        )

        balances = balances_result.all()

        for ticker, amount in balances:
            user_balance[ticker] = amount

        return user_balance

@balance_router.post("/admin/balance/deposit", tags=["admin","balance"])
async def deposit(transaction: BalanceTransaction, rights: None = Depends(is_admin)) -> OK:
    async with async_session_factory() as session:
        stmt = (
            insert(BalanceORM)
            .values(user_id=transaction.user_id, ticker=transaction.ticker, amount=transaction.amount, reserved=0)
            .on_conflict_do_update(
                index_elements=["user_id", "ticker"],
                set_={"amount": BalanceORM.amount + transaction.amount}
            )
        )
        await session.execute(stmt)
        await session.commit()
        return succesMessage

@balance_router.post("/admin/balance/withdraw", tags=["admin","balance"])
async def withdraw(transaction: BalanceTransaction, rights: None = Depends(is_admin)) -> OK:
    async with async_session_factory() as session:
        result = await session.execute(
        select(BalanceORM).where(BalanceORM.user_id == transaction.user_id, BalanceORM.ticker == transaction.ticker)
        )
        balance = result.scalar_one_or_none()
        if balance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Инструмент у пользователя не найден")
        if balance.amount < transaction.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недостаточно средств на балансе")
        
        balance.amount -= transaction.amount

        await session.commit()
        return succesMessage

async def update_balances(
    session: AsyncSession,
    buyer_id: UUID,
    seller_id: UUID,
    orderTransaction: TransactionORM,
    isMarket: bool = False
):
    """
    Обновляет балансы после исполнения сделки, блокируя все нужные балансы за один вызов.
    """
    ticker = orderTransaction.ticker
    amount = orderTransaction.amount
    price = orderTransaction.price
    rub_amount = amount * price

    balance_specs = [
        (buyer_id, "RUB"),
        (seller_id, ticker),
        (seller_id, "RUB"),
        (buyer_id, ticker),
    ]
    
    balance_specs = sorted(set(balance_specs), key=lambda x: (str(x[0]), x[1]))
    
    balances = await bulk_lock_balances(session, balance_specs)

    def get(user, ticker):
        bal = balances.get((user, ticker))
        if bal is None:
            raise HTTPException(404, detail=f"Баланс {ticker} пользователя {user} не найден")
        return bal

    seller_asset = get(seller_id, ticker)
    seller_rub = get(seller_id, "RUB")

    if seller_asset.amount < amount:
        raise HTTPException(400, detail=f"Недостаточно {ticker} у продавца")
    seller_asset.amount -= amount
    seller_rub.amount += rub_amount

    buyer_rub = get(buyer_id, "RUB")
    buyer_asset = get(buyer_id, ticker)

    if buyer_rub.amount < rub_amount:
        raise HTTPException(400, detail="Недостаточно RUB у покупателя")
    buyer_rub.amount -= rub_amount
    buyer_asset.amount += amount

    if not isMarket:
        seller_asset.reserved = max(seller_asset.reserved - amount, 0)
        buyer_rub.reserved = max(buyer_rub.reserved - rub_amount, 0)

async def reserve_funds(
    session: AsyncSession, 
    user_id: UUID, 
    ticker: TickerStr, 
    qty: AmountInt, 
    price: AmountInt, 
    direction: OperationDirection
):
    if direction == OperationDirection.BUY:
        rub_needed = qty * price
        rub_balance = await lock_balance(session, user_id, "RUB")

        available = rub_balance.amount - rub_balance.reserved
        if available < rub_needed:
            raise HTTPException(status_code=400, detail="Недостаточно RUB для резервации")

        rub_balance.reserved += rub_needed

    elif direction == OperationDirection.SELL:
        asset_balance = await lock_balance(session, user_id, ticker)

        available = asset_balance.amount - asset_balance.reserved
        if available < qty:
            raise HTTPException(status_code=400, detail=f"Недостаточно {ticker} для резервации")

        asset_balance.reserved += qty

async def lock_balance(session: AsyncSession, user_id: UUID, ticker: TickerStr) -> BalanceORM:
    balances = await bulk_lock_balances(session, [(user_id, ticker)])
    balance = balances.get((user_id, ticker))
    if not balance:
        raise HTTPException(404, detail=f"Баланс {ticker} не найден")
    return balance

async def release_user_reserve(session: AsyncSession, user_id: UUID, ticker: str):
    balances = await bulk_lock_balances(session, [(user_id, ticker)])
    balance = balances.get((user_id, ticker))
    if not balance:
        raise HTTPException(status_code=404, detail=f"Баланс {ticker} пользователя {user_id} не найден")
    
    balance.reserved = 0

async def bulk_lock_balances(session: AsyncSession, balance_specs: List[Tuple[UUID, str]]) -> Dict[Tuple[UUID, str], BalanceORM]:
    """
    Блокирует несколько балансов одновременно в упорядоченном порядке.
    balance_specs: список кортежей (user_id, ticker)
    """
    sorted_specs = sorted(balance_specs, key=lambda x: (str(x[0]), x[1]))

    conditions = [
        and_(BalanceORM.user_id == user_id, BalanceORM.ticker == ticker)
        for user_id, ticker in sorted_specs
    ]
    
    from sqlalchemy import or_
    result = await session.execute(
        select(BalanceORM)
        .where(or_(*conditions))
        .with_for_update(nowait=True)
        .order_by(BalanceORM.user_id, BalanceORM.ticker)
    )
    
    balances = {(b.user_id, b.ticker): b for b in result.scalars().all()}
    return balances