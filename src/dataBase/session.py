from src.config import settings
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

#-----------------------------------------------------------------------------------------------------------------#
#                                                 Sync                                                            #
#-----------------------------------------------------------------------------------------------------------------#

sync_engine = create_engine(
    url=settings.DATABASE_URL_PSYCOPG,
    echo=False,
)

#-----------------------------------------------------------------------------------------------------------------#
#                                                Async                                                            #
#-----------------------------------------------------------------------------------------------------------------#

async_engine = create_async_engine(
    url = settings.DATABASE_URL_PSYCOPG,
    echo = False
)

#-----------------------------------------------------------------------------------------------------------------#

async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
session_factory = sessionmaker(sync_engine)