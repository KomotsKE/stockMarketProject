
import uvicorn

from fastapi import FastAPI
from src.router import main_router

app = FastAPI(title='stockMarket App')
app.include_router(main_router)