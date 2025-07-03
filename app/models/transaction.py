# app/models/transaction.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from decimal import Decimal
from datetime import datetime
from .pyobjectid import PyObjectId
from bson import ObjectId

class InstallmentDetails(BaseModel):
    current_installment: int
    total_installments: int

class TransactionBase(BaseModel):
    description: str
    value: Decimal = Field(gt=0)
    transaction_date: datetime
    # MUDANÇA 1: O campo de categoria foi renomeado para refletir que é um ID.
    category_id: PyObjectId
    notes: Optional[str] = None

class TransactionCreate(TransactionBase):
    type: Literal["income", "expense"]
    account_id: PyObjectId
    status: Literal["pending", "paid", "received"]
    expense_type: Optional[Literal["fixed", "variable"]] = None
    installment_details: Optional[InstallmentDetails] = None

class TransactionUpdate(BaseModel):
    description: Optional[str] = None
    value: Optional[Decimal] = Field(default=None, gt=0)
    transaction_date: Optional[datetime] = None
    # MUDANÇA 2: O campo de atualização também foi renomeado.
    category_id: Optional[PyObjectId] = None
    notes: Optional[str] = None
    status: Optional[Literal["pending", "paid", "received"]] = None
    expense_type: Optional[Literal["fixed", "variable"]] = None
    installment_details: Optional[InstallmentDetails] = None

class TransactionInDB(TransactionBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    account_id: PyObjectId
    type: Literal["income", "expense"]
    status: Literal["pending", "paid", "received"]
    expense_type: Optional[Literal["fixed", "variable"]]
    installment_details: Optional[InstallmentDetails]

    class Config:
        from_attributes = True
        validate_by_name = True
        json_encoders = {ObjectId: str}