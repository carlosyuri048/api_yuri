# app/models/account.py

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal, List
from decimal import Decimal
from enum import Enum
from .pyobjectid import PyObjectId
from bson import ObjectId

class AccountBase(BaseModel):
    name: str
    type: Literal["checking", "savings", "credit_card", "wallet"]
    balance: Decimal = Field(default=0.0)

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[Literal["checking", "savings", "credit_card", "wallet"]] = None
    balance: Optional[Decimal] = None

# --- NOVOS MODELOS ADICIONADOS ---

class PermissionLevel(str, Enum):
    """Define os níveis de permissão possíveis."""
    READ = "read"
    EDIT = "edit"

class SharePermission(BaseModel):
    """Representa uma única permissão dentro do documento da conta."""
    user_id: PyObjectId
    permission_level: PermissionLevel

class ShareRequest(BaseModel):
    """Modelo para a requisição de compartilhamento de conta."""
    user_email: EmailStr
    permission_level: PermissionLevel

# --- MODELO AccountInDB ATUALIZADO ---

class AccountInDB(AccountBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    permissions: Optional[List[SharePermission]] = [] # Campo de permissões adicionado

    class Config:
        from_attributes = True
        validate_by_name = True
        json_encoders = {ObjectId: str}

class AccountUpdate(BaseModel):
    # Permitimos apenas a atualização do nome e do tipo.
    # O saldo não deve ser editado diretamente.
    name: Optional[str] = None
    type: Optional[Literal["checking", "savings", "credit_card", "wallet"]] = None