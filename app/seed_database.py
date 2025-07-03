# seed_database.py

import os
import random
from decimal import Decimal
from datetime import datetime, timedelta

import pymongo
from bson import ObjectId
from faker import Faker
from dotenv import load_dotenv

# --- CONFIGURAÇÃO ---
# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# !!! IMPORTANTE: Cole os IDs que você copiou do seu banco de dados aqui !!!
USER_ID = ObjectId("64a0a0a0a0a0a0a0a0a0a0a0")  # <--- COLOQUE O ID DO SEU USUÁRIO
ACCOUNT_ID = ObjectId("64b1b1b1b1b1b1b1b1b1b1b1") # <--- COLOQUE O ID DA SUA CONTA

NUM_TRANSACTIONS = 200 # Número de transações falsas a serem criadas

# Inicializa o Faker para gerar dados em português
fake = Faker('pt_BR')

# --- LÓGICA DO SCRIPT ---

def create_fake_transactions():
    """Conecta ao DB e cria transações falsas."""

    print("Iniciando a criação de transações falsas...")

    try:
        # Usamos pymongo (síncrono) aqui, pois é mais simples para um script
        client = pymongo.MongoClient(MONGO_URL)
        db = client[DATABASE_NAME]
        transactions_collection = db["transactions"]
    except Exception as e:
        print(f"Erro ao conectar ao MongoDB: {e}")
        return

    transactions_to_insert = []
    for i in range(NUM_TRANSACTIONS):
        print(f"Gerando transação {i + 1}/{NUM_TRANSACTIONS}...")

        # Decide aleatoriamente se é uma entrada ou saída
        trans_type = random.choices(["income", "expense"], weights=[0.2, 0.8], k=1)[0]

        if trans_type == "income":
            category = random.choice(["Salário", "Freelance", "Vendas", "Rendimentos"])
            value = Decimal(random.uniform(500.0, 7000.0)).quantize(Decimal("0.01"))
            status = "received"
            expense_type = None
        else: # expense
            category = random.choice(["Alimentação", "Transporte", "Moradia", "Lazer", "Saúde", "Educação"])
            value = Decimal(random.uniform(10.0, 800.0)).quantize(Decimal("0.01"))
            status = random.choice(["paid", "pending"])
            expense_type = random.choice(["fixed", "variable"])

        transaction_doc = {
            "user_id": USER_ID,
            "account_id": ACCOUNT_ID,
            "type": trans_type,
            "description": fake.text(max_nb_chars=30),
            "value": value,
            "transaction_date": fake.date_time_between(start_date="-2y", end_date="now"),
            "category": category,
            "status": status,
            "expense_type": expense_type,
            "notes": fake.sentence(),
        }
        transactions_to_insert.append(transaction_doc)

    if transactions_to_insert:
        print("\nInserindo transações no banco de dados...")
        # Usamos insert_many para uma operação em massa, muito mais rápida
        transactions_collection.insert_many(transactions_to_insert)
        print(f"{len(transactions_to_insert)} transações criadas com sucesso!")
    else:
        print("Nenhuma transação foi gerada.")

    client.close()
    print("Conexão com o MongoDB fechada.")

if __name__ == "__main__":
    create_fake_transactions()