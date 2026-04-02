"""
services/sales_service.py
Módulo 03 — Gestión y Administración (MAM)

Servicio: SalesService
Casos de uso: CU54, CU60, CU61, CU62

Accede a las tablas orders, order_items, drinks para generar reportes.
"""

from datetime import datetime
import database


class SalesService:
    """
    Capa de servicio para datos de ventas.

    Provee los métodos que ReportsController consume para
    construir los reportes del gerente.
    """

    # ── CU60 — Reporte de ventas ──────────────────────────────────────

    async def obtener_ventas_periodo(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> dict:
        """
        Resumen de ventas: total, órdenes, promedio, desglose por día.
        Corresponde a solicitarVentasPeriodo() — diagrama CU54.
        """
        db = await database.get_db()

        resumen = await db.fetchrow("""
            SELECT
                COUNT(*)                    AS total_ordenes,
                COALESCE(SUM(total), 0)     AS total_ventas,
                COALESCE(AVG(total), 0)     AS promedio_orden,
                COALESCE(SUM(descuento), 0) AS total_descuentos,
                COALESCE(SUM(propina),  0)  AS total_propinas
            FROM orders
            WHERE estado NOT IN ('cancelada', 'rechazada')
              AND fecha_creacion BETWEEN $1 AND $2
        """, fecha_inicio, fecha_fin)

        por_dia = await db.fetch("""
            SELECT
                DATE(fecha_creacion)       AS dia,
                COUNT(*)                   AS ordenes,
                COALESCE(SUM(total), 0)    AS ventas
            FROM orders
            WHERE estado NOT IN ('cancelada', 'rechazada')
              AND fecha_creacion BETWEEN $1 AND $2
            GROUP BY DATE(fecha_creacion)
            ORDER BY dia
        """, fecha_inicio, fecha_fin)

        return {
            "periodo": {
                "inicio": fecha_inicio.isoformat(),
                "fin": fecha_fin.isoformat(),
            },
            "resumen": dict(resumen),
            "por_dia": [dict(r) for r in por_dia],
        }

    # ── CU54 — Ingredientes descontados por ventas ───────────────────

    async def obtener_ingredientes_descontados(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> list[dict]:
        """
        Retorna los ingredientes consumidos en el periodo según recetas × ventas.
        Corresponde a obtenerIngredientesDescontados() — diagrama CU54.
        """
        db = await database.get_db()

        rows = await db.fetch("""
            SELECT
                i.id AS ingrediente_id,
                i.nombre,
                i.unidad_medida,
                COALESCE(SUM(oi.cantidad * di.cantidad_base), 0) AS cantidad_consumida,
                COALESCE(
                    SUM(oi.cantidad * di.cantidad_base) * i.costo_unitario, 0
                ) AS costo_total_consumo
            FROM ingredients i
            JOIN drink_ingredients di ON di.ingrediente_id = i.id
            JOIN order_items oi ON oi.bebida_id = di.bebida_id
            JOIN orders o ON o.id = oi.orden_id
                AND o.estado NOT IN ('cancelada', 'rechazada')
                AND o.fecha_creacion BETWEEN $1 AND $2
            GROUP BY i.id, i.nombre, i.unidad_medida, i.costo_unitario
            ORDER BY cantidad_consumida DESC
        """, fecha_inicio, fecha_fin)

        return [dict(r) for r in rows]

    # ── CU61 — Análisis de bebidas populares ─────────────────────────

    async def obtener_bebidas_populares(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        top_n: int = 10,
    ) -> list[dict]:
        """
        Ranking de bebidas más vendidas en el periodo.
        """
        db = await database.get_db()

        rows = await db.fetch("""
            SELECT
                d.id,
                d.nombre                                        AS bebida,
                d.imagen_url,
                c.nombre                                        AS categoria,
                SUM(oi.cantidad)                                AS unidades_vendidas,
                SUM(oi.precio_final * oi.cantidad)              AS ingresos_generados,
                COUNT(DISTINCT oi.orden_id)                     AS aparece_en_ordenes
            FROM order_items oi
            JOIN drinks d ON d.id = oi.bebida_id
            JOIN categories c ON c.id = d.categoria_id
            JOIN orders o ON o.id = oi.orden_id
            WHERE o.estado NOT IN ('cancelada', 'rechazada')
              AND o.fecha_creacion BETWEEN $1 AND $2
            GROUP BY d.id, d.nombre, d.imagen_url, c.nombre
            ORDER BY unidades_vendidas DESC
            LIMIT $3
        """, fecha_inicio, fecha_fin, top_n)

        return [dict(r) for r in rows]

    # ── CU62 — Eficiencia de preparación ─────────────────────────────

    async def obtener_eficiencia_preparacion(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> dict:
        """
        Tiempo promedio de preparación y porcentaje de órdenes a tiempo.
        """
        db = await database.get_db()

        resumen = await db.fetchrow("""
            SELECT
                COUNT(*)                                            AS total_ordenes,
                ROUND(AVG(tiempo_preparacion_seg)::numeric, 1)     AS tiempo_promedio_seg,
                ROUND(AVG(tiempo_preparacion_seg)::numeric / 60, 2) AS tiempo_promedio_min,
                COUNT(*) FILTER (WHERE entregada_a_tiempo = TRUE)  AS ordenes_a_tiempo,
                ROUND(
                    COUNT(*) FILTER (WHERE entregada_a_tiempo = TRUE)::numeric
                    / NULLIF(COUNT(*), 0) * 100, 1
                )                                                   AS pct_a_tiempo
            FROM orders
            WHERE estado = 'entregada'
              AND fecha_creacion BETWEEN $1 AND $2
        """, fecha_inicio, fecha_fin)

        por_hora = await db.fetch("""
            SELECT
                EXTRACT(HOUR FROM fecha_creacion)               AS hora,
                COUNT(*)                                        AS ordenes,
                ROUND(AVG(tiempo_preparacion_seg)::numeric, 1) AS tiempo_promedio_seg
            FROM orders
            WHERE estado = 'entregada'
              AND fecha_creacion BETWEEN $1 AND $2
            GROUP BY hora
            ORDER BY hora
        """, fecha_inicio, fecha_fin)

        return {
            "periodo": {"inicio": fecha_inicio.isoformat(), "fin": fecha_fin.isoformat()},
            "resumen": dict(resumen),
            "por_hora": [dict(r) for r in por_hora],
        }