"""
services/payment_service.py
Módulo 01 — Experiencia del Cliente (CEM)
CU13, CU15, CU29, CU30, CU31, CU32, CU33, CU34, CU35, CU68, CU70, CU73

Columnas reales de coupons:
  valor_descuento, usos_maximos, activo, usuario_especifico_id
  tipo_descuento: 'Porcentaje' | 'MontoFijo' | 'BebidaGratis'

Estados reales de orders:
  'Pagado' | 'Rechazada' | 'Cancelada'
"""

from datetime import datetime, date
from typing import Optional
import database
from entities.coupon import Coupon


class PaymentGatewayService:
    """CU29, CU32, CU33, CU34, CU35."""

    async def procesar_pago_tarjeta(
        self, orden_id: str, monto: float, token_tarjeta: str
    ) -> dict:
        """CU29 — Procesar pago con tarjeta."""
        txn_id = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        return {"exitoso": True, "transaccion_id": txn_id,
                "monto": monto, "metodo": "tarjeta"}

    async def procesar_webhook(self, payload: dict) -> dict:
        """CU32 — Confirmar pago vía webhook."""
        db     = await database.get_db()
        status = payload.get("status")
        oid    = payload.get("orden_id")
        txn    = payload.get("transaccion_id")

        if status == "succeeded":
            await db.execute("""
                UPDATE orders
                SET estado = 'Pagado', transaccion_id = $2,
                    fecha_actualizacion = NOW()
                WHERE id = $1::uuid
            """, oid, txn)
            return {"procesado": True, "nuevo_estado": "Pagado"}

        await db.execute("""
            UPDATE orders
            SET estado = 'Rechazada', fecha_actualizacion = NOW()
            WHERE id = $1::uuid
        """, oid)
        return {"procesado": True, "nuevo_estado": "Rechazada"}

    async def registrar_transaccion(
        self, orden_id: str, transaccion_id: str
    ) -> None:
        """CU32 — registrarIDTransaccion()."""
        db = await database.get_db()
        await db.execute("""
            UPDATE orders SET transaccion_id = $2, fecha_actualizacion = NOW()
            WHERE id = $1::uuid
        """, orden_id, transaccion_id)

    async def manejar_pago_rechazado(self, orden_id: str, motivo: str) -> dict:
        """CU33."""
        db = await database.get_db()
        await db.execute("""
            UPDATE orders
            SET estado = 'Rechazada', fecha_actualizacion = NOW()
            WHERE id = $1::uuid
        """, orden_id)
        return {"rechazada": True, "motivo": motivo}

    async def dejar_propina(self, orden_id: str, monto_propina: float) -> dict:
        """CU35 — Dejar propina digital."""
        db = await database.get_db()
        await db.execute("""
            UPDATE orders
            SET propina = $2, total = total + $2, fecha_actualizacion = NOW()
            WHERE id = $1::uuid
        """, orden_id, monto_propina)
        return {"propina_registrada": True, "monto": monto_propina}


class WalletSdkService:
    """CU30."""

    async def procesar_pago_billetera(
        self, orden_id: str, monto: float,
        wallet_token: str, tipo: str = "apple_pay"
    ) -> dict:
        """CU30 — Pago con billetera digital."""
        txn_id = f"WAL-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        db = await database.get_db()
        await db.execute("""
            UPDATE orders
            SET estado = 'Pagado', transaccion_id = $2,
                metodo_pago = $3, fecha_actualizacion = NOW()
            WHERE id = $1::uuid
        """, orden_id, txn_id, tipo)
        return {"exitoso": True, "transaccion_id": txn_id,
                "monto": monto, "metodo": tipo}


