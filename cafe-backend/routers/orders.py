from fastapi import APIRouter
import database

router = APIRouter()

@router.get("/")
async def get_orders():
    db = await database.get_db()
    rows = await db.fetch("""
        SELECT 
            o.id, o.codigo_orden, o.estado,
            o.subtotal, o.descuento, o.propina, o.total,
            o.notas_generales, o.fecha_creacion,
            u.nombre_completo AS cliente
        FROM orders o
        LEFT JOIN users u ON u.id = o.cliente_id
        ORDER BY o.fecha_creacion DESC
    """)
    return [dict(r) for r in rows]

@router.get("/{order_id}")
async def get_order(order_id: str):
    db = await database.get_db()
    
    order = await db.fetchrow("""
        SELECT o.*, u.nombre_completo AS cliente
        FROM orders o
        LEFT JOIN users u ON u.id = o.cliente_id
        WHERE o.id = $1::uuid
    """, order_id)
    
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    items = await db.fetch("""
        SELECT 
            oi.id, oi.tamano, oi.precio_base, oi.precio_final,
            oi.cantidad, oi.notas_item,
            d.nombre AS bebida, d.imagen_url
        FROM order_items oi
        JOIN drinks d ON d.id = oi.bebida_id
        WHERE oi.orden_id = $1::uuid
    """, order_id)
    
    result = dict(order)
    result["items"] = [dict(i) for i in items]
    return result