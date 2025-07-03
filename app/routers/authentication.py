# app/routers/authentication.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Annotated
from datetime import timedelta
from jose import JWTError, jwt

from ..models.user import UserInDB
from ..models.token import Token
from ..core.security import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM
from ..core.config import settings
from ..db.mongodb import database

router = APIRouter(
    tags=["Authentication"]
)

# Esta linha cria um "esquema" que diz ao FastAPI:
# "Para se autenticar, espere um token na URL '/token'"
# A documentação usará isso para criar o botão "Authorize".
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_active_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    """
    Dependência para obter o usuário atual a partir de um token JWT.
    
    1. Decodifica o token.
    2. Valida o token (assinatura e expiração).
    3. Busca o usuário no banco de dados.
    4. Retorna o objeto do usuário ou levanta uma exceção.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user_doc = await database["users"].find_one({"email": email})
    if user_doc is None:
        raise credentials_exception
        
    return UserInDB(**user_doc)


async def authenticate_user(email: str, password: str) -> UserInDB | bool:
    """
    Função auxiliar para autenticar um usuário.
    Busca o usuário pelo e-mail e verifica a senha.
    """
    user_doc = await database["users"].find_one({"email": email})
    if not user_doc:
        return False
    
    user = UserInDB(**user_doc)
    if not verify_password(password, user.hashed_password):
        return False
    
    return user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """
    Endpoint de login. Recebe e-mail (no campo username) e senha.
    Retorna um token de acesso JWT se as credenciais forem válidas.
    """
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}