import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

pool = None

async def get_db():
    return pool

async def connect():
    global pool
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        min_size=2,
        max_size=10
    )
    print("✅ Conectado a PostgreSQL")

async def disconnect():
    await pool.close()