from fastapi import APIRouter
from src.auth.api.user import auth_router
from src.stockMarket.api.instrument import instrument_router


main_router = APIRouter()

main_router.include_router(auth_router)
main_router.include_router(instrument_router)