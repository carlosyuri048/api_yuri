# app/routers/account.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List
from bson import ObjectId
from decimal import Decimal

from ..models.user import UserInDB
# Importe os modelos de criação e atualização que já temos
from ..models.account import AccountInDB, ShareRequest, AccountCreate, AccountUpdate
from ..models.account_sumary import AccountSummary
from ..db.mongodb import database
from ..routers.authentication import get_current_active_user

router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"]
)

# --- ROTA 1: CRIAR UMA NOVA CONTA ---
@router.post("/", response_model=AccountInDB, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Cria uma nova conta (banco, carteira, etc.) para o usuário logado."""
    account_dict = account_data.dict()
    account_dict["user_id"] = current_user.id
    # Garante que o saldo inicial seja um Decimal
    account_dict["balance"] = Decimal(account_data.balance)
    
    result = await database["accounts"].insert_one(account_dict)
    created_account = await database["accounts"].find_one({"_id": result.inserted_id})
    
    return created_account

# --- ROTA 2: LISTAR TODAS AS CONTAS DO USUÁRIO ---
# Esta rota já existia, mas a mantemos aqui na ordem lógica.
@router.get("/", response_model=List[AccountInDB])
async def list_user_accounts(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Lista todas as contas que o usuário possui (não inclui contas compartilhadas com ele)."""
    cursor = database["accounts"].find({"user_id": current_user.id})
    accounts = await cursor.to_list(length=100)
    return accounts

# --- ROTA 3: ATUALIZAR UMA CONTA ---
@router.put("/{id}", response_model=AccountInDB)
async def update_account(
    id: str,
    account_data: AccountUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Atualiza os detalhes de uma conta (nome, tipo, saldo inicial)."""
    try:
        account_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de conta inválido")

    # Apenas o dono da conta pode atualizá-la
    account_doc = await database["accounts"].find_one({"_id": account_id, "user_id": current_user.id})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Conta não encontrada ou acesso não permitido")

    update_data = account_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    updated_account = await database["accounts"].find_one_and_update(
        {"_id": account_id},
        {"$set": update_data},
        return_document=True # pymongo.ReturnDocument.AFTER
    )
    return updated_account

# --- ROTA 4: DELETAR UMA CONTA ---
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Deleta uma conta, mas apenas se não houver transações associadas a ela."""
    try:
        account_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de conta inválido")

    # Apenas o dono da conta pode deletá-la
    account_doc = await database["accounts"].find_one({"_id": account_id, "user_id": current_user.id})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Conta não encontrada ou acesso não permitido")

    # REGRA DE NEGÓCIO: Não permitir deletar contas com transações
    transaction_count = await database["transactions"].count_documents({"account_id": account_id})
    if transaction_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível deletar a conta, pois ela possui {transaction_count} transações associadas."
        )

    await database["accounts"].delete_one({"_id": account_id})
    return

# --- ROTAS EXISTENTES (Resumo e Compartilhamento) ---
# Mantemos as rotas que já tínhamos para resumo e compartilhamento.

@router.get("/{id}/summary", response_model=AccountSummary)
async def get_account_summary(
    id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    # ... (código existente da função, sem alterações)
    try:
        account_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de conta inválido")
    account_doc = await database["accounts"].find_one({"_id": account_id})
    if not account_doc:
        raise HTTPException(status_code=404, detail=f"Conta com id {id} não encontrada")
    is_owner = account_doc["user_id"] == current_user.id
    shared_users = account_doc.get("permissions", [])
    has_permission = any(perm["user_id"] == current_user.id for perm in shared_users)
    if not is_owner and not has_permission:
        raise HTTPException(status_code=403, detail="Acesso não autorizado a esta conta")
    account = AccountInDB(**account_doc)
    pipeline = [
        {"$match": { "account_id": account.id }},
        {"$group": {"_id": "$type", "total": {"$sum": "$value"}}}
    ]
    totals_cursor = database["transactions"].aggregate(pipeline)
    totals = {"income": Decimal("0.0"), "expense": Decimal("0.0")}
    async for doc in totals_cursor:
        if doc["_id"] in totals:
            totals[doc["_id"]] = doc["total"]
    current_balance = (account.balance + totals["income"]) - totals["expense"]
    return AccountSummary(
        name=account.name,
        type=account.type,
        balance=account.balance,
        total_income=totals["income"],
        total_expenses=totals["expense"],
        current_balance=current_balance
    )


@router.post("/{id}/share", status_code=status.HTTP_200_OK)
async def share_account(
    id: str,
    share_request: ShareRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    # ... (código existente da função, sem alterações)
    try:
        account_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de conta inválido")
    account_doc = await database["accounts"].find_one({"_id": account_id})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if account_doc["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o dono pode compartilhar a conta")
    user_to_share_with = await database["users"].find_one({"email": share_request.user_email})
    if not user_to_share_with:
        raise HTTPException(status_code=404, detail=f"Usuário com e-mail {share_request.user_email} não encontrado")
    new_permission = {
        "user_id": user_to_share_with["_id"],
        "permission_level": share_request.permission_level.value
    }
    await database["accounts"].update_one(
        {"_id": account_id},
        {"$pull": {"permissions": {"user_id": user_to_share_with["_id"]}}}
    )
    await database["accounts"].update_one(
        {"_id": account_id},
        {"$push": {"permissions": new_permission}}
    )
    return {"message": f"Conta compartilhada com {share_request.user_email} com permissão de '{share_request.permission_level.value}'."}