"""
services/production_service.py
Módulo 02 — Producción y Operaciones (POM)

Servicio: ProductionService
Casos de uso: CU36, CU37, CU38, CU42, CU44, CU45, CU46, CU47

CORRECCIÓN: _actualizar_estado_db convierte estado dominio → valor real BD
  dominio       → BD
  en_preparacion → EnPreparacion
  lista          → ListaParaRecoger
  entregada      → Entregada
  cancelada      → Cancelada
  con_problema   → Cancelada
"""

from datetime import datetime
from typing import Optional

import database
from entities.order import Order, OrderItem, ESTADOS_VALIDOS


class ProductionService:

    # ── Conversión de estados ─────────────────────────────────────────

    ESTADO_A_DB = {
        "pendiente":      "Pendiente",
        "pagado":         "Pagado",
        "en_preparacion": "EnPreparacion",
        "lista":          "ListaParaRecoger",
        "entregada":      "Entregada",
        "cancelada":      "Cancelada",
        "rechazada":      "Rechazada",
        "con_problema":   "Cancelada",
    }

    # ── Helpers internos ──────────────────────────────────────────────

    async def _fetch_order(self, db, orden_id: str) -> Order:
        """Carga una orden con sus ítems desde la BD."""
        row = await db.fetchrow("""
            SELECT
                o.id, o.codigo_orden, o.estado,
                o.notas_generales, o.subtotal, o.descuento,
                o.propina, o.total,
                o.empleado_asignado_id,
                o.tiempo_preparacion_seg,
                o.entregada_a_tiempo,
                o.fecha_creacion,
                o.fecha_inicio_prep,
                o.fecha_lista,
                o.fecha_entrega,
                o.reporte_problema,
                u.nombre_completo AS cliente
            FROM orders o
            LEFT JOIN users u ON u.id = o.cliente_id
            WHERE o.id = $1::uuid
        """, orden_id)

        if not row:
            raise KeyError(f"Orden '{orden_id}' no encontrada.")

        items_rows = await db.fetch("""
            SELECT
                oi.id, oi.bebida_id, oi.tamano,
                oi.precio_final, oi.cantidad, oi.notas_item,
                d.nombre AS nombre_bebida, d.imagen_url
            FROM order_items oi
            JOIN drinks d ON d.id = oi.bebida_id
            WHERE oi.orden_id = $1::uuid
            ORDER BY oi.id
        """, orden_id)

        items = [
            OrderItem(
                id=r["id"],
                bebida_id=r["bebida_id"],
                nombre_bebida=r["nombre_bebida"],
                tamano=r["tamano"],
                cantidad=r["cantidad"],
                precio_final=float(r["precio_final"]),
                notas_item=r.get("notas_item"),
                imagen_url=r.get("imagen_url"),
            )
            for r in items_rows
        ]
        return Order.from_db_row(dict(row), items)

    async def _actualizar_estado_db(
        self,
        db,
        orden: Order,
        campos_extra: Optional[dict] = None,
    ) -> None:
        """
        Persiste el estado y campos extra de la orden.
        Convierte el estado del dominio al valor real del CHECK constraint de la BD.
        """
        # Convertir estado dominio → valor real del CHECK constraint
        estado_db = self.ESTADO_A_DB.get(orden.estado, orden.estado)

        campos = {
            "estado":                 estado_db,
            "empleado_asignado_id":   orden.empleado_asignado_id,
            "tiempo_preparacion_seg": orden.tiempo_preparacion_seg,
            "entregada_a_tiempo":     orden.entregada_a_tiempo,
            "fecha_inicio_prep":      orden.fecha_inicio_prep,
            "fecha_lista":            orden.fecha_lista,
            "fecha_entrega":          orden.fecha_entrega,
            "reporte_problema":       orden.reporte_problema,
        }
        if campos_extra:
            campos.update(campos_extra)

        set_clauses = ", ".join(
            f"{k} = ${i+2}" for i, k in enumerate(campos)
        )
        await db.execute(
            f"UPDATE orders SET {set_clauses}, fecha_actualizacion = NOW() "
            f"WHERE id = $1::uuid",
            orden.id, *list(campos.values()),
        )

    # ══════════════════════════════════════════════════════
    # CU36 — Recibir orden de producción
    # ══════════════════════════════════════════════════════

    async def recibir_orden_produccion(self, orden_id: str) -> Order:
        """
        Retorna la orden recién llegada a producción.
        Corresponde a Enviar_orden_produccion() → Enviar_fecha_estimada() — CU36.
        """
        db = await database.get_db()
        return await self._fetch_order(db, orden_id)

    async def listar_ordenes_produccion(
        self,
        estado: Optional[str] = None,
        empleado_id: Optional[int] = None,
    ) -> list[dict]:
        """
        Lista las órdenes activas en producción. CU36.
        Excluye las terminales usando los valores reales del CHECK.
        """
        db = await database.get_db()

        # Valores reales del CHECK constraint — excluir terminales
        condiciones = ["o.estado NOT IN ('Cancelada', 'Entregada', 'Rechazada')"]
        params: list = []
        p = 1

        if estado:
            # Convertir si viene en formato dominio
            estado_db = self.ESTADO_A_DB.get(estado, estado)
            condiciones.append(f"o.estado = ${p}")
            params.append(estado_db)
            p += 1
        if empleado_id:
            condiciones.append(f"o.empleado_asignado_id = ${p}")
            params.append(empleado_id)
            p += 1

        where = " AND ".join(condiciones)

        rows = await db.fetch(f"""
            SELECT
                o.id, o.codigo_orden, o.estado,
                o.notas_generales, o.total,
                o.empleado_asignado_id,
                o.fecha_creacion,
                o.fecha_inicio_prep,
                u.nombre_completo AS cliente,
                COUNT(oi.id) AS total_items
            FROM orders o
            LEFT JOIN users u ON u.id = o.cliente_id
            LEFT JOIN order_items oi ON oi.orden_id = o.id
            WHERE {where}
            GROUP BY o.id, u.nombre_completo
            ORDER BY o.fecha_creacion ASC
        """, *params)

        # Enriquecer con items para el frontend
        resultado = []
        for r in rows:
            d = dict(r)
            # Cargar items de la orden
            items_rows = await db.fetch("""
                SELECT oi.id, oi.bebida_id, oi.tamano, oi.cantidad,
                       oi.precio_final, oi.notas_item,
                       dr.nombre AS nombre_bebida
                FROM order_items oi
                JOIN drinks dr ON dr.id = oi.bebida_id
                WHERE oi.orden_id = $1::uuid
            """, str(r["id"]))
            d["items"] = [dict(i) for i in items_rows]
            d["nombre_cliente"] = d.pop("cliente", "")
            resultado.append(d)

        return resultado

    # ══════════════════════════════════════════════════════
    # CU37 — Ver detalles completos de la orden
    # ══════════════════════════════════════════════════════

    async def obtener_detalle_orden(self, orden_id: str) -> Order:
        """Retorna todos los datos de la orden incluyendo ítems y notas. CU37."""
        db = await database.get_db()
        return await self._fetch_order(db, orden_id)

    # ══════════════════════════════════════════════════════
    # CU38 — Marcar orden como 'en preparación'
    # ══════════════════════════════════════════════════════

    async def marcar_en_preparacion(
        self, orden_id: str, empleado_id: Optional[int] = None
    ) -> Order:
        """
        Cambia el estado a 'en_preparacion' y asigna al barista.
        Corresponde a actualizarEstado('EnPreparacion') — CU38.
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        orden.empleado_asignado_id = empleado_id
        orden.cambiar_estado("en_preparacion")
        await self._actualizar_estado_db(db, orden)
        return orden

    # ══════════════════════════════════════════════════════
    # CU42 — Marcar orden como 'lista para recoger'
    # ══════════════════════════════════════════════════════

    async def marcar_lista(self, orden_id: str, umbral_seg: int = 600) -> Order:
        """
        Cambia estado a 'lista' y calcula el tiempo de preparación.
        Corresponde a actualizarEstado('ListaParaRecoger') — CU42.
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        orden.cambiar_estado("lista")

        # CU47: registrar tiempo automáticamente al marcar lista
        if orden.fecha_inicio_prep:
            try:
                orden.registrar_tiempo_preparacion(umbral_seg)
            except ValueError:
                pass

        await self._actualizar_estado_db(db, orden)
        return orden

    async def revertir_a_en_preparacion(self, orden_id: str) -> Order:
        """
        Deshace el marcado como lista.
        Corresponde a revertirEstado('EnPreparacion') — CU42.
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        orden.revertir_a_en_preparacion()
        await self._actualizar_estado_db(db, orden)
        return orden

    # ══════════════════════════════════════════════════════
    # CU44 — Marcar orden como 'entregada'
    # ══════════════════════════════════════════════════════

    async def marcar_entregada(self, orden_id: str) -> Order:
        """
        Finaliza el ciclo de producción. CU44.
        Corresponde a cambiarEstado('Entregada').
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        orden.cambiar_estado("entregada")
        await self._actualizar_estado_db(db, orden)
        return orden

    # ══════════════════════════════════════════════════════
    # CU45 — Reportar problema con la orden
    # ══════════════════════════════════════════════════════

    async def reportar_problema(
        self, orden_id: str, descripcion: str
    ) -> Order:
        """
        Marca la orden con problema y registra la descripción. CU45.
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        orden.reportar_problema(descripcion)
        await self._actualizar_estado_db(db, orden)
        return orden

    # ══════════════════════════════════════════════════════
    # CU46 — Reimprimir ticket de orden
    # ══════════════════════════════════════════════════════

    async def obtener_ticket(self, orden_id: str) -> dict:
        """
        Retorna los datos necesarios para reimprimir el ticket. CU46.
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        return {
            "codigo_orden": orden.codigo_orden,
            "estado": orden.estado,
            "cliente": orden.nombre_cliente,
            "items": [i.to_dict() for i in orden.items],
            "total": orden.total,
            "notas": orden.notas_generales,
            "fecha": orden.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
            "listo_para_impresora": True,
        }

    # ══════════════════════════════════════════════════════
    # CU47 — Registrar tiempo de preparación
    # ══════════════════════════════════════════════════════

    async def registrar_tiempo_preparacion(
        self, orden_id: str, umbral_seg: int = 600
    ) -> dict:
        """
        Calcula y persiste el tiempo de preparación. CU47.
        Si no hay fecha_inicio_prep o fecha_lista retorna sin error.
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)

        # Solo calcular si hay fechas disponibles
        if not orden.fecha_inicio_prep or not orden.fecha_lista:
            return {
                "orden_id": orden_id,
                "tiempo_preparacion_seg": orden.tiempo_preparacion_seg,
                "tiempo_preparacion_min": round((orden.tiempo_preparacion_seg or 0) / 60, 1),
                "entregada_a_tiempo": orden.entregada_a_tiempo,
                "umbral_seg": umbral_seg,
                "nota": "Sin fechas de preparación registradas aún",
            }

        tiempo = orden.registrar_tiempo_preparacion(umbral_seg)
        await self._actualizar_estado_db(db, orden)
        return {
            "orden_id": orden_id,
            "tiempo_preparacion_seg": tiempo,
            "tiempo_preparacion_min": round(tiempo / 60, 1),
            "entregada_a_tiempo": orden.entregada_a_tiempo,
            "umbral_seg": umbral_seg,
        }

    # ══════════════════════════════════════════════════════
    # Usado por M01 — CU14 cancelar
    # ══════════════════════════════════════════════════════

    async def consultar_estado_produccion(self, orden_id: str) -> str:
        """Retorna el estado actual. Usado por M01 CU14."""
        db = await database.get_db()
        estado = await db.fetchval(
            "SELECT estado FROM orders WHERE id = $1::uuid", orden_id
        )
        if not estado:
            raise KeyError(f"Orden '{orden_id}' no encontrada.")
        return estado

    async def cancelar_en_produccion(self, orden_id: str) -> bool:
        """Cancela una orden si aún está en estado cancelable. CU14."""
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        try:
            orden.cambiar_estado("cancelada")
            await self._actualizar_estado_db(db, orden)
            return True
        except ValueError:
            return False