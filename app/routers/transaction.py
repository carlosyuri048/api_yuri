# app/routers/transaction.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Annotated
from bson import ObjectId
from pymongo import ReturnDocument
from typing import List, Annotated, Optional, Literal # Adicione Optional aqui
from datetime import datetime, date # Adicione date aqui

from ..models.user import UserInDB
from ..models.transaction import TransactionCreate, TransactionInDB, TransactionUpdate
from ..db.mongodb import database
from ..routers.authentication import get_current_active_user

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)

# --- FUNÇÃO AUXILIAR PARA VERIFICAR PERMISSÕES ---
async def _get_and_verify_account_permission(
    account_id: ObjectId, 
    current_user: UserInDB, 
    required_level: str = "read"
):
    """
    Busca uma conta e verifica se o usuário atual tem a permissão necessária.
    Levanta exceções HTTP se a conta não for encontrada ou se não houver permissão.
    required_level pode ser 'read' ou 'edit'.
    """
    account = await database["accounts"].find_one({"_id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="A conta especificada não foi encontrada.")

    is_owner = account["user_id"] == current_user.id
    if is_owner:
        return  # O dono sempre tem todas as permissões

    permissions = account.get("permissions", [])
    user_perms = [p for p in permissions if p["user_id"] == current_user.id]

    if not user_perms:
        raise HTTPException(status_code=403, detail="Você não tem permissão para acessar esta conta.")

    # Se a permissão necessária for de edição, verifica o nível
    if required_level == "edit" and user_perms[0]["permission_level"] != "edit":
        raise HTTPException(status_code=403, detail="Você não tem permissão de edição para esta conta.")
    
    # Se chegou até aqui, o usuário tem pelo menos permissão de leitura.
    return

# --- ROTAS ATUALIZADAS ---

@router.post("/", response_model=TransactionInDB, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Cria uma nova transação, validando a permissão de edição na conta."""
    await _get_and_verify_account_permission(
        transaction_data.account_id, current_user, required_level="edit"
    )
    
    # Valida a categoria
    category = await database["categories"].find_one(
        {"_id": transaction_data.category_id, "user_id": current_user.id}
    )
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    # Usamos model_dump() mas garantimos que os ObjectIds não sejam convertidos para string
    transaction_dict = transaction_data.model_dump()
    transaction_dict["account_id"] = transaction_data.account_id
    transaction_dict["category_id"] = transaction_data.category_id
    transaction_dict["user_id"] = current_user.id
    
    result = await database["transactions"].insert_one(transaction_dict)
    created_transaction = await database["transactions"].find_one({"_id": result.inserted_id})
    
    if created_transaction:
        return created_transaction
    raise HTTPException(status_code=500, detail="Erro ao criar a transação")


@router.get("/", response_model=List[TransactionInDB])
async def list_transactions(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    # --- NOVOS PARÂMETROS DE FILTRO (OPCIONAIS) ---
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    type: Optional[Literal["income", "expense"]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    # --- PARÂMETROS DE PAGINAÇÃO ---
    skip: int = 0,
    limit: int = 100
):
    """
    Lista transações com filtros avançados e paginação.
    - Filtre por conta, categoria, tipo e/ou intervalo de datas.
    """
    # A query base sempre filtra pelo usuário logado
    query = {"user_id": current_user.id}

    # Constrói a query dinamicamente com base nos filtros fornecidos
    if account_id:
        try:
            query["account_id"] = ObjectId(account_id)
        except Exception:
            raise HTTPException(status_code=400, detail="ID de conta inválido.")
            
    if category_id:
        try:
            query["category_id"] = ObjectId(category_id)
        except Exception:
            raise HTTPException(status_code=400, detail="ID de categoria inválido.")

    if type:
        query["type"] = type

    if start_date and end_date:
        query["transaction_date"] = {
            "$gte": datetime.combine(start_date, datetime.min.time()),
            "$lt": datetime.combine(end_date, datetime.max.time())
        }

    # Aplica a ordenação, paginação e executa a busca
    cursor = database["transactions"].find(query).sort("transaction_date", -1).skip(skip).limit(limit)
    
    transactions = await cursor.to_list(length=limit)
    return transactions


@router.get("/{id}", response_model=TransactionInDB)
async def get_transaction_by_id(
    id: str, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Busca uma transação e valida a permissão de leitura na conta associada."""
    try:
        transaction_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de transação inválido")

    transaction = await database["transactions"].find_one({"_id": transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transação com id {id} não encontrada")

    await _get_and_verify_account_permission(transaction["account_id"], current_user, required_level="read")
    
    return transaction


@router.put("/{id}", response_model=TransactionInDB)
async def update_transaction(
    id: str, 
    transaction_data: TransactionUpdate, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Atualiza uma transação, validando a permissão de edição na conta associada."""
    try:
        transaction_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de transação inválido")

    transaction_to_update = await database["transactions"].find_one({"_id": transaction_id})
    if not transaction_to_update:
        raise HTTPException(status_code=404, detail="Transação não encontrada.")
    
    await _get_and_verify_account_permission(
        transaction_to_update["account_id"], current_user, required_level="edit"
    )

    update_data = transaction_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    updated_transaction = await database["transactions"].find_one_and_update(
        {"_id": transaction_id}, {"$set": update_data}, return_document=ReturnDocument.AFTER
    )
    return updated_transaction


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    id: str, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Deleta uma transação, validando a permissão de edição na conta associada."""
    try:
        transaction_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de transação inválido")

    transaction_to_delete = await database["transactions"].find_one({"_id": transaction_id})
    if not transaction_to_delete:
        raise HTTPException(status_code=404, detail="Transação não encontrada.")
        
    await _get_and_verify_account_permission(
        transaction_to_delete["account_id"], current_user, required_level="edit"
    )
        
    await database["transactions"].delete_one({"_id": transaction_id})
    return


@router.post("/{id}/pay-installment", response_model=TransactionInDB)
async def pay_installment(
    id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Paga uma parcela, validando a permissão de edição na conta associada."""
    try:
        transaction_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de transação inválido")

    transaction = await database["transactions"].find_one({"_id": transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    
    await _get_and_verify_account_permission(
        transaction["account_id"], current_user, required_level="edit"
    )

    installments = transaction.get("installment_details")
    if not installments:
        raise HTTPException(status_code=400, detail="Esta não é uma transação parcelada válida.")
        
    if installments["current_installment"] >= installments["total_installments"]:
        raise HTTPException(status_code=400, detail="Todas as parcelas já foram pagas.")

    update_query = {"$inc": {"installment_details.current_installment": 1}}
    if installments["current_installment"] + 1 == installments["total_installments"]:
        update_query["$set"] = {"status": "paid"}
    
    updated_transaction = await database["transactions"].find_one_and_update(
        {"_id": transaction_id}, update_query, return_document=ReturnDocument.AFTER
    )
    
    return updated_transaction