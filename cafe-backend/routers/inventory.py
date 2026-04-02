"""
routers/inventory.py
Módulo 03 — Gestión y Administración (MAM)

Router FastAPI que delega en InventoryController.
Cubre: CU48, CU49, CU50, CU51, CU52, CU53, CU55, CU56
"""

from fastapi import APIRouter, Query
from typing import Optional

import database
from controllers.inventory_controller import InventoryController
from schemas.inventory_schemas import (
    IngredientCreateSchema,
    IngredientUpdateSchema,
    StockManualUpdateSchema,
    EntradaMercanciaSchema,
    WasteLogCreateSchema,
    PurchaseOrderCreateSchema,
    EstadoOrdenCompraSchema,
)

router = APIRouter()
ctrl   = InventoryController()


# ══════════════════════════════════════════════════════════
# INGREDIENTES
# ══════════════════════════════════════════════════════════

@router.get("/ingredients")
async def get_inventory_levels(
    alerta: Optional[bool] = Query(None, description="True = solo ingredientes bajo mínimo")
):
    """CU50 — Consultar niveles de inventario | CU51 — Alertas de stock bajo"""
    return await ctrl.consultar_niveles_inventario(solo_alertas=alerta is True)


@router.get("/ingredients/alerts")
async def get_stock_alerts():
    """CU51 — Retorna exclusivamente los ingredientes con alerta activa."""
    return await ctrl.obtener_alertas()


@router.post("/ingredients", status_code=201)
async def create_ingredient(data: IngredientCreateSchema):
    """CU48 — Registrar nuevo ingrediente (con validación de duplicado CU57)."""
    return await ctrl.crear_ingrediente(**data.model_dump())


@router.patch("/ingredients/{ingredient_id}")
async def update_ingredient(ingredient_id: int, data: IngredientUpdateSchema):
    """CU49 — Modificar información de ingrediente."""
    campos = data.model_dump(exclude_none=True)
    return await ctrl.modificar_ingrediente(ingredient_id, campos)


@router.put("/ingredients/{ingredient_id}/stock")
async def update_stock_manual(ingredient_id: int, data: StockManualUpdateSchema):
    """CU52 — Actualizar inventario manualmente."""
    return await ctrl.actualizar_stock_manual(
        ingredient_id, data.nuevo_stock, data.motivo
    )


@router.post("/ingredients/{ingredient_id}/entry")
async def register_stock_entry(ingredient_id: int, data: EntradaMercanciaSchema):
    """CU53 — Registrar entrada de mercancía."""
    return await ctrl.registrar_entrada_mercancia(
        ingredient_id, data.cantidad, data.orden_compra_id, data.notas
    )


@router.post("/ingredients/waste", status_code=201)
async def register_waste(data: WasteLogCreateSchema):
    """CU56 — Registrar merma / desperdicio."""
    return await ctrl.registrar_perdida_contable(
        data.ingrediente_id, data.cantidad, data.motivo, data.registrado_por
    )


# ══════════════════════════════════════════════════════════
# PURCHASE ORDERS — CU55, CU53
# ══════════════════════════════════════════════════════════

@router.get("/purchase-orders/suggested")
async def get_suggested_purchase_list():
    """CU55 — Lista de compras automatizada."""
    return await ctrl.generar_lista_compras()


@router.get("/purchase-orders")
async def get_purchase_orders(estado: Optional[str] = None):
    """Lista órdenes de compra, filtradas por estado si se indica."""
    db = await database.get_db()
    query = """
        SELECT po.id, po.estado, po.notas,
               po.fecha_creacion, po.fecha_envio, po.fecha_recepcion,
               s.nombre AS proveedor,
               COUNT(poi.id) AS total_items,
               COALESCE(SUM(poi.cantidad * i.costo_unitario), 0) AS total_estimado
        FROM purchase_orders po
        JOIN suppliers s ON s.id = po.proveedor_id
        LEFT JOIN purchase_order_items poi ON poi.orden_id = po.id
        LEFT JOIN ingredients i ON i.id = poi.ingrediente_id
    """
    params = []
    if estado:
        query += " WHERE po.estado = $1"
        params.append(estado)
    query += " GROUP BY po.id, s.nombre ORDER BY po.fecha_creacion DESC"
    rows = await db.fetch(query, *params)
    return [dict(r) for r in rows]


