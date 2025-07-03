# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # <--- 1. IMPORTE O MIDDLEWARE

# Importa todos os seus routers
from .routers import transaction, user, authentication, dashboard, account, report, category

# Cria a instância da aplicação FastAPI
app = FastAPI(
    title="Financial App API",
    description="API para o seu aplicativo de controle financeiro.",
    version="0.1.0"
)

# --- 2. CONFIGURAÇÃO DO CORS ---

# Lista de origens permitidas (seu frontend)
# Para desenvolvimento, adicionamos os endereços do localhost.
# Quando você implantar seu frontend, deverá adicionar o domínio dele aqui.
origins = [
    "http://localhost",
    "http://localhost:8080", # Porta comum para desenvolvimento frontend
    "http://localhost:8000", # Se o frontend e backend rodarem na mesma porta
    # "https://seu-dominio-frontend.com", # Exemplo de domínio em produção
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Permite cookies e cabeçalhos de autorização
    allow_methods=["*"],    # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"],    # Permite todos os cabeçalhos
)
# --- FIM DA CONFIGURAÇÃO DO CORS ---


# Rota raiz para um teste rápido
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Bem-vindo à API do seu App Financeiro!"}

# Inclui os routers na aplicação
app.include_router(transaction.router)
app.include_router(user.router)
app.include_router(authentication.router)
app.include_router(dashboard.router)
app.include_router(account.router)
app.include_router(report.router)
app.include_router(category.router)