# app/routers/category.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List
from bson import ObjectId

from ..models.user import UserInDB
from ..models.category import CategoryCreate, CategoryInDB, CategoryUpdate
from ..db.mongodb import database
from ..routers.authentication import get_current_active_user

router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)

@router.post("/", response_model=CategoryInDB, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Cria uma nova categoria para o usuário logado."""
    # Verifica se uma categoria com o mesmo nome já existe para este usuário
    existing_category = await database["categories"].find_one(
        {"name": category_data.name, "user_id": current_user.id}
    )
    if existing_category:
        raise HTTPException(
            status_code=400,
            detail="Uma categoria com este nome já existe."
        )

    category_dict = category_data.dict()
    category_dict["user_id"] = current_user.id
    
    result = await database["categories"].insert_one(category_dict)
    created_category = await database["categories"].find_one({"_id": result.inserted_id})
    
    return created_category


@router.get("/", response_model=List[CategoryInDB])
async def list_user_categories(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Lista todas as categorias criadas pelo usuário logado."""
    cursor = database["categories"].find({"user_id": current_user.id})
    categories = await cursor.to_list(length=100)
    return categories


@router.put("/{id}", response_model=CategoryInDB)
async def update_category(
    id: str,
    category_data: CategoryUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Atualiza o nome ou ícone de uma categoria."""
    try:
        category_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de categoria inválido")

    # Apenas o dono pode atualizar
    category_doc = await database["categories"].find_one({"_id": category_id, "user_id": current_user.id})
    if not category_doc:
        raise HTTPException(status_code=404, detail="Categoria não encontrada ou acesso não permitido")

    update_data = category_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    updated_category = await database["categories"].find_one_and_update(
        {"_id": category_id},
        {"$set": update_data},
        return_document=True # pymongo.ReturnDocument.AFTER
    )
    return updated_category


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """Deleta uma categoria, mas apenas se não estiver em uso."""
    try:
        category_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de categoria inválido")

    category_doc = await database["categories"].find_one({"_id": category_id, "user_id": current_user.id})
    if not category_doc:
        raise HTTPException(status_code=404, detail="Categoria não encontrada ou acesso não permitido")

    # REGRA DE NEGÓCIO: Não permitir deletar categorias em uso
    # Nota: Isso verifica o campo de texto 'category'. O ideal seria refatorar para usar 'category_id'.
    transaction_count = await database["transactions"].count_documents(
        {"category": category_doc["name"], "user_id": current_user.id}
    )
    if transaction_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível deletar a categoria, pois ela está sendo usada em {transaction_count} transações."
        )

    await database["categories"].delete_one({"_id": category_id})
    return