from fastapi import APIRouter
import database

router = APIRouter()

@router.get("/")
async def get_ingredients():
    db = await database.get_db()
    rows = await db.fetch("""
        SELECT id, nombre, unidad_medida, imagen_url,
               stock_actual, disponible, descripcion
        FROM ingredients
        WHERE activo = TRUE
        ORDER BY nombre
    """)
    return [dict(r) for r in rows]