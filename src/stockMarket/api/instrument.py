from src.stockMarket.schemas.instrument import Instrument, OK
from src.stockMarket.models.instrument import InstrumentORM
from src.dataBase.session import async_session_factory
from sqlalchemy import select
from fastapi import APIRouter, HTTPException
from typing import List

instrument_router = APIRouter(prefix="/api/v1")

succesMessage = OK(success=True)

@instrument_router.get("/public/instrument")
async def get_instruments_list() -> List[Instrument]:
    async with async_session_factory() as session:
        result = await session.execute(select(InstrumentORM.name, InstrumentORM.ticker))
        return result.all()

@instrument_router.post("/admin/instrument")
async def add_instrument(instrument : Instrument) -> OK:
    newInstrument = InstrumentORM(name=instrument.name, ticker=instrument.ticker)
    async with async_session_factory() as session:
        session.add(newInstrument)
        await session.commit()
        return succesMessage
    
@instrument_router.delete("/admin/instrument/{ticker}")
async def del_instrument(ticker : str) -> OK:
    async with async_session_factory() as session:
        result = await session.execute(select(InstrumentORM).filter(InstrumentORM.ticker == ticker))
        instrument = result.scalar_one_or_none()
        if instrument is None:
            raise HTTPException(status_code=404, detail="Instrument not found")
        await session.delete(instrument)
        await session.commit()
        return succesMessage
