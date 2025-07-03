# app/routers/user.py

from fastapi import APIRouter, HTTPException, status
from ..models.user import UserCreate, UserInDB
from ..db.mongodb import database
from ..core.security import get_password_hash
from decimal import Decimal

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """
    Registra um novo usuário no sistema.
    - Verifica se o e-mail já existe.
    - Hashea a senha antes de salvar.
    - Cria uma conta padrão ("Conta Principal") para o novo usuário.
    """
    # 1. Verifica se o usuário já existe
    existing_user = await database["users"].find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuário com este e-mail já existe."
        )

    # 2. Cria o novo usuário
    hashed_password = get_password_hash(user_data.password)
    new_user_data = {
        "name": user_data.name,
        "email": user_data.email,
        "hashed_password": hashed_password
    }
    result = await database["users"].insert_one(new_user_data)
    created_user = await database["users"].find_one({"_id": result.inserted_id})

    if not created_user:
        # Se, por algum motivo, o usuário não foi criado, lançamos um erro.
        raise HTTPException(status_code=500, detail="Erro ao criar o usuário.")

    # 3. Cria a conta padrão para o usuário recém-criado
    default_account = {
        "user_id": created_user["_id"],  # Associa a conta ao ID do novo usuário
        "name": "Conta Principal",
        "type": "checking",
        "balance": Decimal("0.0")
    }
    await database["accounts"].insert_one(default_account)

    # 4. Retorna os dados do usuário criado
    return created_user