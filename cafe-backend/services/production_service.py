"""
services/production_service.py
Módulo 02 — Producción y Operaciones (POM)

Servicio: ProductionService
Casos de uso: CU36, CU37, CU38, CU42, CU44, CU45, CU46, CU47

Orquesta el ciclo de vida de las órdenes desde que llegan
a producción hasta que se entregan al cliente.
Comparte la tabla `orders` con M01 — solo lee/escribe columnas propias.
"""

from datetime import datetime
from typing import Optional

import database
from entities.order import Order, OrderItem, ESTADOS_VALIDOS


class ProductionService:
    """
    Servicio de producción que gestiona el flujo completo de una orden
    desde su recepción hasta su entrega.

    Lee la tabla `orders` (creada por M01) y actualiza:
      - estado
      - empleado_asignado_id
      - tiempo_preparacion_seg
      - entregada_a_tiempo
      - fecha_inicio_prep, fecha_lista, fecha_entrega
    """

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
        """Persiste el estado y campos extra de la orden."""
        campos = {
            "estado": orden.estado,
            "empleado_asignado_id": orden.empleado_asignado_id,
            "tiempo_preparacion_seg": orden.tiempo_preparacion_seg,
            "entregada_a_tiempo": orden.entregada_a_tiempo,
            "fecha_inicio_prep": orden.fecha_inicio_prep,
            "fecha_lista": orden.fecha_lista,
            "fecha_entrega": orden.fecha_entrega,
            "reporte_problema": orden.reporte_problema,
        }
        if campos_extra:
            campos.update(campos_extra)

        set_clauses = ", ".join(
            f"{k} = ${i+2}" for i, k in enumerate(campos)
        )
        await db.execute(
            f"UPDATE orders SET {set_clauses} WHERE id = $1::uuid",
            orden.id, *list(campos.values()),
        )

    # ══════════════════════════════════════════════════════
    # CU36 — Recibir orden de producción
    # ══════════════════════════════════════════════════════

    async def recibir_orden_produccion(self, orden_id: str) -> Order:
        """
        Retorna la orden recién llegada a producción con fecha estimada.
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
        Lista las órdenes activas en producción, filtradas por estado
        o por barista asignado. CU36.
        """
        db = await database.get_db()

        condiciones = ["o.estado NOT IN ('cancelada', 'entregada')"]
        params: list = []
        p = 1

        if estado:
            condiciones.append(f"o.estado = ${p}")
            params.append(estado)
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

        return [dict(r) for r in rows]

    # ══════════════════════════════════════════════════════
    # CU37 — Ver detalles completos de la orden
    # ══════════════════════════════════════════════════════

    async def obtener_detalle_orden(self, orden_id: str) -> Order:
        """
        Retorna todos los datos de la orden incluyendo ítems, notas
        y personalización. CU37.
        """
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
        También dispara el evento para CU43 (lo maneja NotificationService).
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        orden.cambiar_estado("lista")

        # CU47: registrar tiempo automáticamente al marcar lista
        if orden.fecha_inicio_prep:
            try:
                orden.registrar_tiempo_preparacion(umbral_seg)
            except ValueError:
                pass  # si no hay fecha_inicio_prep no bloquea

        await self._actualizar_estado_db(db, orden)
        return orden

    async def revertir_a_en_preparacion(self, orden_id: str) -> Order:
        """
        Deshace el marcado como lista (ventana de 5 seg en la UI).
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
        Finaliza el ciclo de producción marcando la orden como entregada.
        Corresponde a cambiarEstado('Entregada') — CU44.
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
        Marca la orden con problema y registra la descripción.
        Corresponde al flujo CU45.
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
        Retorna los datos necesarios para reimprimir el ticket.
        Corresponde a Proporcionar_numero_orden() → Enviar_a_impresora() — CU46.
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
        Calcula y persiste el tiempo de preparación de la orden.
        Alimenta las métricas del M03 (CU62).
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
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
    # Consultar estado (usado por M01 — CU14 cancelar)
    # ══════════════════════════════════════════════════════

    async def consultar_estado_produccion(self, orden_id: str) -> str:
        """
        Retorna el estado actual de producción.
        Usado por M01 para verificar si una orden es cancelable.
        Corresponde a consultarEstadoProduccion() — CU14.
        """
        db = await database.get_db()
        estado = await db.fetchval(
            "SELECT estado FROM orders WHERE id = $1::uuid", orden_id
        )
        if not estado:
            raise KeyError(f"Orden '{orden_id}' no encontrada.")
        return estado

    async def cancelar_en_produccion(self, orden_id: str) -> bool:
        """
        Cancela una orden si aún está en estado cancelable.
        Usado por M01 CU14. Retorna True si se canceló.
        """
        db = await database.get_db()
        orden = await self._fetch_order(db, orden_id)
        try:
            orden.cambiar_estado("cancelada")
            await self._actualizar_estado_db(db, orden)
            return True
        except ValueError:
            return False