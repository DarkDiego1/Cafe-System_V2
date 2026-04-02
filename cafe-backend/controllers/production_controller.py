"""
controllers/production_controller.py
Módulo 02 — Producción y Operaciones (POM)

Controlador: ProductionController
Casos de uso: CU36–CU47

Orquesta ProductionService, KnowledgeBase y NotificationService.
Traduce excepciones de dominio a HTTPException.
"""

from typing import Optional
from fastapi import HTTPException

from services.production_service import ProductionService
from services.knowledge_base import KnowledgeBase
from services.notification_service import NotificationService
from entities.order import Order


class ProductionController:
    """
    Intermediario entre los routers del Módulo 02 y los servicios.
    """

    def __init__(self) -> None:
        self._prod    = ProductionService()
        self._kb      = KnowledgeBase()
        self._notif   = NotificationService()

    # ── CU36: recibir y listar órdenes ───────────────────────────────

    async def listar_ordenes(
        self,
        estado: Optional[str] = None,
        empleado_id: Optional[int] = None,
    ) -> list[dict]:
        """Lista las órdenes activas en producción. CU36."""
        return await self._prod.listar_ordenes_produccion(estado, empleado_id)

    async def recibir_orden(self, orden_id: str) -> dict:
        """
        Recibe una orden en producción.
        Corresponde a Enviar_orden_produccion() → Enviar_fecha_estimada() — CU36.
        """
        try:
            orden = await self._prod.recibir_orden_produccion(orden_id)
            return orden.to_dict()
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU37: ver detalles completos ──────────────────────────────────

    async def obtener_detalle(self, orden_id: str) -> dict:
        """Retorna todos los datos de la orden. CU37."""
        try:
            orden = await self._prod.obtener_detalle_orden(orden_id)
            return orden.to_dict()
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU38: marcar en preparación ───────────────────────────────────

    async def marcar_en_preparacion(
        self, orden_id: str, empleado_id: Optional[int] = None
    ) -> dict:
        """
        Cambia estado a 'en_preparacion'.
        Corresponde a actualizarEstado('EnPreparacion') — CU38.
        """
        try:
            orden = await self._prod.marcar_en_preparacion(orden_id, empleado_id)
            return {
                "mensaje": "Orden marcada como en preparación.",
                **orden.confirmacion_actualizacion_estado(),
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # ── CU39: consultar receta ────────────────────────────────────────

    async def obtener_receta(self, bebida_id: int) -> dict:
        """Retorna la receta detallada de una bebida. CU39."""
        try:
            return await self._kb.consultar_receta(bebida_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def obtener_recetas_orden(self, orden_id: str) -> list[dict]:
        """Retorna todas las recetas de una orden. CU39."""
        return await self._kb.obtener_recetas_orden(orden_id)

    # ── CU40: notas especiales ────────────────────────────────────────

    async def obtener_notas(self, orden_id: str) -> dict:
        """
        Retorna las notas especiales de la orden.
        Corresponde a mostrarTextoNota() — CU40.
        """
        try:
            orden = await self._prod.obtener_detalle_orden(orden_id)
            return {
                "orden_id": orden_id,
                "codigo_orden": orden.codigo_orden,
                "tiene_notas": orden.tiene_notas_especiales(),
                "notas_generales": orden.notas_generales,
                "notas_por_item": [
                    {
                        "bebida": item.nombre_bebida,
                        "tamano": item.tamano,
                        "nota": item.notas_item,
                    }
                    for item in orden.items
                    if item.notas_item
                ],
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU41: ficha técnica de ingrediente ───────────────────────────

    async def obtener_ficha_tecnica_ingrediente(self, ingrediente_id: int) -> dict:
        """
        Retorna ficha técnica con advertencias.
        Corresponde a obtenerFichaTecnicaIngrediente() — CU41.
        """
        try:
            ficha = await self._kb.consultar_ficha_tecnica(ingrediente_id)
            ficha["falta_imagen"] = self._kb.detectar_falta_imagenes(ficha)
            return ficha
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU42: marcar lista / deshacer ────────────────────────────────

    async def marcar_lista(self, orden_id: str) -> dict:
        """
        Marca la orden como lista y dispara notificación.
        Corresponde a actualizarEstado('ListaParaRecoger')
        + dispararEventoNotificacion() — CU42.
        """
        try:
            orden = await self._prod.marcar_lista(orden_id)

            # Disparar notificación automáticamente — CU43
            try:
                await self._notif.notificar_orden_lista(orden_id)
            except Exception:
                pass  # La notificación no debe bloquear el marcado

            return {
                "mensaje": "Orden lista para recoger. Notificación enviada al cliente.",
                **orden.confirmacion_actualizacion_estado(),
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    async def revertir_lista(self, orden_id: str) -> dict:
        """
        Deshace el marcado como lista.
        Corresponde a revertirEstado('EnPreparacion') — CU42.
        """
        try:
            orden = await self._prod.revertir_a_en_preparacion(orden_id)
            return {
                "mensaje": "Estado revertido a 'en preparación'.",
                **orden.confirmacion_actualizacion_estado(),
            }
        except (KeyError, ValueError) as e:
            code = 404 if isinstance(e, KeyError) else 422
            raise HTTPException(status_code=code, detail=str(e))

    # ── CU43: notificar ───────────────────────────────────────────────

    async def notificar_orden_lista(self, orden_id: str) -> dict:
        """
        Dispara la notificación push y actualiza pantalla pública.
        Corresponde al flujo CU43.
        """
        try:
            return await self._notif.notificar_orden_lista(orden_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def obtener_pantalla_publica(self) -> list[dict]:
        """Retorna las órdenes para mostrar en pantalla pública. CU43."""
        return await self._notif.obtener_notificaciones_pantalla_publica()

    # ── CU44: marcar entregada ────────────────────────────────────────

    async def marcar_entregada(self, orden_id: str) -> dict:
        """
        Cierra el ciclo de producción.
        Corresponde a cambiarEstado('Entregada') — CU44.
        """
        try:
            orden = await self._prod.marcar_entregada(orden_id)
            return {
                "mensaje": "Orden marcada como entregada.",
                **orden.confirmacion_actualizacion_estado(),
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # ── CU45: reportar problema ───────────────────────────────────────

    async def reportar_problema(self, orden_id: str, descripcion: str) -> dict:
        """Registra un problema con la orden. CU45."""
        try:
            orden = await self._prod.reportar_problema(orden_id, descripcion)
            return {
                "mensaje": "Problema reportado correctamente.",
                "orden_id": orden_id,
                "estado": orden.estado,
                "reporte": descripcion,
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # ── CU46: reimprimir ticket ───────────────────────────────────────

    async def reimprimir_ticket(self, orden_id: str) -> dict:
        """
        Obtiene datos del ticket para reimpresión.
        Corresponde a Proporcionar_numero_orden() → Enviar_a_impresora() — CU46.
        """
        try:
            return await self._prod.obtener_ticket(orden_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU47: registrar tiempo ────────────────────────────────────────

    async def registrar_tiempo_preparacion(self, orden_id: str) -> dict:
        """Calcula y persiste el tiempo de preparación. CU47."""
        try:
            return await self._prod.registrar_tiempo_preparacion(orden_id)
        except (KeyError, ValueError) as e:
            code = 404 if isinstance(e, KeyError) else 422
            raise HTTPException(status_code=code, detail=str(e))