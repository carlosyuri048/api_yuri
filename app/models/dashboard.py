# app/models/dashboard.py
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional

class TopCategory(BaseModel):
    category: str
    total_value: Decimal

class DashboardSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    balance: Decimal
    top_expense_category: Optional[TopCategory] = None