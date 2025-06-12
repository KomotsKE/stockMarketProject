from fastapi import Depends, HTTPException, status, APIRouter
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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

async def validate_user_ticker(session: AsyncSession, user_id: UUID, ticker : TickerStr) -> None:
    user = await session.get(UserORM, user_id)
    if user is None: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    instrument = await session.get(InstrumentORM, ticker)
    if instrument is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Инструмент '{ticker}'не найден")


@balance_router.get("/balance", tags=["balance"])
async def get_balances(user: User = Depends(get_user_by_token)) -> Dict[str, int]:
    user_balance : Dict[str, int] = {}
    ticker_to_name : Dict[str, str] = {}
    async with async_session_factory() as session:
        instruments = await get_instruments_list()
        
        for name, ticker in instruments:
            ticker_to_name[ticker] = name
            user_balance[name] = 0
        balances_result = await session.execute(select(BalanceORM.ticker, BalanceORM.amount).where(BalanceORM.user_id == user.id))
        balances = balances_result.all()
        for ticker, amount in balances:
            user_balance[ticker_to_name[ticker]] = amount
    return user_balance


@balance_router.post("/admin/balance/deposit", tags=["admin","balance"])
async def deposit(transaction: BalanceTransaction, rights: None = Depends(is_admin)) -> OK:
    async with async_session_factory() as session:
        balance = await get_user_balance(session, transaction.user_id, transaction.ticker)
        await increase_balance(session, balance, amount=transaction.amount, ticker=transaction.ticker, user_id=transaction.user_id)
        await session.commit()
    return succesMessage


@balance_router.post("/admin/balance/withdraw", tags=["admin","balance"])
async def withdraw(transaction: BalanceTransaction, rights: None = Depends(is_admin)) -> OK:
    async with async_session_factory() as session:
        balance = await get_user_balance(session, transaction.user_id, transaction.ticker)
        await decrease_balance(session, balance, amount=transaction.amount)
        await session.commit()
    return succesMessage


async def get_user_balance(session : AsyncSession, user_id : UUID, ticker: TickerStr) -> BalanceORM | None:
    await validate_user_ticker(session, user_id, ticker)
    result = await session.execute(select(BalanceORM)
                                    .where(BalanceORM.user_id == user_id, 
                                    BalanceORM.ticker == ticker))
    balance = result.scalar_one_or_none()
    return balance


async def update_balances(session: AsyncSession, buyer_id: UUID, seller_id: UUID, orderTransaction: TransactionORM, isMarket: bool = False):
    buyer_balance = await get_user_balance(session, buyer_id, orderTransaction.ticker)
    seller_balance = await get_user_balance(session, seller_id, orderTransaction.ticker)

    await increase_balance(session, buyer_balance, amount=orderTransaction.amount, ticker=orderTransaction.ticker, user_id=buyer_id)
    await decrease_balance(session, seller_balance, amount=orderTransaction.amount)

    buyer_balance_RUB = await get_user_balance(session, buyer_id, "RUB")
    seller_balance_RUB = await get_user_balance(session, seller_id, "RUB")

    rub_amount = orderTransaction.amount * orderTransaction.price

    await decrease_balance(session, buyer_balance_RUB, amount=rub_amount)
    await increase_balance(session, seller_balance_RUB, amount=rub_amount, ticker=orderTransaction.ticker, user_id=seller_id)

    if not isMarket:
        buyer_balance_RUB.reserved -= rub_amount
    seller_balance.reserved -= orderTransaction.amount


async def increase_balance(session: AsyncSession, balance: BalanceORM | None, ticker: TickerStr, user_id: UUID, amount: AmountInt):
    if balance is None:
        session.add(BalanceORM(user_id = user_id, ticker=ticker, amount=amount))
    else:
        balance.amount += amount


async def decrease_balance(session: AsyncSession, balance: BalanceORM | None, amount: AmountInt):
    if balance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Инструмент у пользователя не найден")
    elif balance.amount < amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недостаточно средств на балансе")
    balance.amount -= amount
    if balance.amount == 0:
        await session.delete(balance)

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
        balance = await get_user_balance(session, user_id, "RUB")
        if balance is None or balance.amount - balance.reserved < rub_needed:
            raise HTTPException(status_code=400, detail="Недостаточно средств для резервации RUB")
        balance.reserved += rub_needed

    elif direction == OperationDirection.SELL:
        asset_balance = await get_user_balance(session, user_id, ticker)
        if asset_balance is None or asset_balance.amount - asset_balance.reserved < qty:
            raise HTTPException(status_code=400, detail=f"Недостаточно {ticker} для резервации")
        asset_balance.reserved += qty