@router.post("/purchase-orders", status_code=201)
async def create_purchase_order(data: PurchaseOrderCreateSchema):
    """CU55 — Crear borrador de orden de compra."""
    db = await database.get_db()
    from fastapi import HTTPException
    from entities.supplier import Supplier

    sup_row = await db.fetchrow("SELECT * FROM suppliers WHERE id = $1", data.proveedor_id)
    if not sup_row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    supplier = Supplier.from_db_row(dict(sup_row))
    advertencia = supplier.resaltar_proveedor_inactivo()
    if advertencia:
        raise HTTPException(status_code=422, detail=advertencia)

    async with db.transaction():
        orden = await db.fetchrow("""
            INSERT INTO purchase_orders (proveedor_id, estado, notas, fecha_creacion)
            VALUES ($1, 'borrador', $2, NOW())
            RETURNING id, estado, fecha_creacion
        """, data.proveedor_id, data.notas)

        for item in data.items:
            await db.execute("""
                INSERT INTO purchase_order_items (orden_id, ingrediente_id, cantidad)
                VALUES ($1, $2, $3)
            """, orden["id"], item.ingrediente_id, item.cantidad)

    return {"mensaje": "Orden de compra creada.", "orden": dict(orden)}


@router.patch("/purchase-orders/{order_id}/status")
async def update_purchase_order_status(order_id: int, data: EstadoOrdenCompraSchema):
    """Actualiza el estado de una orden de compra."""
    db = await database.get_db()
    from fastapi import HTTPException
    from entities.purchase_order import PurchaseOrder

    row = await db.fetchrow("SELECT * FROM purchase_orders WHERE id = $1", order_id)
    if not row:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada.")

    orden = PurchaseOrder.from_db_row(dict(row))
    # Aplicar lógica de dominio
    if data.estado == "enviada":
        orden.enviar()
    elif data.estado == "recibida":
        orden.confirmar_recepcion()
    elif data.estado == "cancelada":
        orden.cancelar()

    extras = ""
    if orden.fecha_envio:
        extras = ", fecha_envio = NOW()"
    if orden.fecha_recepcion:
        extras = ", fecha_recepcion = NOW()"

    updated = await db.fetchrow(
        f"UPDATE purchase_orders SET estado = $2{extras} WHERE id = $1 RETURNING *",
        order_id, orden.estado,
    )
    return dict(updated)


# ══════════════════════════════════════════════════════════
# HISTORIAL DE MERMAS
# ══════════════════════════════════════════════════════════

@router.get("/waste-logs")
async def get_waste_logs(ingrediente_id: Optional[int] = None):
    """Historial de mermas, opcionalmente filtrado por ingrediente."""
    db = await database.get_db()
    query = """
        SELECT wl.id, wl.cantidad, wl.motivo, wl.costo_estimado, wl.fecha,
               i.nombre AS ingrediente, i.unidad_medida,
               e.nombre_completo AS registrado_por_nombre
        FROM waste_logs wl
        JOIN ingredients i ON i.id = wl.ingrediente_id
        LEFT JOIN employees e ON e.id = wl.registrado_por
    """
    params = []
    if ingrediente_id:
        query += " WHERE wl.ingrediente_id = $1"
        params.append(ingrediente_id)
    query += " ORDER BY wl.fecha DESC"
    rows = await db.fetch(query, *params)
    from entities.waste_log import WasteLog
    return [WasteLog.from_db_row(dict(r)).to_dict() for r in rows]