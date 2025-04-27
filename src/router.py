from fastapi import APIRouter
from src.profile.api.user import auth_router
from src.stockMarket.api.instrument import instrument_router
from src.profile.api.balance import balance_router
from src.stockMarket.api.order import order_router
from src.stockMarket.api.market_order import market_order_router
from src.stockMarket.api.limit_order import limit_order_router

main_router = APIRouter()

main_router.include_router(auth_router)
main_router.include_router(instrument_router)
main_router.include_router(balance_router)
main_router.include_router(order_router)
main_router.include_router(market_order_router)
main_router.include_router(limit_order_router)