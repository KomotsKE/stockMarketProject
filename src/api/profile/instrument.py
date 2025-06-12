from src.schemas.instrument import Instrument, Transaction, TickerStr, LimitInt
from src.dataBase.models.instrument import InstrumentORM
from src.api.profile.user import is_admin
from src.dataBase.session import async_session_factory
from sqlalchemy import select
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from src.schemas.schemas import succesMessage, OK
from src.dataBase.models.balance import TransactionORM


instrument_router = APIRouter(prefix="/api/v1")

@instrument_router.get("/public/instrument", tags=["public"])
async def get_instruments_list() -> List[Instrument]:
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(InstrumentORM.name, InstrumentORM.ticker))
            return result.all()
    except Exception as e:
        raise e

@instrument_router.post("/admin/instrument", tags=["admin"])
async def add_instrument(instrument : Instrument, rights: None = Depends(is_admin)) -> OK:
    try: 
        newInstrument = InstrumentORM(name=instrument.name, ticker=instrument.ticker)
        async with async_session_factory() as session:
            session.add(newInstrument)
            await session.commit()
            return succesMessage
    except Exception as e:
        raise e

@instrument_router.delete("/admin/instrument/{ticker}", tags=["admin"])
async def del_instrument(ticker : TickerStr, rights: None = Depends(is_admin)) -> OK:
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(InstrumentORM).filter(InstrumentORM.ticker == ticker))
            instrument = result.scalar_one_or_none()
            if instrument is None:
                raise HTTPException(status_code=404, detail="Instrument not found")
            await session.delete(instrument)
            await session.commit()
            return succesMessage
    except Exception as e:
        raise e

@instrument_router.get("/public/transaction/{ticker}", tags=["public"])
async def get_transaction_history(ticker : TickerStr, limit : LimitInt) -> List[Transaction]:
    try:
        async with async_session_factory() as session:
            query = select(TransactionORM).where(TransactionORM.ticker == ticker).order_by(TransactionORM.timestamp).limit(limit)
            result = await session.execute(query)
            transactions = result.scalars().all()
            return transactions
    except Exception as e:
        raise e
