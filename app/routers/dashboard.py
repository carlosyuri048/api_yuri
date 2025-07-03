# app/routers/dashboard.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from datetime import datetime

from ..models.user import UserInDB
from ..models.dashboard import DashboardSummary, TopCategory
from ..db.mongodb import database
from ..routers.authentication import get_current_active_user
from decimal import Decimal

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    year: int,
    month: int,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """
    Retorna um resumo financeiro para o mês e ano especificados.
    """
    start_date = datetime(year, month, 1)
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    end_date = datetime(next_year, next_month, 1)

    pipeline_totals = [
        {"$match": {"user_id": current_user.id, "transaction_date": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": "$type", "total_value": {"$sum": "$value"}}}
    ]
    
    pipeline_top_category = [
        {"$match": {"user_id": current_user.id, "type": "expense", "transaction_date": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": "$category", "total_value": {"$sum": "$value"}}},
        {"$sort": {"total_value": -1}},
        {"$limit": 1}
    ]

    totals_cursor = database["transactions"].aggregate(pipeline_totals)
    top_category_cursor = database["transactions"].aggregate(pipeline_top_category)

    summary_data = {"income": Decimal("0.0"), "expense": Decimal("0.0")}
    async for doc in totals_cursor:
        summary_data[doc['_id']] = doc['total_value']

    top_category_doc = await top_category_cursor.to_list(length=1)
    
    top_expense = None
    if top_category_doc:
        top_expense = TopCategory(
            category=top_category_doc[0]['_id'],
            total_value=top_category_doc[0]['total_value']
        )
        
    total_income = summary_data['income']
    total_expenses = summary_data['expense']
    balance = total_income - total_expenses
    
    return DashboardSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance,
        top_expense_category=top_expense
    )

# --- NOVA ROTA ADICIONADA ---
@router.delete("/transactions/{year}", status_code=200)
async def delete_transactions_by_year(
    year: int,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """
    DELETA permanentemente todas as transações de um determinado ano.
    Esta é uma ação DESTRUTIVA e IRREVERSÍVEL.
    """
    # Define o período do ano a ser deletado
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)

    # Define o filtro para a operação de exclusão
    query = {
        "user_id": current_user.id,
        "transaction_date": {"$gte": start_date, "$lt": end_date}
    }

    # Executa a exclusão em massa
    delete_result = await database["transactions"].delete_many(query)

    # Retorna uma confirmação com o número de documentos deletados
    return {
        "message": f"{delete_result.deleted_count} transações do ano {year} foram deletadas com sucesso."
    }