"""
services/admin_service.py
Módulo 03 — Gestión y Administración (MAM)

Servicio: AdminService
Casos de uso: CU58, CU59, CU63, CU64, UC65

Centraliza la lógica de administración del sistema:
empleados, permisos, menú, umbrales de alertas y auditoría.
"""

import json
from datetime import datetime
from typing import Optional

import database
from entities.employee import Employee, ROLES_VALIDOS
from entities.alert_threshold import AlertThreshold
from entities.audit_log import AuditLog


class AdminService:
    """
    Capa de servicio para administración del sistema.
    Todos los métodos operan sobre el pool asyncpg.
    """

    # ══════════════════════════════════════════════════════
    # CU65 — Auditoría (transversal, se usa en todos los CU)
    # ══════════════════════════════════════════════════════

    async def registrar_auditoria(
        self,
        tipo_evento: str,
        descripcion: str,
        usuario_id: Optional[int] = None,
        nombre_usuario: str = "sistema",
        entidad_afectada: Optional[str] = None,
        entidad_id: Optional[str] = None,
        datos_anteriores: Optional[dict] = None,
        datos_nuevos: Optional[dict] = None,
        ip_origen: Optional[str] = None,
    ) -> None:
        """
        Persiste un evento de auditoría. Llamado automáticamente por cada
        operación sensible del sistema.
        Corresponde al flujo CU65 — registro automático de eventos.
        """
        db = await database.get_db()
        await db.execute("""
            INSERT INTO audit_logs
                (tipo_evento, descripcion, usuario_id, nombre_usuario,
                 entidad_afectada, entidad_id, datos_anteriores,
                 datos_nuevos, ip_origen, fecha)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
        """,
            tipo_evento, descripcion, usuario_id, nombre_usuario,
            entidad_afectada, entidad_id,
            json.dumps(datos_anteriores) if datos_anteriores else None,
            json.dumps(datos_nuevos) if datos_nuevos else None,
            ip_origen,
        )

    async def obtener_registros_auditoria(
        self,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        tipo_evento: Optional[str] = None,
        usuario_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Retorna registros de auditoría con filtros.
        Corresponde al flujo:
          Seleccionar_filtros_busqueda()
          → Especificar_periodo_tiempo()
          → Seleccionar_tipo_evento()
          → Confirmar_busqueda_auditoria()
          → Mostrar_registros_auditoria()
        del diagrama CU65.
        """
        db = await database.get_db()

        condiciones = []
        params: list = []
        p = 1

        if fecha_inicio:
            condiciones.append(f"fecha >= ${p}")
            params.append(fecha_inicio)
            p += 1
        if fecha_fin:
            condiciones.append(f"fecha <= ${p}")
            params.append(fecha_fin)
            p += 1
        if tipo_evento:
            condiciones.append(f"tipo_evento = ${p}")
            params.append(tipo_evento)
            p += 1
        if usuario_id:
            condiciones.append(f"usuario_id = ${p}")
            params.append(usuario_id)
            p += 1

        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

        total = await db.fetchval(
            f"SELECT COUNT(*) FROM audit_logs {where}", *params
        )
        rows = await db.fetch(
            f"""
            SELECT * FROM audit_logs {where}
            ORDER BY fecha DESC
            LIMIT ${p} OFFSET ${p+1}
            """,
            *params, limit, offset,
        )

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "registros": [AuditLog.from_db_row(dict(r)).to_dict() for r in rows],
        }

    # ══════════════════════════════════════════════════════
    # CU58 — Gestionar empleados
    # ══════════════════════════════════════════════════════

    async def listar_empleados(self, activo: Optional[bool] = None) -> list[dict]:
        db = await database.get_db()
        query = """
            SELECT id, nombre_completo, usuario, rol,
                   email, telefono, activo, fecha_contratacion
            FROM employees {where}
            ORDER BY nombre_completo
        """
        if activo is not None:
            rows = await db.fetch(query.format(where="WHERE activo = $1"), activo)
        else:
            rows = await db.fetch(query.format(where=""))
        return [Employee.from_db_row(dict(r)).to_dict() for r in rows]

    async def obtener_empleado(self, employee_id: int) -> Employee:
        db = await database.get_db()
        row = await db.fetchrow(
            "SELECT * FROM employees WHERE id = $1", employee_id
        )
        if not row:
            raise KeyError(f"Empleado {employee_id} no encontrado.")
        return Employee.from_db_row(dict(row))

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
    ) -> Employee:
        db = await database.get_db()

        # Validar rol en dominio
        emp_temp = Employee(id=0, nombre_completo=nombre_completo, usuario=usuario, rol="empleado")
        if not emp_temp.validar_rol(rol):
            raise ValueError(f"Rol '{rol}' no válido. Opciones: {', '.join(ROLES_VALIDOS)}")

        existe = await db.fetchval(
            "SELECT id FROM employees WHERE LOWER(usuario) = LOWER($1)", usuario
        )
        if existe:
            raise ValueError(f"Ya existe un empleado con el usuario '{usuario}'.")

        row = await db.fetchrow("""
            INSERT INTO employees
                (nombre_completo, usuario, contrasena_hash, rol,
                 email, telefono, activo, fecha_contratacion)
            VALUES ($1, $2, $3, $4, $5, $6, TRUE, NOW())
            RETURNING *
        """, nombre_completo, usuario, contrasena_hash, rol, email, telefono)

        emp = Employee.from_db_row(dict(row))

        await self.registrar_auditoria(
            tipo_evento="crear_empleado",
            descripcion=f"Se creó el empleado '{nombre_completo}' con rol '{rol}'.",
            usuario_id=creado_por_id,
            nombre_usuario=creado_por_nombre,
            entidad_afectada="employees",
            entidad_id=str(emp.id),
            datos_nuevos=emp.to_dict(),
        )
        return emp

    async def modificar_empleado(
        self,
        employee_id: int,
        campos: dict,
        modificado_por_id: Optional[int] = None,
        modificado_por_nombre: str = "sistema",
    ) -> Employee:
        db = await database.get_db()

        anterior = await self.obtener_empleado(employee_id)

        set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(campos))
        row = await db.fetchrow(
            f"UPDATE employees SET {set_clauses} WHERE id = $1 RETURNING *",
            employee_id, *list(campos.values()),
        )
        nuevo = Employee.from_db_row(dict(row))

        await self.registrar_auditoria(
            tipo_evento="modificar_empleado",
            descripcion=f"Se modificó el empleado '{anterior.nombre_completo}'.",
            usuario_id=modificado_por_id,
            nombre_usuario=modificado_por_nombre,
            entidad_afectada="employees",
            entidad_id=str(employee_id),
            datos_anteriores=anterior.to_dict(),
            datos_nuevos=nuevo.to_dict(),
        )
        return nuevo

    # ══════════════════════════════════════════════════════
    # CU59 — Asignar permisos de acceso (cambio de rol)
    # ══════════════════════════════════════════════════════

    async def asignar_rol(
        self,
        employee_id: int,
        nuevo_rol: str,
        asignado_por_id: Optional[int] = None,
        asignado_por_nombre: str = "sistema",
    ) -> Employee:
        """
        Cambia el rol del empleado.
        Corresponde a asignarPermisos() — diagrama CU59.
        """
        db = await database.get_db()

        anterior = await self.obtener_empleado(employee_id)
        anterior.asignar_rol(nuevo_rol)  # valida en dominio

        row = await db.fetchrow(
            "UPDATE employees SET rol = $2 WHERE id = $1 RETURNING *",
            employee_id, nuevo_rol,
        )
        nuevo = Employee.from_db_row(dict(row))

        await self.registrar_auditoria(
            tipo_evento="cambiar_rol",
            descripcion=(
                f"Rol de '{anterior.nombre_completo}' cambiado: "
                f"'{anterior.rol}' → '{nuevo_rol}'."
            ),
            usuario_id=asignado_por_id,
            nombre_usuario=asignado_por_nombre,
            entidad_afectada="employees",
            entidad_id=str(employee_id),
            datos_anteriores={"rol": anterior.rol},
            datos_nuevos={"rol": nuevo_rol, "permisos": nuevo.obtener_permisos()},
        )
        return nuevo

    # ══════════════════════════════════════════════════════
    # CU63 — Gestionar menú (bebidas y categorías)
    # ══════════════════════════════════════════════════════

    async def activar_desactivar_bebida(
        self,
        drink_id: int,
        activo: bool,
        modificado_por_id: Optional[int] = None,
        modificado_por_nombre: str = "sistema",
    ) -> dict:
        """
        Activa o desactiva una bebida del menú.
        Corresponde a gestionar disponibilidad — CU63.
        """
        db = await database.get_db()

        drink = await db.fetchrow("SELECT * FROM drinks WHERE id = $1", drink_id)
        if not drink:
            raise KeyError(f"Bebida {drink_id} no encontrada.")

        row = await db.fetchrow(
            "UPDATE drinks SET activo = $2 WHERE id = $1 RETURNING id, nombre, activo",
            drink_id, activo,
        )

        accion = "activó" if activo else "desactivó"
        await self.registrar_auditoria(
            tipo_evento="modificar_menu",
            descripcion=f"Se {accion} la bebida '{drink['nombre']}' del menú.",
            usuario_id=modificado_por_id,
            nombre_usuario=modificado_por_nombre,
            entidad_afectada="drinks",
            entidad_id=str(drink_id),
            datos_anteriores={"activo": drink["activo"]},
            datos_nuevos={"activo": activo},
        )
        return dict(row)

    async def actualizar_precio_bebida(
        self,
        drink_id: int,
        precio_chico: Optional[float] = None,
        precio_mediano: Optional[float] = None,
        precio_grande: Optional[float] = None,
        modificado_por_id: Optional[int] = None,
        modificado_por_nombre: str = "sistema",
    ) -> dict:
        """Actualiza los precios de una bebida. CU63."""
        db = await database.get_db()

        drink = await db.fetchrow("SELECT * FROM drinks WHERE id = $1", drink_id)
        if not drink:
            raise KeyError(f"Bebida {drink_id} no encontrada.")

        campos = {}
        if precio_chico is not None:
            campos["precio_chico"] = precio_chico
        if precio_mediano is not None:
            campos["precio_mediano"] = precio_mediano
        if precio_grande is not None:
            campos["precio_grande"] = precio_grande

        if not campos:
            raise ValueError("Debe especificar al menos un precio para actualizar.")

        set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(campos))
        row = await db.fetchrow(
            f"UPDATE drinks SET {set_clauses} WHERE id = $1 "
            f"RETURNING id, nombre, precio_chico, precio_mediano, precio_grande",
            drink_id, *list(campos.values()),
        )

        await self.registrar_auditoria(
            tipo_evento="modificar_menu",
            descripcion=f"Se actualizaron precios de '{drink['nombre']}'.",
            usuario_id=modificado_por_id,
            nombre_usuario=modificado_por_nombre,
            entidad_afectada="drinks",
            entidad_id=str(drink_id),
            datos_anteriores={
                "precio_chico": float(drink.get("precio_chico", 0)),
                "precio_mediano": float(drink.get("precio_mediano", 0)),
                "precio_grande": float(drink.get("precio_grande", 0)),
            },
            datos_nuevos=campos,
        )
        return dict(row)

    async def actualizar_disponibilidad_bebida(
        self, drink_id: int, disponible: bool
    ) -> dict:
        """Marca una bebida como disponible/no disponible para pedidos. CU63."""
        db = await database.get_db()
        row = await db.fetchrow(
            "UPDATE drinks SET disponible = $2 WHERE id = $1 "
            "RETURNING id, nombre, disponible",
            drink_id, disponible,
        )
        if not row:
            raise KeyError(f"Bebida {drink_id} no encontrada.")
        return dict(row)

    # ══════════════════════════════════════════════════════
    # CU64 — Configurar umbrales de alertas de stock
    # ══════════════════════════════════════════════════════

    async def obtener_umbrales(self) -> AlertThreshold:
        """Retorna la configuración actual de umbrales."""
        db = await database.get_db()
        row = await db.fetchrow("SELECT * FROM alert_thresholds ORDER BY id DESC LIMIT 1")
        if not row:
            return AlertThreshold.defaults()
        return AlertThreshold.from_db_row(dict(row))

    async def configurar_umbrales(
        self,
        umbral_stock_minimo: Optional[float] = None,
        umbral_tiempo_prep: Optional[int] = None,
        umbral_ventas_bajas: Optional[float] = None,
        umbral_desperdicio: Optional[float] = None,
        modificado_por_id: Optional[int] = None,
        modificado_por_nombre: str = "gerente",
    ) -> AlertThreshold:
        """
        Aplica la configuración de umbrales.
        Corresponde al flujo completo del diagrama CU64:
          Configurar_umbral_stock_minimo()
          → Configurar_umbral_tiempo_preparacion()
          → Configurar_umbral_ventas_bajas()
          → Configurar_umbral_desperdicio()
          → Aplicar_configuracion_umbrales()
          → Confirmar_configuracion_exitosa()
        """
        db = await database.get_db()

        anterior = await self.obtener_umbrales()

        # Aplicar lógica de dominio con validaciones
        if umbral_stock_minimo is not None:
            anterior.configurar_umbral_stock_minimo(umbral_stock_minimo)
        if umbral_tiempo_prep is not None:
            anterior.configurar_umbral_tiempo_preparacion(umbral_tiempo_prep)
        if umbral_ventas_bajas is not None:
            anterior.configurar_umbral_ventas_bajas(umbral_ventas_bajas)
        if umbral_desperdicio is not None:
            anterior.configurar_umbral_desperdicio(umbral_desperdicio)

        anterior.aplicar_configuracion(modificado_por_id)

        # Upsert: actualizar si existe, insertar si no
        row = await db.fetchrow("""
            INSERT INTO alert_thresholds
                (umbral_stock_minimo, umbral_tiempo_prep,
                 umbral_ventas_bajas, umbral_desperdicio,
                 modificado_por, fecha_modificacion)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (id) DO UPDATE
               SET umbral_stock_minimo  = EXCLUDED.umbral_stock_minimo,
                   umbral_tiempo_prep   = EXCLUDED.umbral_tiempo_prep,
                   umbral_ventas_bajas  = EXCLUDED.umbral_ventas_bajas,
                   umbral_desperdicio   = EXCLUDED.umbral_desperdicio,
                   modificado_por       = EXCLUDED.modificado_por,
                   fecha_modificacion   = NOW()
            RETURNING *
        """,
            anterior.umbral_stock_minimo, anterior.umbral_tiempo_prep,
            anterior.umbral_ventas_bajas, anterior.umbral_desperdicio,
            modificado_por_id,
        )

        nuevo = AlertThreshold.from_db_row(dict(row))

        await self.registrar_auditoria(
            tipo_evento="configurar_umbrales",
            descripcion="Se actualizaron los umbrales de alertas del sistema.",
            usuario_id=modificado_por_id,
            nombre_usuario=modificado_por_nombre,
            entidad_afectada="alert_thresholds",
            entidad_id=str(nuevo.id),
            datos_anteriores={
                "umbral_stock_minimo": anterior.umbral_stock_minimo,
                "umbral_tiempo_prep": anterior.umbral_tiempo_prep,
                "umbral_ventas_bajas": anterior.umbral_ventas_bajas,
                "umbral_desperdicio": anterior.umbral_desperdicio,
            },
            datos_nuevos=nuevo.to_dict(),
        )
        return nuevo