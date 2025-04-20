from src.stockMarket.schemas.instrument import Instrument
from src.stockMarket.models.instrument import InstrumentORM
from src.profile.api.user import is_admin
from src.dataBase.session import async_session_factory
from sqlalchemy import select
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from src.public.schemas import succesMessage, OK


instrument_router = APIRouter(prefix="/api/v1")

@instrument_router.get("/public/instrument", tags=["public"])
async def get_instruments_list() -> List[Instrument]:
    async with async_session_factory() as session:
        result = await session.execute(select(InstrumentORM.name, InstrumentORM.ticker))
        return result.all()

@instrument_router.post("/admin/instrument", tags=["admin"])
async def add_instrument(instrument : Instrument, rights: None = Depends(is_admin)) -> OK:
    newInstrument = InstrumentORM(name=instrument.name, ticker=instrument.ticker)
    async with async_session_factory() as session:
        session.add(newInstrument)
        await session.commit()
        return succesMessage

@instrument_router.delete("/admin/instrument/{ticker}", tags=["admin"])
async def del_instrument(ticker : str, rights: None = Depends(is_admin)) -> OK:
    async with async_session_factory() as session:
        result = await session.execute(select(InstrumentORM).filter(InstrumentORM.ticker == ticker))
        instrument = result.scalar_one_or_none()
        if instrument is None:
            raise HTTPException(status_code=404, detail="Instrument not found")
        await session.delete(instrument)
        await session.commit()
        return succesMessage
