# app/routers/authentication.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Annotated
from datetime import timedelta
from jose import JWTError, jwt

from ..models.user import UserInDB
from ..models.token import Token, AccessTokenResponse
from ..core.security import verify_password, create_access_token, REFRESH_TOKEN_EXPIRE_MINUTES, ALGORITHM
from ..core.config import settings
from ..db.mongodb import database

router = APIRouter(
    tags=["Authentication"]
)

# Este esquema é usado pelo FastAPI para gerar a documentação e extrair o token do cabeçalho
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Função de dependência que valida o token (access ou refresh) e retorna o usuário
async def get_current_active_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    """
    Dependência para obter o usuário atual a partir de um token JWT.
    Valida a assinatura, o tempo de expiração e se o usuário existe.
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


# Função auxiliar que verifica email e senha no banco de dados
async def authenticate_user(email: str, password: str) -> UserInDB | bool:
    """
    Busca o usuário pelo e-mail e verifica se a senha corresponde.
    """
    user_doc = await database["users"].find_one({"email": email})
    if not user_doc:
        return False
    
    user = UserInDB(**user_doc)
    if not verify_password(password, user.hashed_password):
        return False
    
    return user


# Rota principal de login
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """
    Endpoint de login. Recebe e-mail (no campo username) e senha.
    Retorna um access_token (curta duração) e um refresh_token (longa duração).
    """
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_access_token(
        data={"sub": user.email}, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token, 
        "token_type": "bearer"
    }


# Rota para renovar o token de acesso
@router.post("/token/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """
    Gera um novo access token a partir de um refresh token válido.
    Para testar na documentação, use o refresh_token no botão 'Authorize'.
    """
    # A dependência 'get_current_active_user' já fez todo o trabalho de validar
    # o refresh token e nos retornar o usuário. Se chegamos até aqui, está tudo certo.
    # Agora, apenas precisamos gerar um novo access token de curta duração.
    new_access_token = create_access_token(data={"sub": current_user.email})
    
    return {"access_token": new_access_token}