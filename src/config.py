from pydantic_settings import BaseSettings, SettingsConfigDict
from redis import Redis

class Settings(BaseSettings):
    POSTGRES_DB_HOST: str
    POSTGRES_DB_PORT: int
    POSTGRES_DB_USER: str
    POSTGRES_DB_PASSWORD: str
    POSTGRES_DB_NAME: str
    SECRET_JWT_KEY: str
    REDIS_HOST: str
    REDIS_USER: str
    REDIS_PASSWORD: str
    REDIS_USER_PASSWORD: str

    @property
    def DATABASE_URL_PSYCOPG(self):
        return f"postgresql+psycopg://{self.POSTGRES_DB_USER}:{self.POSTGRES_DB_PASSWORD}@{self.POSTGRES_DB_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB_NAME}"
    
    @property
    def DATABASE_URL_ASYNCPG(self):
        return f"postgresql+asyncpg://{self.POSTGRES_DB_USER}:{self.POSTGRES_DB_PASSWORD}@{self.POSTGRES_DB_HOST}:{self.POSTGRES_DB_PORT}/{self.POSTGRES_DB_NAME}"
    
    @property 
    def REDIS_DB_CONN(self):
        return Redis(host=self.REDIS_HOST, port=6380, db=0, username=self.REDIS_USER, password=self.REDIS_USER_PASSWORD)

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()