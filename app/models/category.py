# app/models/category.py
from pydantic import BaseModel, Field
from typing import Optional
from .pyobjectid import PyObjectId
from bson import ObjectId

class CategoryBase(BaseModel):
    name: str
    icon: Optional[str] = None # Campo opcional para o nome do ícone no frontend

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None

class CategoryInDB(CategoryBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId

    class Config:
        from_attributes = True
        validate_by_name = True
        json_encoders = {ObjectId: str}