from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import database
from routers import drinks, ingredients, categories, orders

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(
    title="Café Nuevos Horizontes API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — permite que Vue (puerto 5173) hable con FastAPI (puerto 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drinks.router,      prefix="/api/drinks",      tags=["Bebidas"])
app.include_router(ingredients.router, prefix="/api/ingredients",  tags=["Ingredientes"])
app.include_router(categories.router,  prefix="/api/categories",   tags=["Categorías"])
app.include_router(orders.router,      prefix="/api/orders",       tags=["Órdenes"])

@app.get("/")
async def root():
    return {"message": "API Café Nuevos Horizontes funcionando ✅"}