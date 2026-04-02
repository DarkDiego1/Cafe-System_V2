"""
routers/suppliers.py
Módulo 03 — Gestión y Administración (MAM)

Router FastAPI para gestión de proveedores.
Cubre: CU57 — Gestionar datos de proveedores
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

import database
from entities.supplier import Supplier
from schemas.inventory_schemas import SupplierCreateSchema, SupplierUpdateSchema

router = APIRouter()


@router.get("/")
async def get_suppliers(activo: Optional[bool] = None):
    """CU57 — Lista todos los proveedores."""
    db = await database.get_db()
    query = """
        SELECT s.id, s.nombre, s.contacto, s.telefono, s.email,
               s.activo, s.notas, s.fecha_registro,
               COUNT(isu.ingrediente_id) AS total_ingredientes
        FROM suppliers s
        LEFT JOIN ingredient_suppliers isu ON isu.proveedor_id = s.id
        {where}
        GROUP BY s.id
        ORDER BY s.nombre
    """
    if activo is not None:
        rows = await db.fetch(
            query.format(where="WHERE s.activo = $1"), activo
        )
    else:
        rows = await db.fetch(query.format(where=""))

    suppliers = [Supplier.from_db_row(dict(r)) for r in rows]
    return [s.to_dict() for s in suppliers]


@router.get("/{supplier_id}")
async def get_supplier(supplier_id: int):
    """CU57 — Detalle de un proveedor con sus ingredientes asociados."""
    db = await database.get_db()

    row = await db.fetchrow("SELECT * FROM suppliers WHERE id = $1", supplier_id)
    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    supplier = Supplier.from_db_row(dict(row))

    ingredientes = await db.fetch("""
        SELECT i.id, i.nombre, i.unidad_medida, isu.principal
        FROM ingredient_suppliers isu
        JOIN ingredients i ON i.id = isu.ingrediente_id
        WHERE isu.proveedor_id = $1
        ORDER BY isu.principal DESC, i.nombre
    """, supplier_id)

    result = supplier.to_dict()
    result["ingredientes"] = [dict(r) for r in ingredientes]
    return result


@router.post("/", status_code=201)
async def create_supplier(data: SupplierCreateSchema):
    """CU57 — Registrar nuevo proveedor."""
    db = await database.get_db()

    existe = await db.fetchval(
        "SELECT id FROM suppliers WHERE LOWER(nombre) = LOWER($1)", data.nombre
    )
    if existe:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un proveedor con el nombre '{data.nombre}'."
        )

    row = await db.fetchrow("""
        INSERT INTO suppliers (nombre, contacto, telefono, email, notas, activo, fecha_registro)
        VALUES ($1, $2, $3, $4, $5, TRUE, NOW())
        RETURNING *
    """, data.nombre, data.contacto, data.telefono, data.email, data.notas)

    return Supplier.from_db_row(dict(row)).to_dict()


@router.patch("/{supplier_id}")
async def update_supplier(supplier_id: int, data: SupplierUpdateSchema):
    """CU57 — Modificar datos del proveedor."""
    db = await database.get_db()

    row = await db.fetchrow("SELECT * FROM suppliers WHERE id = $1", supplier_id)
    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    campos = data.model_dump(exclude_none=True)
    if not campos:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar.")

    set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(campos))
    updated = await db.fetchrow(
        f"UPDATE suppliers SET {set_clauses} WHERE id = $1 RETURNING *",
        supplier_id, *list(campos.values()),
    )
    return Supplier.from_db_row(dict(updated)).to_dict()


@router.post("/{supplier_id}/ingredients/{ingredient_id}")
async def assign_ingredient(
    supplier_id: int, ingredient_id: int, principal: bool = True
):
    """
    CU57 / CU55 — Vincula un ingrediente con un proveedor.
    Si principal=True es el proveedor predeterminado para listas de compras (CU55).
    """
    db = await database.get_db()

    sup_row = await db.fetchrow(
        "SELECT * FROM suppliers WHERE id = $1 AND activo = TRUE", supplier_id
    )
    if not sup_row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado o inactivo.")

    supplier = Supplier.from_db_row(dict(sup_row))
    # validarProveedorActivo()
    if not supplier.validar_proveedor_activo():
        raise HTTPException(
            status_code=422,
            detail=supplier.resaltar_proveedor_inactivo()
        )

    ing = await db.fetchval(
        "SELECT id FROM ingredients WHERE id = $1 AND activo = TRUE", ingredient_id
    )
    if not ing:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado.")

    if principal:
        await db.execute(
            "UPDATE ingredient_suppliers SET principal = FALSE WHERE ingrediente_id = $1",
            ingredient_id,
        )

    await db.execute("""
        INSERT INTO ingredient_suppliers (proveedor_id, ingrediente_id, principal)
        VALUES ($1, $2, $3)
        ON CONFLICT (proveedor_id, ingrediente_id)
        DO UPDATE SET principal = EXCLUDED.principal
    """, supplier_id, ingredient_id, principal)

    return {"mensaje": "Ingrediente asignado correctamente al proveedor."}


@router.delete("/{supplier_id}/ingredients/{ingredient_id}", status_code=204)
async def remove_ingredient(supplier_id: int, ingredient_id: int):
    """CU57 — Desvincula un ingrediente de un proveedor."""
    db = await database.get_db()
    await db.execute("""
        DELETE FROM ingredient_suppliers
        WHERE proveedor_id = $1 AND ingrediente_id = $2
    """, supplier_id, ingredient_id)