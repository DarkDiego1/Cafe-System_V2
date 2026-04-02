"""
services/notification_service.py
Módulo 02 — Producción y Operaciones (POM)
Compartido con M01 — Experiencia del Cliente

Servicio: NotificationService
Casos de uso: CU43 — Notificar orden lista al cliente
              CU27 — Recibir notificaciones push (M01)

Columnas reales de la tabla notifications:
  - usuario_id (uuid, FK a users) — columna original
  - orden_id   (uuid, FK a orders) — añadida por migration_m02_fix
  - tipo        VARCHAR(30) con CHECK
  - titulo, mensaje, leida, fecha_creacion, payload
  - fecha_envio, enviada — añadidas por migration_m02_fix
"""

from datetime import datetime
from typing import Optional
import database


class NotificationService:
    """
    Servicio de notificaciones del sistema.

    Atributos del diagrama:
        datosOrden: Object — recibido en detectarCambioEstado()
    """

    # ══════════════════════════════════════════════════════
    # CU43 — Notificar orden lista al cliente
    # ══════════════════════════════════════════════════════

    async def detectar_cambio_estado(
        self, orden_id: str, estado_esperado: str = "lista"
    ) -> bool:
        """
        Verifica si la orden alcanzó el estado indicado.
        Corresponde a detectarCambioEstado('Lista') — CU43.

        Returns:
            True si el estado coincide con el esperado.
        """
        db = await database.get_db()
        estado = await db.fetchval(
            "SELECT estado FROM orders WHERE id = $1::uuid", orden_id
        )
        # La BD guarda 'lista' o 'Lista' dependiendo del CHECK — comparar sin case
        return (estado or "").lower() == estado_esperado.lower()

    async def enviar_notificacion_push(self, datos_orden: dict) -> dict:
        """
        Envía notificación push al cliente.
        Corresponde a enviarNotificacionPush(datosOrden) — CU43.

        Usa las columnas reales de la tabla notifications:
          usuario_id (obtenido via JOIN con orders.cliente_id)
          orden_id, tipo 'OrdenLista', titulo, mensaje
        """
        db = await database.get_db()

        mensaje = (
            f"Hola {datos_orden.get('nombre_cliente', '')}! "
            f"Tu orden {datos_orden.get('codigo_orden', '')} está lista para recoger."
        )

        # Insertar usando usuario_id = cliente_id de la orden
        await db.execute("""
            INSERT INTO notifications
                (usuario_id, orden_id, tipo, titulo, mensaje,
                 leida, fecha_creacion, fecha_envio, enviada)
            SELECT
                o.cliente_id,
                o.id,
                'OrdenLista',
                '¡Tu pedido está listo! ☕',
                $2,
                FALSE,
                NOW(),
                NOW(),
                TRUE
            FROM orders o
            WHERE o.id = $1::uuid
              AND o.cliente_id IS NOT NULL
        """,
            datos_orden.get("orden_id"),
            mensaje,
        )

        return {
            "enviada": True,
            "tipo": "OrdenLista",
            "destinatario": datos_orden.get("nombre_cliente"),
            "orden": datos_orden.get("codigo_orden"),
            "timestamp": datetime.now().isoformat(),
        }

    async def actualizar_pantalla_publica(
        self, nombre_cliente: str, codigo_orden: str
    ) -> dict:
        """
        Actualiza la pantalla pública del local con el nombre del cliente.
        Corresponde a actualizarPantallaPublica(nombreCliente) — CU43.

        En producción enviaría un evento WebSocket a PublicScreen.
        Aquí persiste el estado de pantalla en la BD.
        """
        db = await database.get_db()

        await db.execute("""
            INSERT INTO public_screen_queue
                (codigo_orden, nombre_cliente, estado, fecha_agregado)
            VALUES ($1, $2, 'lista', NOW())
            ON CONFLICT (codigo_orden)
            DO UPDATE SET estado = 'lista', fecha_agregado = NOW()
        """, codigo_orden, nombre_cliente)

        return {
            "pantalla_actualizada": True,
            "nombre_cliente": nombre_cliente,
            "codigo_orden": codigo_orden,
            "timestamp": datetime.now().isoformat(),
        }

    async def notificar_orden_lista(self, orden_id: str) -> dict:
        """
        Orquesta el flujo completo de notificación CU43:
          detectarCambioEstado('Lista')
          → enviarNotificacionPush(datosOrden)
          → actualizarPantallaPublica(nombreCliente)
        """
        db = await database.get_db()

        row = await db.fetchrow("""
            SELECT
                o.id, o.codigo_orden, o.estado,
                u.nombre_completo AS nombre_cliente
            FROM orders o
            LEFT JOIN users u ON u.id = o.cliente_id
            WHERE o.id = $1::uuid
        """, orden_id)

        if not row:
            raise KeyError(f"Orden '{orden_id}' no encontrada.")

        datos_orden = {
            "orden_id": str(row["id"]),
            "codigo_orden": row["codigo_orden"],
            "nombre_cliente": row["nombre_cliente"] or "Cliente",
            "estado": row["estado"],
        }

        # Verificar que efectivamente está lista
        lista = await self.detectar_cambio_estado(orden_id, "lista")
        if not lista:
            return {
                "enviada": False,
                "razon": (
                    f"La orden está en estado '{row['estado']}', no 'lista'."
                ),
            }

        push_result = await self.enviar_notificacion_push(datos_orden)
        pantalla_result = await self.actualizar_pantalla_publica(
            datos_orden["nombre_cliente"], datos_orden["codigo_orden"]
        )

        return {
            "notificacion_push": push_result,
            "pantalla_publica": pantalla_result,
        }

    # ══════════════════════════════════════════════════════
    # CU27 — Notificaciones generales (M01)
    # ══════════════════════════════════════════════════════

    async def enviar_notificacion_generica(
        self,
        user_id: str,
        titulo: str,
        mensaje: str,
        tipo: str = "Sistema",
    ) -> dict:
        """
        Envía una notificación genérica a un usuario.
        Usado por M01 para CU27 — Recibir notificaciones push.

        Usa usuario_id (columna original de la tabla).
        El tipo debe ser uno de los valores del CHECK:
          push, email, sms, in_app, OrdenLista, StockBajo,
          Cumpleaños, Promocion, Recordatorio, Sistema
        """
        db = await database.get_db()

        await db.execute("""
            INSERT INTO notifications
                (usuario_id, tipo, titulo, mensaje,
                 leida, fecha_creacion, fecha_envio, enviada)
            VALUES ($1::uuid, $2, $3, $4, FALSE, NOW(), NOW(), TRUE)
        """, user_id, tipo, titulo, mensaje)

        return {
            "enviada": True,
            "tipo": tipo,
            "titulo": titulo,
            "timestamp": datetime.now().isoformat(),
        }

    async def obtener_notificaciones_usuario(self, user_id: str) -> list[dict]:
        """
        Retorna las notificaciones de un usuario ordenadas por fecha.
        Usado por M01 CU27.
        """
        db = await database.get_db()
        rows = await db.fetch("""
            SELECT
                id, tipo, titulo, mensaje, leida,
                orden_id, fecha_creacion
            FROM notifications
            WHERE usuario_id = $1::uuid
            ORDER BY fecha_creacion DESC
            LIMIT 50
        """, user_id)
        return [dict(r) for r in rows]

    async def marcar_leida(self, notificacion_id: int) -> bool:
        """Marca una notificación como leída. Usado por M01."""
        db = await database.get_db()
        result = await db.execute(
            "UPDATE notifications SET leida = TRUE WHERE id = $1",
            notificacion_id,
        )
        return result == "UPDATE 1"

    # ══════════════════════════════════════════════════════
    # Pantalla pública (CU43 — PublicScreen)
    # ══════════════════════════════════════════════════════

    async def obtener_notificaciones_pantalla_publica(self) -> list[dict]:
        """
        Retorna las órdenes listas para mostrar en la pantalla pública.
        Corresponde a PublicScreen.actualizarPantallaPublica() — CU43.
        """
        db = await database.get_db()
        rows = await db.fetch("""
            SELECT codigo_orden, nombre_cliente, estado, fecha_agregado
            FROM public_screen_queue
            WHERE estado = 'lista'
              AND fecha_agregado > NOW() - INTERVAL '30 minutes'
            ORDER BY fecha_agregado DESC
        """)
        return [dict(r) for r in rows]