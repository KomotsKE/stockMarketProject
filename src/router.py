from fastapi import APIRouter
from src.api.profile.user import auth_router
from src.api.profile.instrument import instrument_router
from src.api.profile.balance import balance_router
from src.api.stockMarket.order import order_router

main_router = APIRouter()

main_router.include_router(auth_router)
main_router.include_router(instrument_router)
main_router.include_router(balance_router)
main_router.include_router(order_router)