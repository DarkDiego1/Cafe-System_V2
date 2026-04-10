"""
services/order_service.py
Módulo 01 — Experiencia del Cliente (CEM)
CU04, CU05, CU12, CU14, CU21, CU22, CU23

Estados reales de orders:
  'Pendiente' | 'Pagado' | 'EnPreparacion' | 'ListaParaRecoger'
  | 'Entregada' | 'Cancelada' | 'Rechazada'

Tamaños reales de order_items:
  'Chico' | 'Mediano' | 'Grande'
"""

from datetime import datetime
from typing import Optional
import database


# Mapa de tamaño normalizado → valor real de la BD
TAMANO_MAP = {
    "chico":   "Chico",
    "mediano": "Mediano",
    "grande":  "Grande",
    "Chico":   "Chico",
    "Mediano": "Mediano",
    "Grande":  "Grande",
}

# Estados cancelables antes de que entren a producción
ESTADOS_CANCELABLES = {"pendiente", "pagado", "Pendiente", "Pagado"}


class OrderService:

    # ── CU05: precio en tiempo real ───────────────────────────────────

    async def recalcular_total(
        self,
        bebida_id: int,
        tamano: str,
        ingredientes_personalizados: list[dict],
    ) -> dict:
        """Corresponde a recalcularTotal() — CU05."""
        db = await database.get_db()
        col = {
            "chico": "precio_chico", "mediano": "precio_mediano",
            "grande": "precio_grande",
        }.get(tamano.lower(), "precio_mediano")

        precio_base = float(await db.fetchval(
            f"SELECT {col} FROM drinks WHERE id = $1", bebida_id
        ) or 0)

        costo_extras = 0.0
        for item in ingredientes_personalizados:
            ing = await db.fetchrow(
                "SELECT costo_unitario FROM ingredients WHERE id = $1",
                item.get("ingrediente_id"),
            )
            if ing:
                cantidad_extra = max(0, item.get("cantidad", 0) - 1)
                costo_extras += float(ing["costo_unitario"]) * cantidad_extra

        total = round(precio_base + costo_extras, 2)
        return {
            "precio_base":  precio_base,
            "costo_extras": round(costo_extras, 2),
            "total":        total,
        }

    # ── CU12: crear orden ─────────────────────────────────────────────

    async def crear_orden(
        self,
        cliente_id: str,
        items: list[dict],
        notas_generales: Optional[str] = None,
        cupon_codigo: Optional[str]    = None,
        hora_recogida: Optional[datetime] = None,
    ) -> dict:
        """Corresponde a añadirProductoPersonalizado() → confirmarAñadido() — CU12."""
        db = await database.get_db()

        subtotal = sum(
            float(item.get("precio_final", 0)) * int(item.get("cantidad", 1))
            for item in items
        )

        # Aplicar cupón si existe
        descuento = 0.0
        if cupon_codigo:
            cupon_row = await db.fetchrow(
                "SELECT * FROM coupons WHERE codigo = $1 AND activo = TRUE",
                cupon_codigo,
            )
            if cupon_row:
                from entities.coupon import Coupon
                c = Coupon.from_db_row(dict(cupon_row))
                valido, _ = c.es_valido()
                if valido:
                    descuento = c.calcular_descuento(subtotal)

        total = round(subtotal - descuento, 2)

        # Código único de orden
        ultimo = await db.fetchval("SELECT COUNT(*) FROM orders") or 0
        codigo_orden = f"ORD-{datetime.now().strftime('%Y%m%d')}-{str(ultimo + 1).zfill(4)}"

        # Usar acquire() para obtener una conexión real del pool y poder usar transaction()
        async with db.acquire() as conn:
            async with conn.transaction():
                orden = await conn.fetchrow("""
                    INSERT INTO orders
                        (cliente_id, codigo_orden, estado, subtotal, descuento,
                         total, notas_generales, cupon_codigo,
                         fecha_creacion, fecha_actualizacion)
                    VALUES ($1::uuid, $2, 'Pendiente', $3, $4, $5, $6, $7, NOW(), NOW())
                    RETURNING id, codigo_orden, total
                """, cliente_id, codigo_orden, subtotal, descuento,
                    total, notas_generales, cupon_codigo)

                orden_id = str(orden["id"])

                for item in items:
                    tamano_real = TAMANO_MAP.get(
                        item.get("tamano", "Mediano"), "Mediano"
                    )
                    await conn.execute("""
                        INSERT INTO order_items
                            (orden_id, bebida_id, tamano, precio_base,
                             precio_final, cantidad, notas_item)
                        VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)
                    """,
                        orden_id,
                        item["bebida_id"],
                        tamano_real,
                        float(item.get("precio_base", 0)),
                        float(item.get("precio_final", 0)),
                        int(item.get("cantidad", 1)),
                        item.get("notas_item"),
                    )

        return {
            "orden_id":     orden_id,
            "codigo_orden": codigo_orden,
            "total":        total,
        }

    # ── CU14: cancelar ────────────────────────────────────────────────

    async def solicitar_cancelacion(self, orden_id: str) -> dict:
        """Corresponde a solicitarCancelacion(numeroPedido) — CU14."""
        db     = await database.get_db()
        estado = await db.fetchval(
            "SELECT estado FROM orders WHERE id = $1::uuid", orden_id
        )
        if not estado:
            raise KeyError(f"Orden '{orden_id}' no encontrada.")

        if estado not in ESTADOS_CANCELABLES:
            return {
                "cancelada": False,
                "mensaje": (
                    "No se puede cancelar: la orden ya está en preparación. "
                    "Por favor acude a la barra."
                ),
            }

        await db.execute("""
            UPDATE orders
            SET estado = 'Cancelada', fecha_actualizacion = NOW()
            WHERE id = $1::uuid
        """, orden_id)
        return {"cancelada": True, "mensaje": "Orden cancelada exitosamente."}

    # ── CU22: historial ───────────────────────────────────────────────

    async def obtener_historial(
        self, cliente_id: str, limit: int = 20
    ) -> list[dict]:
        """CU22 — Ver historial de pedidos."""
        db   = await database.get_db()
        rows = await db.fetch("""
            SELECT
                o.id, o.codigo_orden, o.estado,
                o.total, o.fecha_creacion,
                COUNT(oi.id) AS total_items
            FROM orders o
            LEFT JOIN order_items oi ON oi.orden_id = o.id
            WHERE o.cliente_id = $1::uuid
            GROUP BY o.id
            ORDER BY o.fecha_creacion DESC
            LIMIT $2
        """, cliente_id, limit)
        return [dict(r) for r in rows]

    # ── CU23: reordenar ───────────────────────────────────────────────

    async def reordenar(self, orden_id_original: str, cliente_id: str) -> dict:
        """CU23 — Reordenar con un clic."""
        db    = await database.get_db()
        items = await db.fetch("""
            SELECT bebida_id, tamano, precio_base, precio_final,
                   cantidad, notas_item
            FROM order_items WHERE orden_id = $1::uuid
        """, orden_id_original)
        if not items:
            raise KeyError("Orden original no encontrada o sin ítems.")
        return await self.crear_orden(
            cliente_id=cliente_id,
            items=[dict(i) for i in items],
        )

    # ── CU21: favoritas ───────────────────────────────────────────────

    async def guardar_favorita(
        self, cliente_id: str, bebida_id: int, nombre: str
    ) -> dict:
        """CU21 — Guardar receta favorita."""
        db  = await database.get_db()
        row = await db.fetchrow("""
            INSERT INTO favorite_drinks
                (cliente_id, bebida_id, nombre, fecha_guardado)
            VALUES ($1::uuid, $2, $3, NOW())
            ON CONFLICT (cliente_id, bebida_id)
            DO UPDATE SET nombre = EXCLUDED.nombre
            RETURNING *
        """, cliente_id, bebida_id, nombre)
        return dict(row)

    async def obtener_favoritas(self, cliente_id: str) -> list[dict]:
        """CU21 — Ver favoritas."""
        db   = await database.get_db()
        rows = await db.fetch("""
            SELECT fd.id, fd.nombre, fd.fecha_guardado,
                   d.nombre AS bebida, d.imagen_url
            FROM favorite_drinks fd
            JOIN drinks d ON d.id = fd.bebida_id
            WHERE fd.cliente_id = $1::uuid
            ORDER BY fd.fecha_guardado DESC
        """, cliente_id)
        return [dict(r) for r in rows]