"""
views/employee/screens_m02.py
Módulo 02 — Producción y Operaciones (POM)

Clases Vista del Employee que corresponden a los archivos HTML:
  e1-login.html   → LoginScreen (ya en kiosk, reutilizada)
  e2-cola.html    → ProductionScreen (vista de cola de órdenes)
  e3-detalle.html → ProductionScreen (vista de detalle de orden)
  e4-control.html → ProductionScreen (control de estado)
  e5-reporte.html → PublicScreen (pantalla pública del local)
"""

import httpx
from typing import Optional

BASE_URL = "http://localhost:8000/api"


# ══════════════════════════════════════════════════════════
# ProductionScreen — e2-cola.html, e3-detalle.html, e4-control.html
# CU36, CU37, CU38, CU39, CU40, CU41, CU42, CU44, CU45, CU46, CU47
# ══════════════════════════════════════════════════════════

class ProductionScreen:
    """
    Pantalla principal del barista para gestionar órdenes de producción.
    Corresponde a e2-cola.html, e3-detalle.html y e4-control.html del Employee.

    Atributos del diagrama:
        nota: String          (CU40)
        idOrden: String       (CU42)
        idIngrediente: String (CU41)
    """

    def __init__(self, empleado_id: Optional[int] = None):
        self.empleado_id = empleado_id
        self.nota: str = ""
        self.id_orden: str = ""
        self.id_ingrediente: Optional[int] = None
        self._ordenes_activas: list = []

    # ── CU36: recibir orden ───────────────────────────────

    async def cargar_cola_produccion(
        self, estado: Optional[str] = None
    ) -> list:
        """
        Carga la cola de órdenes activas en e2-cola.html.
        Corresponde a CU36 — Recibir orden de producción.
        """
        params = {}
        if estado:
            params["estado"] = estado
        if self.empleado_id:
            params["empleado_id"] = self.empleado_id
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/production/orders", params=params
            )
        self._ordenes_activas = r.json() if r.status_code == 200 else []
        return self._ordenes_activas

    # ── CU37: ver detalle ─────────────────────────────────

    async def ver_detalle_orden(self, orden_id: str) -> dict:
        """
        Muestra el detalle completo de una orden en e3-detalle.html.
        Corresponde a CU37 — Ver detalles completos de la orden.
        """
        self.id_orden = orden_id
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/production/orders/{orden_id}")
        return r.json() if r.status_code == 200 else {}

    # ── CU38: marcar en preparación ──────────────────────

    async def iniciar_preparacion(self, orden_id: str) -> dict:
        """
        El barista toca 'Iniciar preparación' en e4-control.html.
        Corresponde a CU38 — Marcar orden como 'en preparación'.
        """
        self.id_orden = orden_id
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{BASE_URL}/production/orders/{orden_id}/start",
                json={"empleado_id": self.empleado_id},
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU39: consultar receta ────────────────────────────

    async def consultar_receta(self, bebida_id: int) -> dict:
        """
        El barista consulta la receta desde e3-detalle.html.
        Corresponde a CU39 — Consultar receta detallada.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/production/recipes/{bebida_id}")
        return r.json() if r.status_code == 200 else {}

    async def consultar_recetas_orden(self, orden_id: str) -> list:
        """Retorna todas las recetas de una orden. CU39."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/production/orders/{orden_id}/recipes"
            )
        return r.json() if r.status_code == 200 else []

    # ── CU40: notas especiales ────────────────────────────

    async def recibir_orden_con_nota(self, orden_id: str) -> dict:
        """
        Recibe una orden y verifica si tiene notas especiales.
        Corresponde a recibirOrdenConNota() — CU40.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/production/orders/{orden_id}/notes"
            )
        data = r.json() if r.status_code == 200 else {}
        if data.get("tiene_notas"):
            await self.resaltar_icono_nota()
        return data

    async def resaltar_icono_nota(self) -> dict:
        """
        Resalta visualmente el ícono de nota en e3-detalle.html.
        Corresponde a resaltarIconoNota() — CU40.
        """
        return {"icono_nota": True, "destacado": True}

    async def mostrar_texto_nota(self, orden_id: str) -> dict:
        """
        Muestra el texto de la nota especial del cliente.
        Corresponde a mostrarTextoNota() — CU40.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/production/orders/{orden_id}/notes"
            )
        return r.json() if r.status_code == 200 else {}

    async def confirmar_lectura_nota(self) -> dict:
        """El barista confirma que leyó la nota. CU40."""
        return {"nota_leida": True}

    # ── CU41: ficha técnica de ingrediente ───────────────

    async def seleccionar_ingrediente(self, ingrediente_id: int) -> dict:
        """
        El barista selecciona un ingrediente para ver su ficha.
        Corresponde a seleccionarIngrediente(idIngrediente) — CU41.
        """
        self.id_ingrediente = ingrediente_id
        return await self.mostrar_ficha_tecnica(ingrediente_id)

    async def presionar_boton_ayuda(self) -> dict:
        """
        El barista presiona el botón de ayuda del ingrediente.
        Corresponde a presionarBotonAyuda() — CU41.
        """
        if not self.id_ingrediente:
            return {"error": "No hay ingrediente seleccionado."}
        return await self.mostrar_ficha_tecnica(self.id_ingrediente)

    async def mostrar_ficha_tecnica(
        self,
        ingrediente_id: int,
    ) -> dict:
        """
        Muestra la ficha técnica del ingrediente.
        Corresponde a mostrarFichaTecnica(proporciones, metodo, advertencias) — CU41.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/production/ingredients/{ingrediente_id}/tech-sheet"
            )
        data = r.json() if r.status_code == 200 else {}
        if data.get("falta_imagen"):
            await self.mostrar_texto_tecnico_detallado(data)
        return data

    async def mostrar_texto_tecnico_detallado(self, ficha: dict) -> dict:
        """
        Muestra texto técnico cuando no hay imagen disponible.
        Corresponde a mostrarTextoTecnicoDetallado() — CU41.
        """
        return {
            "modo": "texto",
            "descripcion": ficha.get("descripcion", "Sin descripción."),
            "ficha_tecnica": ficha.get("ficha_tecnica", ""),
        }

    async def ofrecer_contacto_soporte_interno(self) -> dict:
        """
        Ofrece contactar al soporte interno cuando faltan imágenes.
        Corresponde a ofrecerContactoSoporteInterno() — CU41.
        """
        return {
            "soporte": True,
            "mensaje": "Contacta al administrador para actualizar la ficha técnica.",
        }

    # ── CU42: marcar lista ────────────────────────────────

    async def presionar_marcar_como_lista(self, orden_id: str) -> dict:
        """
        El barista marca la orden como lista en e4-control.html.
        Corresponde a presionarMarcarComoLista(idOrden) — CU42.
        """
        self.id_orden = orden_id
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{BASE_URL}/production/orders/{orden_id}/ready"
            )
        resultado = r.json() if r.status_code == 200 else {}
        await self.mover_a_columna_listas(orden_id)
        await self.habilitar_boton_deshacer(orden_id)
        return resultado

    async def mover_a_columna_listas(self, orden_id: str) -> dict:
        """
        Mueve la orden a la columna de 'Listas' en e2-cola.html.
        Corresponde a moverAColumnaListas() — CU42.
        """
        return {"orden_id": orden_id, "columna": "listas"}

    async def habilitar_boton_deshacer(
        self, orden_id: str, segundos: int = 5
    ) -> dict:
        """
        Habilita el botón de deshacer por 5 segundos.
        Corresponde a habilitarBotonDeshacer(5seg) — CU42.
        """
        return {
            "deshacer_disponible": True,
            "segundos": segundos,
            "orden_id": orden_id,
        }

    async def deshacer_marcar_lista(self, orden_id: str) -> dict:
        """Deshace el marcado como lista. CU42."""
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{BASE_URL}/production/orders/{orden_id}/undo-ready"
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU44: marcar entregada ────────────────────────────

    async def marcar_entregada(self, orden_id: str) -> dict:
        """
        El barista entrega la orden al cliente.
        Corresponde a CU44 — Marcar orden como 'entregada'.
        """
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{BASE_URL}/production/orders/{orden_id}/deliver"
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU45: reportar problema ───────────────────────────

    async def reportar_problema(self, orden_id: str, descripcion: str) -> dict:
        """
        El barista reporta un problema con la orden.
        Corresponde a CU45 — Reportar problema con orden.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/production/orders/{orden_id}/problem",
                json={"descripcion": descripcion},
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU46: reimprimir ticket ───────────────────────────

    async def reimprimir_ticket(self, orden_id: str) -> dict:
        """
        Solicita la reimpresión del ticket de la orden.
        Corresponde a CU46 — Reimprimir ticket de orden.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/production/orders/{orden_id}/ticket"
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU47: registrar tiempo ────────────────────────────

    async def registrar_tiempo_preparacion(self, orden_id: str) -> dict:
        """
        Registra el tiempo de preparación de la orden.
        Corresponde a CU47 — Registrar tiempo de preparación.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/production/orders/{orden_id}/prep-time"
            )
        return r.json() if r.status_code == 200 else {}


# ══════════════════════════════════════════════════════════
# PublicScreen — e5-reporte.html (pantalla pública del local)
# CU43
# ══════════════════════════════════════════════════════════

class PublicScreen:
    """
    Pantalla pública del local que muestra las órdenes listas.
    Corresponde a e5-reporte.html del Employee.

    Atributos del diagrama:
        nombreCliente: String
    """

    def __init__(self):
        self.nombre_cliente: str = ""
        self._ordenes_listas: list = []

    async def actualizar_pantalla_publica(self) -> list:
        """
        Actualiza la pantalla con las órdenes listas para recoger.
        Corresponde a actualizarPantallaPublica() — CU43.
        Alimenta e5-reporte.html con datos del backend.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/production/public-screen")
        self._ordenes_listas = r.json() if r.status_code == 200 else []
        if self._ordenes_listas:
            self.nombre_cliente = self._ordenes_listas[0].get(
                "nombre_cliente", ""
            )
        return self._ordenes_listas

    async def notificar_orden_lista(self, orden_id: str) -> dict:
        """
        Dispara la notificación push al cliente cuando su orden está lista.
        Corresponde al flujo CU43 completo.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/production/orders/{orden_id}/notify"
            )
        return r.json() if r.status_code == 200 else {}