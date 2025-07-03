# app/models/report.py
from pydantic import BaseModel
from decimal import Decimal
from typing import List

class CategoryExpense(BaseModel):
    category: str
    total_value: Decimal

class CategoryExpenseReport(BaseModel):
    report: List[CategoryExpense]

class MonthlySummary(BaseModel):
    """Representa o resumo de um único mês."""
    year: int
    month: int
    total_income: Decimal
    total_expenses: Decimal