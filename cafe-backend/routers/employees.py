"""
routers/employees.py
Módulo 03 — Gestión y Administración (MAM)

Router FastAPI para gestión de empleados y permisos.
Cubre: CU58 — Gestionar empleados | CU59 — Asignar permisos
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel, Field

import database

router = APIRouter()


class EmployeeCreateSchema(BaseModel):
    nombre_completo: str           = Field(..., min_length=2, max_length=150)
    usuario:         str           = Field(..., min_length=3, max_length=60)
    contrasena_hash: str           = Field(..., min_length=8)
    rol:             str           = Field(..., description="barista | gerente | empleado")
    email:           Optional[str] = None
    telefono:        Optional[str] = None


class EmployeeUpdateSchema(BaseModel):
    nombre_completo: Optional[str]  = None
    email:           Optional[str]  = None
    telefono:        Optional[str]  = None
    activo:          Optional[bool] = None


class RolUpdateSchema(BaseModel):
    rol: str = Field(..., description="barista | gerente | empleado")


ROLES_VALIDOS = {"barista", "gerente", "empleado"}


@router.get("/")
async def get_employees(activo: Optional[bool] = None):
    """CU58 — Listar empleados."""
    db = await database.get_db()
    query = """
        SELECT id, nombre_completo, usuario, rol, email,
               telefono, activo, fecha_contratacion
        FROM employees {where}
        ORDER BY nombre_completo
    """
    if activo is not None:
        rows = await db.fetch(query.format(where="WHERE activo = $1"), activo)
    else:
        rows = await db.fetch(query.format(where=""))
    return [dict(r) for r in rows]


@router.get("/{employee_id}")
async def get_employee(employee_id: int):
    """CU58 — Detalle de un empleado."""
    db = await database.get_db()
    row = await db.fetchrow(
        "SELECT id, nombre_completo, usuario, rol, email, "
        "telefono, activo, fecha_contratacion FROM employees WHERE id = $1",
        employee_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return dict(row)


@router.post("/", status_code=201)
async def create_employee(data: EmployeeCreateSchema):
    """CU58 — Registrar nuevo empleado."""
    if data.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=422, detail=f"Rol inválido. Opciones: {', '.join(ROLES_VALIDOS)}")

    db = await database.get_db()
    existe = await db.fetchval(
        "SELECT id FROM employees WHERE LOWER(usuario) = LOWER($1)", data.usuario
    )
    if existe:
        raise HTTPException(status_code=409, detail=f"Ya existe un empleado con el usuario '{data.usuario}'.")

    row = await db.fetchrow("""
        INSERT INTO employees
            (nombre_completo, usuario, contrasena_hash, rol, email, telefono, activo, fecha_contratacion)
        VALUES ($1, $2, $3, $4, $5, $6, TRUE, NOW())
        RETURNING id, nombre_completo, usuario, rol, email, activo, fecha_contratacion
    """, data.nombre_completo, data.usuario, data.contrasena_hash,
        data.rol, data.email, data.telefono)

    return dict(row)


@router.patch("/{employee_id}")
async def update_employee(employee_id: int, data: EmployeeUpdateSchema):
    """CU58 — Modificar datos de empleado."""
    db = await database.get_db()
    existe = await db.fetchval("SELECT id FROM employees WHERE id = $1", employee_id)
    if not existe:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")

    campos = data.model_dump(exclude_none=True)
    if not campos:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar.")

    set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(campos))
    row = await db.fetchrow(
        f"UPDATE employees SET {set_clauses} WHERE id = $1 "
        f"RETURNING id, nombre_completo, usuario, rol, activo",
        employee_id, *list(campos.values()),
    )
    return dict(row)


@router.patch("/{employee_id}/role")
async def update_role(employee_id: int, data: RolUpdateSchema):
    """CU59 — Asignar permisos de acceso (cambiar rol)."""
    if data.rol not in ROLES_VALIDOS:
        raise HTTPException(status_code=422, detail=f"Rol inválido. Opciones: {', '.join(ROLES_VALIDOS)}")

    db = await database.get_db()
    row = await db.fetchrow(
        "UPDATE employees SET rol = $2 WHERE id = $1 "
        "RETURNING id, nombre_completo, usuario, rol",
        employee_id, data.rol,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return {"mensaje": "Rol actualizado correctamente.", "empleado": dict(row)}