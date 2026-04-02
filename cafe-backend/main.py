"""
main.py — Café Nuevos Horizontes API
Versión actualizada con Módulo 03 completo.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import database

# Módulo 01 — Experiencia del Cliente
from routers import drinks, ingredients, categories, orders

# Módulo 02 — Empleados y Producción
from routers import production
from routers import production

# Módulo 03 — Gestión y Administración (MAM)
from routers import inventory, suppliers, reports, admin
from middleware.audit_middleware import AuditMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()


app = FastAPI(
    title="Café Nuevos Horizontes API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auditoría automática (CU65) ────────────────────────────────────────────
app.add_middleware(AuditMiddleware)

# ── Módulo 01 ──────────────────────────────────────────────────────────────
app.include_router(drinks.router,      prefix="/api/drinks",       tags=["M01 · Bebidas"])
app.include_router(ingredients.router, prefix="/api/ingredients",  tags=["M01 · Ingredientes"])
app.include_router(categories.router,  prefix="/api/categories",   tags=["M01 · Categorías"])
app.include_router(orders.router,      prefix="/api/orders",       tags=["M01 · Órdenes"])

# ── Módulo 02 — Producción y Operaciones ─────────────────────────────────
app.include_router(production.router, prefix="/api/production", tags=["M02 · Producción"])
app.include_router(production.router, prefix="/api/production", tags=["M02 · Producción"])

# ── Módulo 03 — Gestión y Administración ──────────────────────────────────
app.include_router(inventory.router,   prefix="/api/inventory",    tags=["M03 · Inventario"])
app.include_router(suppliers.router,   prefix="/api/suppliers",    tags=["M03 · Proveedores"])
app.include_router(reports.router,     prefix="/api/reports",      tags=["M03 · Reportes"])
app.include_router(admin.router,       prefix="/api/admin",        tags=["M03 · Administración"])


@app.get("/")
async def root():
    return {"message": "API Café Nuevos Horizontes v2.0 ✅"}