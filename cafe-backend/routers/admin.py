"""
routers/admin.py
Módulo 03 — Gestión y Administración (MAM)

Router FastAPI que delega en AdminController.
Cubre: CU58, CU59, CU63, CU64, CU65
"""

from fastapi import APIRouter, Query
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from controllers.admin_controller import AdminController
from entities.employee import ROLES_VALIDOS

router = APIRouter()
ctrl   = AdminController()


# ══════════════════════════════════════════════════════════
# SCHEMAS inline
# ══════════════════════════════════════════════════════════

class EmployeeCreateSchema(BaseModel):
    nombre_completo: str           = Field(..., min_length=2, max_length=150)
    usuario:         str           = Field(..., min_length=3, max_length=60)
    contrasena_hash: str           = Field(..., min_length=8)
    rol:             str           = Field(..., description="gerente | barista | empleado")
    email:           Optional[str] = None
    telefono:        Optional[str] = None


class EmployeeUpdateSchema(BaseModel):
    nombre_completo: Optional[str]  = None
    email:           Optional[str]  = None
    telefono:        Optional[str]  = None
    activo:          Optional[bool] = None


class RolUpdateSchema(BaseModel):
    rol: str = Field(..., description="gerente | barista | empleado")


class DrinkStatusSchema(BaseModel):
    activo: bool


class DrinkDisponibilidadSchema(BaseModel):
    disponible: bool


class DrinkPreciosSchema(BaseModel):
    precio_chico:   Optional[float] = Field(None, ge=0)
    precio_mediano: Optional[float] = Field(None, ge=0)
    precio_grande:  Optional[float] = Field(None, ge=0)


class UmbralesSchema(BaseModel):
    umbral_stock_minimo:  Optional[float] = Field(None, ge=0, le=100)
    umbral_tiempo_prep:   Optional[int]   = Field(None, gt=0)
    umbral_ventas_bajas:  Optional[float] = Field(None, ge=0)
    umbral_desperdicio:   Optional[float] = Field(None, ge=0, le=100)


# ══════════════════════════════════════════════════════════
# CU58 — Gestionar empleados
# ══════════════════════════════════════════════════════════

@router.get("/employees")
async def get_employees(activo: Optional[bool] = None):
    """CU58 — Listar empleados con sus permisos."""
    return await ctrl.listar_empleados(activo)


@router.get("/employees/{employee_id}")
async def get_employee(employee_id: int):
    """CU58 — Detalle de un empleado."""
    return await ctrl.obtener_empleado(employee_id)


@router.post("/employees", status_code=201)
async def create_employee(data: EmployeeCreateSchema):
    """CU58 — Registrar nuevo empleado."""
    return await ctrl.crear_empleado(**data.model_dump())


@router.patch("/employees/{employee_id}")
async def update_employee(employee_id: int, data: EmployeeUpdateSchema):
    """CU58 — Modificar datos del empleado."""
    campos = data.model_dump(exclude_none=True)
    return await ctrl.modificar_empleado(employee_id, campos)


# ══════════════════════════════════════════════════════════
# CU59 — Asignar permisos de acceso
# ══════════════════════════════════════════════════════════

@router.patch("/employees/{employee_id}/role")
async def update_employee_role(employee_id: int, data: RolUpdateSchema):
    """
    CU59 — Cambiar el rol del empleado, lo que modifica sus permisos.
    Retorna el empleado actualizado con su nueva lista de permisos.
    """
    return await ctrl.asignar_rol(employee_id, data.rol)


@router.get("/roles")
async def get_roles():
    """CU59 — Retorna los roles disponibles con sus permisos asociados."""
    from entities.employee import PERMISOS_POR_ROL
    return {
        "roles": [
            {"rol": rol, "permisos": permisos}
            for rol, permisos in PERMISOS_POR_ROL.items()
        ]
    }


# ══════════════════════════════════════════════════════════
# CU63 — Gestionar menú
# ══════════════════════════════════════════════════════════

@router.patch("/menu/drinks/{drink_id}/status")
async def update_drink_status(drink_id: int, data: DrinkStatusSchema):
    """CU63 — Activar o desactivar una bebida del menú."""
    return await ctrl.activar_desactivar_bebida(drink_id, data.activo)


@router.patch("/menu/drinks/{drink_id}/disponibilidad")
async def update_drink_disponibilidad(drink_id: int, data: DrinkDisponibilidadSchema):
    """CU63 — Marcar una bebida como disponible o no disponible para pedidos."""
    return await ctrl.actualizar_disponibilidad_bebida(drink_id, data.disponible)


@router.patch("/menu/drinks/{drink_id}/prices")
async def update_drink_prices(drink_id: int, data: DrinkPreciosSchema):
    """CU63 — Actualizar precios de una bebida."""
    return await ctrl.actualizar_precio_bebida(
        drink_id=drink_id,
        precio_chico=data.precio_chico,
        precio_mediano=data.precio_mediano,
        precio_grande=data.precio_grande,
    )


# ══════════════════════════════════════════════════════════
# CU64 — Configurar umbrales de alertas
# ══════════════════════════════════════════════════════════

@router.get("/thresholds")
async def get_thresholds():
    """
    CU64 — Retorna la configuración actual de umbrales del sistema.
    Corresponde a Acceder_configuracion_alertas().
    """
    return await ctrl.obtener_umbrales()


@router.put("/thresholds")
async def update_thresholds(data: UmbralesSchema):
    """
    CU64 — Configura los umbrales de alertas del sistema.
    Corresponde al flujo completo:
      Configurar_umbral_stock_minimo()
      → Configurar_umbral_tiempo_preparacion()
      → Configurar_umbral_ventas_bajas()
      → Configurar_umbral_desperdicio()
      → Aplicar_configuracion_umbrales()
    """
    return await ctrl.configurar_umbrales(**data.model_dump(exclude_none=True))


# ══════════════════════════════════════════════════════════
# CU65 — Ver registro de auditoría
# ══════════════════════════════════════════════════════════

@router.get("/audit")
async def get_audit_logs(
    fecha_inicio: Optional[datetime] = Query(None),
    fecha_fin:    Optional[datetime] = Query(None),
    tipo_evento:  Optional[str]      = Query(None, description="Tipo de evento a filtrar"),
    usuario_id:   Optional[int]      = Query(None),
    limit:        int                = Query(default=100, ge=1, le=500),
    offset:       int                = Query(default=0, ge=0),
):
    """
    CU65 — Ver registro de auditoría del sistema.
    Corresponde al flujo:
      Seleccionar_filtros_busqueda()
      → Especificar_periodo_tiempo(periodo)
      → Seleccionar_tipo_evento()
      → Confirmar_busqueda_auditoria()
      → Mostrar_registros_auditoria()
    """
    return await ctrl.obtener_auditoria(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tipo_evento=tipo_evento,
        usuario_id=usuario_id,
        limit=limit,
        offset=offset,
    )


@router.get("/audit/event-types")
async def get_audit_event_types():
    """CU65 — Lista los tipos de evento registrables para usar como filtro."""
    from entities.audit_log import TIPOS_EVENTO
    return {"tipos_evento": sorted(TIPOS_EVENTO)}