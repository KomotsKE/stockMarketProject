from fastapi import Depends, HTTPException, Header , status, APIRouter
import jwt


from src.config import settings

from src.auth.schemas.user import User, NewUser
from src.auth.models.user import UserORM
from src.dataBase.session import async_session_factory

import uuid

auth_router = APIRouter(prefix='/api/v1')

@auth_router.post('/register')
async def user_registration(newUser: NewUser) -> User:
    token = jwt.encode(payload={"name": newUser.name}, key=settings.SECRET_JWT_KEY, algorithm='HS256')
    user = UserORM(id=uuid.uuid4(),name=newUser.name, role='user', api_key = token)
    async with async_session_factory() as session:
        session.add(user)
        await session.commit()
    return User(id=user.id, name=user.name, role=user.role, api_key=user.api_key)



# user_tokens = {
#     '0fas123124s0afsd0fg0212orwsaf12': 'lopast',
#     'f212e23tgqegw1324t354tre431fwrr': 'kopost'
# }

# def get_user_by_token(token : str = Header(alias='auth_token')) -> str:
#     if token := user_tokens.get(token):
#         return token
#     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='token invalid')

# @auth_router.get('/auth/')
# def auth_http_heade(username: str = Depends(get_user_by_token)):
#     return {
#         'message' : f"HI, {username}"
#     }

