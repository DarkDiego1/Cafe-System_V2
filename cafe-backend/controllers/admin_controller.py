"""
controllers/admin_controller.py
Módulo 03 — Gestión y Administración (MAM)

Controlador: AdminController
Casos de uso: CU58, CU59, CU63, CU64, UC65

Orquesta AdminService y traduce excepciones de dominio
a HTTPException de FastAPI.
"""

from datetime import datetime
from typing import Optional
from fastapi import HTTPException

from services.admin_service import AdminService
from entities.employee import Employee, ROLES_VALIDOS


class AdminController:
    """
    Intermediario entre los routers de administración y AdminService.
    """

    def __init__(self) -> None:
        self._service = AdminService()

    # ── CU58: gestionar empleados ─────────────────────────────────────

    async def listar_empleados(self, activo: Optional[bool] = None) -> list[dict]:
        return await self._service.listar_empleados(activo)

    async def obtener_empleado(self, employee_id: int) -> dict:
        try:
            return (await self._service.obtener_empleado(employee_id)).to_dict()
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def crear_empleado(
        self,
        nombre_completo: str,
        usuario: str,
        contrasena_hash: str,
        rol: str,
        email: Optional[str] = None,
        telefono: Optional[str] = None,
        creado_por_id: Optional[int] = None,
        creado_por_nombre: str = "sistema",
    ) -> dict:
        try:
            emp = await self._service.crear_empleado(
                nombre_completo=nombre_completo,
                usuario=usuario,
                contrasena_hash=contrasena_hash,
                rol=rol,
                email=email,
                telefono=telefono,
                creado_por_id=creado_por_id,
                creado_por_nombre=creado_por_nombre,
            )
            return emp.to_dict()
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    async def modificar_empleado(
        self,
        employee_id: int,
        campos: dict,
        modificado_por_id: Optional[int] = None,
        modificado_por_nombre: str = "sistema",
    ) -> dict:
        try:
            emp = await self._service.modificar_empleado(
                employee_id, campos, modificado_por_id, modificado_por_nombre
            )
            return emp.to_dict()
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU59: asignar permisos ────────────────────────────────────────

    async def asignar_rol(
        self,
        employee_id: int,
        nuevo_rol: str,
        asignado_por_id: Optional[int] = None,
        asignado_por_nombre: str = "sistema",
    ) -> dict:
        try:
            emp = await self._service.asignar_rol(
                employee_id, nuevo_rol, asignado_por_id, asignado_por_nombre
            )
            return {
                "mensaje": f"Rol actualizado a '{nuevo_rol}' correctamente.",
                "empleado": emp.to_dict(),
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # ── CU63: gestionar menú ──────────────────────────────────────────

    async def activar_desactivar_bebida(
        self,
        drink_id: int,
        activo: bool,
        modificado_por_id: Optional[int] = None,
        modificado_por_nombre: str = "sistema",
    ) -> dict:
        try:
            return await self._service.activar_desactivar_bebida(
                drink_id, activo, modificado_por_id, modificado_por_nombre
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def actualizar_precio_bebida(
        self,
        drink_id: int,
        precio_chico: Optional[float],
        precio_mediano: Optional[float],
        precio_grande: Optional[float],
        modificado_por_id: Optional[int] = None,
        modificado_por_nombre: str = "sistema",
    ) -> dict:
        try:
            return await self._service.actualizar_precio_bebida(
                drink_id, precio_chico, precio_mediano, precio_grande,
                modificado_por_id, modificado_por_nombre,
            )
        except (KeyError, ValueError) as e:
            code = 404 if isinstance(e, KeyError) else 422
            raise HTTPException(status_code=code, detail=str(e))

    async def actualizar_disponibilidad_bebida(
        self, drink_id: int, disponible: bool
    ) -> dict:
        try:
            return await self._service.actualizar_disponibilidad_bebida(drink_id, disponible)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU64: configurar umbrales ─────────────────────────────────────

    async def obtener_umbrales(self) -> dict:
        threshold = await self._service.obtener_umbrales()
        return threshold.to_dict()

    async def configurar_umbrales(
        self,
        umbral_stock_minimo: Optional[float] = None,
        umbral_tiempo_prep: Optional[int] = None,
        umbral_ventas_bajas: Optional[float] = None,
        umbral_desperdicio: Optional[float] = None,
        modificado_por_id: Optional[int] = None,
        modificado_por_nombre: str = "gerente",
    ) -> dict:
        try:
            threshold = await self._service.configurar_umbrales(
                umbral_stock_minimo=umbral_stock_minimo,
                umbral_tiempo_prep=umbral_tiempo_prep,
                umbral_ventas_bajas=umbral_ventas_bajas,
                umbral_desperdicio=umbral_desperdicio,
                modificado_por_id=modificado_por_id,
                modificado_por_nombre=modificado_por_nombre,
            )
            return {
                "mensaje": "Umbrales configurados correctamente.",
                "umbrales": threshold.to_dict(),
            }
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # ── CU65: registro de auditoría ───────────────────────────────────

    async def obtener_auditoria(
        self,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        tipo_evento: Optional[str] = None,
        usuario_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Corresponde al flujo completo CU65:
          Seleccionar_filtros_busqueda()
          → Especificar_periodo_tiempo()
          → Seleccionar_tipo_evento()
          → Mostrar_registros_auditoria()
        """
        return await self._service.obtener_registros_auditoria(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_evento=tipo_evento,
            usuario_id=usuario_id,
            limit=limit,
            offset=offset,
        )