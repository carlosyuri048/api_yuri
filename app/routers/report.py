# app/routers/report.py
from fastapi import APIRouter, Depends
from typing import Annotated, List
from datetime import datetime, date # Adicione 'date' aqui

from ..models.user import UserInDB
from ..models.report import CategoryExpense, MonthlySummary # Adicione MonthlySummary
from ..db.mongodb import database
from ..routers.authentication import get_current_active_user

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)

# ... (a rota get_expenses_by_category_report continua aqui, sem alterações) ...
@router.get("/expenses-by-category", response_model=List[CategoryExpense])
async def get_expenses_by_category_report(
    year: int,
    month: int,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    # ... (código existente)
    start_date = datetime(year, month, 1)
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    end_date = datetime(next_year, next_month, 1)
    pipeline = [
        {"$match": {"user_id": current_user.id, "type": "expense", "transaction_date": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": "$category", "total_value": {"$sum": "$value"}}},
        {"$project": {"category": "$_id", "total_value": "$total_value", "_id": 0}},
        {"$sort": {"total_value": -1}}
    ]
    report_cursor = database["transactions"].aggregate(pipeline)
    report_data = await report_cursor.to_list(length=None)
    return report_data


# --- NOVA ROTA ADICIONADA ---
@router.get("/income-vs-expenses", response_model=List[MonthlySummary])
async def get_income_vs_expenses_report(
    start_date: date,
    end_date: date,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)]
):
    """
    Gera um relatório de série temporal com o total de entradas e saídas
    para cada mês dentro de um intervalo de datas.
    """
    # Converte as datas para datetime para a query do MongoDB
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    pipeline = [
        # 1. Filtra as transações pelo usuário e pelo intervalo de datas
        {
            "$match": {
                "user_id": current_user.id,
                "transaction_date": {"$gte": start_datetime, "$lt": end_datetime}
            }
        },
        # 2. Agrupa por ano e mês
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$transaction_date"},
                    "month": {"$month": "$transaction_date"}
                },
                # 3. Usa $cond para somar condicionalmente
                "total_income": {
                    "$sum": {
                        "$cond": [{"$eq": ["$type", "income"]}, "$value", 0]
                    }
                },
                "total_expenses": {
                    "$sum": {
                        "$cond": [{"$eq": ["$type", "expense"]}, "$value", 0]
                    }
                }
            }
        },
        # 4. Formata o resultado para bater com nosso modelo Pydantic
        {
            "$project": {
                "year": "$_id.year",
                "month": "$_id.month",
                "total_income": "$total_income",
                "total_expenses": "$total_expenses",
                "_id": 0
            }
        },
        # 5. Ordena cronologicamente
        {
            "$sort": {"year": 1, "month": 1}
        }
    ]
    
    report_cursor = database["transactions"].aggregate(pipeline)
    report_data = await report_cursor.to_list(length=None)

    # O TypeCodec já garante que os totais sejam Decimals
    return report_data