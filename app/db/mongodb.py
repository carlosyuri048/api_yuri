# app/db/mongodb.py

import motor.motor_asyncio
from ..core.config import settings
from decimal import Decimal
from bson.decimal128 import Decimal128
from bson.codec_options import TypeCodec, TypeRegistry, CodecOptions

# --- A classe do tradutor de Decimal continua a mesma ---

class DecimalCodec(TypeCodec):
    """
    Codec para converter entre Decimal do Python e Decimal128 do BSON.
    """
    @property
    def python_type(self):
        return Decimal

    @property
    def bson_type(self):
        return Decimal128

    def transform_python(self, value: Decimal) -> Decimal128:
        return Decimal128(value)

    def transform_bson(self, value: Decimal128) -> Decimal:
        return value.to_decimal()

# --- A lógica de criação do codec também continua a mesma ---

decimal_codec = DecimalCodec()
type_registry = TypeRegistry([decimal_codec])
codec_options = CodecOptions(type_registry=type_registry)


# --- A MUDANÇA ESTÁ AQUI ---

# 1. Crie o cliente de forma simples, SEM as opções de codec
client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URL)

# 2. Selecione o banco de dados e APLIQUE AS OPÇÕES DE CODEC AQUI
#    Este método é mais estável e compatível entre versões.
database = client.get_database(
    settings.DATABASE_NAME,
    codec_options=codec_options
)