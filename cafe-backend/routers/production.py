"""
routers/production.py
Módulo 02 — Producción y Operaciones (POM)

Router FastAPI que delega en ProductionController.
Cubre: CU36, CU37, CU38, CU39, CU40, CU41, CU42, CU43, CU44, CU45, CU46, CU47
"""

from fastapi import APIRouter, Query
from typing import Optional
from pydantic import BaseModel, Field

from controllers.production_controller import ProductionController

router = APIRouter()
ctrl   = ProductionController()


# ── Schemas inline ────────────────────────────────────────────────────────────

class EstadoUpdateSchema(BaseModel):
    empleado_id: Optional[int] = None

class ProblemaSchema(BaseModel):
    descripcion: str = Field(..., min_length=5, max_length=500)


# ══════════════════════════════════════════════════════════
# CU36 — Recibir orden de producción
# ══════════════════════════════════════════════════════════

@router.get("/orders")
async def list_production_orders(
    estado:      Optional[str] = Query(None, description="pendiente|en_preparacion|lista|entregada|con_problema"),
    empleado_id: Optional[int] = Query(None),
):
    """
    CU36 — Lista todas las órdenes activas en producción.
    Corresponde a Enviar_orden_produccion() del diagrama.
    """
    return await ctrl.listar_ordenes(estado, empleado_id)


@router.get("/orders/{orden_id}/receive")
async def receive_order(orden_id: str):
    """
    CU36 — Confirma la recepción de una orden específica en producción.
    Corresponde a Confirmar_recepcion_informacion() del diagrama.
    """
    return await ctrl.recibir_orden(orden_id)


# ══════════════════════════════════════════════════════════
# CU37 — Ver detalles completos de la orden
# ══════════════════════════════════════════════════════════

@router.get("/orders/{orden_id}")
async def get_order_detail(orden_id: str):
    """CU37 — Detalles completos de la orden: ítems, personalización, notas."""
    return await ctrl.obtener_detalle(orden_id)


# ══════════════════════════════════════════════════════════
# CU38 — Marcar orden como 'en preparación'
# ══════════════════════════════════════════════════════════

@router.patch("/orders/{orden_id}/start")
async def start_preparation(orden_id: str, data: EstadoUpdateSchema):
    """
    CU38 — El barista inicia la preparación de la orden.
    Corresponde a actualizarEstado('EnPreparacion').
    """
    return await ctrl.marcar_en_preparacion(orden_id, data.empleado_id)


# ══════════════════════════════════════════════════════════
# CU39 — Consultar receta detallada
# ══════════════════════════════════════════════════════════

@router.get("/recipes/{bebida_id}")
async def get_recipe(bebida_id: int):
    """CU39 — Receta completa de una bebida con proporciones e ingredientes."""
    return await ctrl.obtener_receta(bebida_id)


@router.get("/orders/{orden_id}/recipes")
async def get_order_recipes(orden_id: str):
    """CU39 — Todas las recetas necesarias para preparar una orden."""
    return await ctrl.obtener_recetas_orden(orden_id)


# ══════════════════════════════════════════════════════════
# CU40 — Ver notas especiales del cliente
# ══════════════════════════════════════════════════════════

@router.get("/orders/{orden_id}/notes")
async def get_order_notes(orden_id: str):
    """
    CU40 — Notas especiales del cliente.
    Corresponde a resaltarIconoNota() → mostrarTextoNota().
    """
    return await ctrl.obtener_notas(orden_id)


# ══════════════════════════════════════════════════════════
# CU41 — Consultar ficha técnica de ingrediente
# ══════════════════════════════════════════════════════════

@router.get("/ingredients/{ingrediente_id}/tech-sheet")
async def get_ingredient_tech_sheet(ingrediente_id: int):
    """
    CU41 — Ficha técnica del ingrediente: proporciones, método, advertencias.
    Corresponde a mostrarFichaTecnica(proporciones, metodo, advertencias).
    """
    return await ctrl.obtener_ficha_tecnica_ingrediente(ingrediente_id)


# ══════════════════════════════════════════════════════════
# CU42 — Marcar orden como 'lista para recoger'
# ══════════════════════════════════════════════════════════

@router.patch("/orders/{orden_id}/ready")
async def mark_order_ready(orden_id: str):
    """
    CU42 — Marca la orden como lista y dispara notificación al cliente (CU43).
    Corresponde a presionarMarcarComoLista() → actualizarEstado('ListaParaRecoger')
    + dispararEventoNotificacion().
    """
    return await ctrl.marcar_lista(orden_id)


@router.patch("/orders/{orden_id}/undo-ready")
async def undo_ready(orden_id: str):
    """
    CU42 — Deshace el marcado como lista (ventana de 5 seg).
    Corresponde a revertirEstado('EnPreparacion').
    """
    return await ctrl.revertir_lista(orden_id)


# ══════════════════════════════════════════════════════════
# CU43 — Notificar orden lista al cliente
# ══════════════════════════════════════════════════════════

@router.post("/orders/{orden_id}/notify")
async def notify_order_ready(orden_id: str):
    """
    CU43 — Envía notificación push al cliente y actualiza pantalla pública.
    Corresponde a detectarCambioEstado() → enviarNotificacionPush()
    → actualizarPantallaPublica().
    """
    return await ctrl.notificar_orden_lista(orden_id)


@router.get("/public-screen")
async def get_public_screen():
    """
    CU43 — Retorna las órdenes listas para mostrar en la pantalla pública del local.
    Corresponde a actualizarPantallaPublica() — vista PublicScreen.
    """
    return await ctrl.obtener_pantalla_publica()


# ══════════════════════════════════════════════════════════
# CU44 — Marcar orden como 'entregada'
# ══════════════════════════════════════════════════════════

@router.patch("/orders/{orden_id}/deliver")
async def deliver_order(orden_id: str):
    """
    CU44 — El barista entrega la orden al cliente.
    Corresponde a cambiarEstado('Entregada').
    """
    return await ctrl.marcar_entregada(orden_id)


# ══════════════════════════════════════════════════════════
# CU45 — Reportar problema con la orden
# ══════════════════════════════════════════════════════════

@router.post("/orders/{orden_id}/problem")
async def report_problem(orden_id: str, data: ProblemaSchema):
    """CU45 — El barista reporta un problema con la preparación."""
    return await ctrl.reportar_problema(orden_id, data.descripcion)


# ══════════════════════════════════════════════════════════
# CU46 — Reimprimir ticket de orden
# ══════════════════════════════════════════════════════════

@router.get("/orders/{orden_id}/ticket")
async def reprint_ticket(orden_id: str):
    """
    CU46 — Datos del ticket para reimprimir.
    Corresponde a Proporcionar_numero_orden() → Enviar_a_impresora()
    → Confirmar_impresion_exitosa().
    """
    return await ctrl.reimprimir_ticket(orden_id)


# ══════════════════════════════════════════════════════════
# CU47 — Registrar tiempo de preparación
# ══════════════════════════════════════════════════════════

@router.post("/orders/{orden_id}/prep-time")
async def register_prep_time(orden_id: str):
    """
    CU47 — Calcula y persiste el tiempo de preparación.
    Alimenta las métricas de eficiencia del M03 (CU62).
    """
    return await ctrl.registrar_tiempo_preparacion(orden_id)