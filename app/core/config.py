# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Variáveis que já tínhamos
    MONGO_URL: str
    DATABASE_NAME: str

    # Adicione esta linha para a chave secreta da autenticação
    SECRET_KEY: str

    # Define o arquivo de onde carregar as variáveis (.env)
    model_config = SettingsConfigDict(env_file=".env")

# Cria uma instância das configurações que será usada em toda a aplicação
settings = Settings()