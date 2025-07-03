# app/models/pyobjectid.py

from bson import ObjectId
from typing import Any
from pydantic_core import core_schema

class PyObjectId(ObjectId):
    """
    Custom Pydantic type for MongoDB's ObjectId, compatible with Pydantic v2.
    """
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        """
        Return the Pydantic v2 CoreSchema for this type.
        This defines how to validate and serialize the data.
        """
        def validate(v: Any) -> ObjectId:
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid ObjectId")
            return ObjectId(v)

        # Defines a schema that accepts a string, validates it as an ObjectId,
        # and serializes ObjectId back to a string.
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.no_info_plain_validator_function(validate)
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )