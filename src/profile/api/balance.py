from fastapi import Depends, HTTPException, status, APIRouter
from uuid import UUID
from sqlalchemy import select
from src.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from src.profile.api.user import get_user_by_token, is_admin, UserORM
from src.profile.schemas.user import User
from src.stockMarket.models.instrument import InstrumentORM
from src.stockMarket.api.instrument import get_instruments_list
from src.profile.schemas.balance import BalanceTransaction
from src.profile.models.balance import BalanceORM
from src.dataBase.session import async_session_factory
from src.public.schemas import succesMessage, OK
from typing import Dict

balance_router = APIRouter(prefix='/api/v1')

async def validate_user_ticker(session: AsyncSession, user_id: UUID, ticker : str) -> None:
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

        await validate_user_ticker(session, transaction.user_id, transaction.ticker)

        result = await session.execute(select(BalanceORM)
                                        .where(BalanceORM.user_id == transaction.user_id, 
                                        BalanceORM.ticker == transaction.ticker))
        balance = result.scalar_one_or_none()
        if balance is None:
            session.add(BalanceORM(user_id = transaction.user_id, ticker=transaction.ticker, amount=transaction.amount))
        else:
            balance.amount += transaction.amount
        await session.commit()
    return succesMessage

@balance_router.post("/admin/balance/withdraw", tags=["admin","balance"])
async def withdraw(transaction: BalanceTransaction, rights: None = Depends(is_admin)) -> OK:
    async with async_session_factory() as session:

        await validate_user_ticker(session, transaction.user_id, transaction.ticker)

        result = await session.execute(select(BalanceORM)
                                        .where(BalanceORM.user_id == transaction.user_id, 
                                        BalanceORM.ticker == transaction.ticker))
        balance = result.scalar_one_or_none()
        if balance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Инструмент '{transaction.ticker}' у пользователя не найден")
        elif balance.amount < transaction.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недостаточно средств на балансе")
        balance.amount -= transaction.amount
        if balance.amount == 0:
            await session.delete(balance)
        await session.commit()
    return succesMessage