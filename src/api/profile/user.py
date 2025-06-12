import jwt
import uuid
from sqlalchemy import select
from fastapi import Depends, HTTPException, Header , status, APIRouter
from src.config import settings
from src.schemas.user import User, NewUser, Role
from src.dataBase.models.user import UserORM
from src.dataBase.session import async_session_factory
from typing import Optional



auth_router = APIRouter(prefix='/api/v1')


async def get_user_by_token(token: Optional[str] = Header(alias="authorization")) -> User:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")

    if not token.startswith("TOKEN "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")

    token = token.split(" ", 1)[1]
    async with async_session_factory() as session:
        result = await session.execute(select(UserORM).filter(UserORM.api_key == token))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='token invalid')
        return User(id=user.id, name=user.name, role=user.role, api_key=user.api_key)


async def is_admin(user: User = Depends(get_user_by_token)) -> None:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not enough rights')


@auth_router.post('/public/register', tags=["public"])
async def register_user(newUser: NewUser) -> User:
    token = jwt.encode(payload={"name": newUser.name}, key=settings.SECRET_JWT_KEY, algorithm='HS256')
    user = UserORM(id=uuid.uuid4(),name=newUser.name, role=newUser.role, api_key = token)
    async with async_session_factory() as session:
        session.add(user)
        await session.commit()
    return User(id=user.id, name=user.name, role=user.role, api_key=user.api_key)


@auth_router.delete('/admin/user/{user_id}', tags=["admin", "user"])
async def delete_user(user_id : uuid.UUID, token : str = Depends(is_admin)) -> User:
    async with async_session_factory() as session:
        result = await session.execute(select(UserORM).filter(UserORM.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        await session.delete(user)
        await session.commit()
    return User(id=user.id, name = user.name, role = user.role, api_key=user.api_key)



