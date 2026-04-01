from fastapi import APIRouter
import database

router = APIRouter()

@router.get("/")
async def get_categories():
    db = await database.get_db()
    rows = await db.fetch("""
        SELECT id, nombre, descripcion, imagen_url
        FROM categories
        WHERE activa = TRUE
        ORDER BY orden_visualizacion
    """)
    return [dict(r) for r in rows]