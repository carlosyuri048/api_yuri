# app/models/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from .pyobjectid import PyObjectId
from bson import ObjectId

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str

    class Config:
        from_attributes = True
        validate_by_name = True
        json_encoders = {ObjectId: str}