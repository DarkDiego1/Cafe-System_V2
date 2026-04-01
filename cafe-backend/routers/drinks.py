from fastapi import APIRouter, HTTPException
import database

router = APIRouter()

@router.get("/")
async def get_drinks():
    db = await database.get_db()
    rows = await db.fetch("""
        SELECT 
            d.id, d.nombre, d.descripcion,
            d.imagen_url,
            d.precio_chico, d.precio_mediano, d.precio_grande,
            d.disponible,
            c.nombre AS categoria
        FROM drinks d
        JOIN categories c ON c.id = d.categoria_id
        WHERE d.activo = TRUE
        ORDER BY c.orden_visualizacion, d.nombre
    """)
    return [dict(r) for r in rows]

@router.get("/{drink_id}")
async def get_drink(drink_id: int):
    db = await database.get_db()
    
    # Datos de la bebida
    drink = await db.fetchrow("""
        SELECT d.*, c.nombre AS categoria
        FROM drinks d
        JOIN categories c ON c.id = d.categoria_id
        WHERE d.id = $1 AND d.activo = TRUE
    """, drink_id)
    
    if not drink:
        raise HTTPException(status_code=404, detail="Bebida no encontrada")
    
    # Ingredientes de la receta base
    ingredients = await db.fetch("""
        SELECT 
            i.id, i.nombre, i.unidad_medida, i.imagen_url,
            di.cantidad_base, di.cantidad_minima, 
            di.cantidad_maxima, di.es_opcional
        FROM drink_ingredients di
        JOIN ingredients i ON i.id = di.ingrediente_id
        WHERE di.bebida_id = $1 AND i.disponible = TRUE
        ORDER BY di.es_opcional, i.nombre
    """, drink_id)
    
    result = dict(drink)
    result["ingredientes"] = [dict(i) for i in ingredients]
    return result

@router.get("/category/{category_id}")
async def get_drinks_by_category(category_id: int):
    db = await database.get_db()
    rows = await db.fetch("""
        SELECT id, nombre, descripcion, imagen_url,
               precio_chico, precio_mediano, precio_grande, disponible
        FROM drinks
        WHERE categoria_id = $1 AND activo = TRUE
        ORDER BY nombre
    """, category_id)
    return [dict(r) for r in rows]