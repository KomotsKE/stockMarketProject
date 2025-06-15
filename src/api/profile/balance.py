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
from typing import Dict

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
        await increase_balance(session, user_id=transaction.user_id, ticker=transaction.ticker, amount=transaction.amount)
        await session.commit()
        return succesMessage

@balance_router.post("/admin/balance/withdraw", tags=["admin","balance"])
async def withdraw(transaction: BalanceTransaction, rights: None = Depends(is_admin)) -> OK:
    async with async_session_factory() as session:
        await decrease_balance(session, user_id=transaction.user_id, ticker=transaction.ticker, amount=transaction.amount)
        await session.commit()
        return succesMessage

async def update_balances(session: AsyncSession, buyer_id: UUID, seller_id: UUID, orderTransaction: TransactionORM, isMarket: bool = False):
    ticker = orderTransaction.ticker
    amount = orderTransaction.amount
    price = orderTransaction.price
    rub_amount = amount * price

    await decrease_balance(session, user_id=seller_id, ticker=ticker, amount=amount)
    await increase_balance(session, user_id=buyer_id, ticker=ticker, amount=amount)

    await decrease_balance(session, user_id=buyer_id, ticker="RUB", amount=rub_amount)
    await increase_balance(session, user_id=seller_id, ticker="RUB", amount=rub_amount)

    rub_balance_result = await session.execute(
        select(BalanceORM).where(BalanceORM.user_id == buyer_id, BalanceORM.ticker == "RUB").with_for_update()
    )
    buyer_balance_RUB = rub_balance_result.scalar_one_or_none()

    if buyer_balance_RUB is None:
        raise HTTPException(status_code=404, detail="Баланс RUB покупателя не найден")

    seller_balance_result = await session.execute(
        select(BalanceORM).where(BalanceORM.user_id == seller_id, BalanceORM.ticker == ticker).with_for_update()
    )
    seller_balance = seller_balance_result.scalar_one_or_none()

    if seller_balance is None:
        raise HTTPException(status_code=404, detail=f"Баланс {ticker} продавца не найден")
    
    if not isMarket:
        buyer_balance_RUB.reserved = max(buyer_balance_RUB.reserved - rub_amount, 0)
        seller_balance.reserved = max(seller_balance.reserved - amount, 0)

async def increase_balance(session: AsyncSession, user_id: UUID, ticker: str, amount: int):
    stmt = (
        insert(BalanceORM)
        .values(user_id=user_id, ticker=ticker, amount=amount, reserved=0)
        .on_conflict_do_update(
            index_elements=["user_id", "ticker"],
            set_={"amount": BalanceORM.amount + amount}
        )
    )
    await session.execute(stmt)

async def decrease_balance(session: AsyncSession, user_id: UUID, ticker: str, amount: int):
    result = await session.execute(
        select(BalanceORM).where(BalanceORM.user_id == user_id, BalanceORM.ticker == ticker).with_for_update()
    )
    balance = result.scalar_one_or_none()
    if balance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Инструмент у пользователя не найден")
    if balance.amount < amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недостаточно средств на балансе")
    
    balance.amount -= amount

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
    result = await session.execute(
        select(BalanceORM).where(
            BalanceORM.user_id == user_id,
            BalanceORM.ticker == ticker
        ).with_for_update()
    )
    balance = result.scalar_one_or_none()
    if not balance:
        raise HTTPException(status_code=404, detail=f"Баланс {ticker} не найден")
    return balance

async def release_user_reserve(session: AsyncSession, user_id: UUID, ticker: str):
    """
    Снимает весь резерв (reserved = 0) у пользователя по указанному активу (тикеру).
    """
    balance_result = await session.execute(
        select(BalanceORM).where(BalanceORM.user_id == user_id, BalanceORM.ticker == ticker).with_for_update()
    )
    balance = balance_result.scalar_one_or_none()

    if balance is None:
        raise HTTPException(status_code=404, detail=f"Баланс {ticker} пользователя {user_id} не найден")

    balance.reserved = 0