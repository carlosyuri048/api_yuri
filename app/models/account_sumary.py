# app/models/account_summary.py
from pydantic import BaseModel
from decimal import Decimal

from .account import AccountBase # Importamos a base da conta que já temos

class AccountSummary(AccountBase):
    """
    Representa os detalhes de uma conta mais um resumo calculado
    das suas transações.
    """
    total_income: Decimal
    total_expenses: Decimal
    current_balance: Decimal