class CouponService:
    """CU31, CU68, CU70, CU73."""

    async def verificar_cupon(
        self, codigo: str, cliente_id: Optional[str] = None
    ) -> dict:
        """Corresponde a verificarCupon(codigo) — CU31."""
        db  = await database.get_db()
        row = await db.fetchrow(
            "SELECT * FROM coupons WHERE codigo = $1", codigo
        )
        if not row:
            return {"valido": False, "motivo": "El código de cupón no existe."}

        cupon = Coupon.from_db_row(dict(row))

        if cupon.user_id and cliente_id and cupon.user_id != cliente_id:
            return {"valido": False, "motivo": "Este cupón no pertenece a tu cuenta."}

        valido, motivo = cupon.es_valido()
        return {
            "valido":          valido,
            "motivo":          motivo,
            "descuento":       cupon.descuento if valido else 0,
            "tipo_descuento":  cupon.tipo_descuento,
            "codigo":          codigo,
        }

    async def aplicar_cupon(self, orden_id: str, codigo: str) -> dict:
        """Corresponde a aplicarDescuento() — CU31."""
        db    = await database.get_db()
        orden = await db.fetchrow(
            "SELECT subtotal FROM orders WHERE id = $1::uuid", orden_id
        )
        if not orden:
            raise KeyError(f"Orden {orden_id} no encontrada.")

        resultado = await self.verificar_cupon(codigo)
        if not resultado["valido"]:
            return resultado

        cupon_row = await db.fetchrow(
            "SELECT * FROM coupons WHERE codigo = $1", codigo
        )
        cupon     = Coupon.from_db_row(dict(cupon_row))
        descuento = cupon.calcular_descuento(float(orden["subtotal"]))

        async with db.transaction():
            await db.execute("""
                UPDATE orders
                SET descuento = $2, total = subtotal - $2,
                    cupon_codigo = $3, fecha_actualizacion = NOW()
                WHERE id = $1::uuid
            """, orden_id, descuento, codigo)

            # Incrementar usos_actuales (columna real)
            await db.execute("""
                UPDATE coupons
                SET usos_actuales = usos_actuales + 1
                WHERE codigo = $1
            """, codigo)

        return {"valido": True, "descuento_aplicado": descuento, "codigo": codigo}

    async def generar_cupon_cumpleanos(self, user_id: str) -> Coupon:
        """Corresponde a generarCuponUnico() — CU70."""
        db    = await database.get_db()
        cupon = Coupon.generar_cupon_unico(
            descuento=15.0, tipo_descuento="Porcentaje", user_id=user_id
        )
        row = await db.fetchrow("""
            INSERT INTO coupons
                (codigo, valor_descuento, tipo_descuento, activo,
                 fecha_inicio, fecha_fin, usos_maximos, usos_actuales,
                 usuario_especifico_id, origen)
            VALUES ($1, $2, $3, TRUE, $4, $5, 1, 0, $6::uuid, 'Cumpleaños')
            RETURNING *
        """,
            cupon.codigo, cupon.descuento, cupon.tipo_descuento,
            cupon.fecha_inicio, cupon.fecha_fin, user_id,
        )
        return Coupon.from_db_row(dict(row))


class EmailService:
    """CU13, CU18, CU34, CU70."""

    async def enviar_correo_recibo(self, correo: str, orden_id: str) -> dict:
        """CU13/CU34 — Enviar recibo por correo."""
        db    = await database.get_db()
        orden = await db.fetchrow(
            "SELECT codigo_orden, total FROM orders WHERE id = $1::uuid", orden_id
        )
        if not orden:
            raise KeyError("Orden no encontrada.")

        # Registrar notificación usando columnas reales
        await db.execute("""
            INSERT INTO notifications
                (usuario_id, tipo, titulo, mensaje, leida, fecha_creacion, fecha_envio, enviada)
            SELECT cliente_id, 'Sistema',
                   'Recibo de tu orden ' || $2,
                   'Tu compra por $' || $3 || ' ha sido procesada.',
                   FALSE, NOW(), NOW(), TRUE
            FROM orders WHERE id = $1::uuid AND cliente_id IS NOT NULL
        """, orden_id, orden["codigo_orden"], orden["total"])

        return {"enviado": True, "destinatario": correo,
                "orden": orden["codigo_orden"]}

    async def enviar_correo_recuperacion(self, correo: str, token: str) -> dict:
        """CU18."""
        enlace = f"https://cafenuevoshorizontes.com/reset-password?token={token}"
        return {"enviado": True, "destinatario": correo, "enlace": enlace}

    def confirmacion_envio(self, correo: str) -> dict:
        return {"confirmado": True, "correo": correo}

    def error_envio(self, correo: str, error: str) -> dict:
        return {"confirmado": False, "correo": correo, "error": error}


class PromotionsService:
    """CU15, CU73."""

    async def obtener_promociones_vigentes(self) -> list[dict]:
        """CU15 — Ver promociones vigentes."""
        db   = await database.get_db()
        rows = await db.fetch("""
            SELECT id, titulo, descripcion, imagen_url,
                   descuento, fecha_inicio, fecha_fin, codigo_qr
            FROM promotions
            WHERE activa = TRUE
              AND fecha_inicio <= NOW()
              AND fecha_fin    >= NOW()
            ORDER BY fecha_fin ASC
        """)
        return [dict(r) for r in rows]

    async def aplicar_promocion_qr(
        self, codigo_qr: str, orden_id: str
    ) -> dict:
        """CU73 — Aplicar_promocion_orden()."""
        db   = await database.get_db()
        promo = await db.fetchrow("""
            SELECT * FROM promotions
            WHERE codigo_qr = $1
              AND activa = TRUE
              AND fecha_inicio <= NOW()
              AND fecha_fin    >= NOW()
        """, codigo_qr)

        if not promo:
            return {"aplicada": False, "motivo": "Promoción no válida o expirada."}

        orden = await db.fetchrow(
            "SELECT subtotal FROM orders WHERE id = $1::uuid", orden_id
        )
        if not orden:
            raise KeyError("Orden no encontrada.")

        descuento = round(
            float(orden["subtotal"]) * float(promo["descuento"]) / 100, 2
        )
        await db.execute("""
            UPDATE orders
            SET descuento = $2, total = subtotal - $2,
                fecha_actualizacion = NOW()
            WHERE id = $1::uuid
        """, orden_id, descuento)

        return {"aplicada": True, "titulo": promo["titulo"],
                "descuento_aplicado": descuento}