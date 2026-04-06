"""
views/management/screens_m03.py
Módulo 03 — Gestión y Administración (MAM)

Clases Vista del Management que corresponden a los archivos HTML:
  g1-dashboard.html    → ReportsScreen (dashboard general)
  g2-auditoria.html    → ReportsScreen (auditoría)
  g3-inventario.html   → InventoryScreen
  g4-menu.html         → InventoryScreen (gestión menú)
  g5-empleados.html    → AdminScreen (empleados)
  g6-reportes.html     → ReportsScreen (reportes)
  g7-configuracion.html→ ReportsScreen (umbrales)
"""

import httpx
from typing import Optional
from datetime import datetime

BASE_URL = "http://localhost:8000/api"


# ══════════════════════════════════════════════════════════
# InventoryScreen — g3-inventario.html, g4-menu.html
# CU48, CU49, CU50, CU51, CU52, CU53, CU55, CU56, CU57, CU63
# ══════════════════════════════════════════════════════════

class InventoryScreen:
    """
    Pantalla de gestión de inventario del gerente.
    Corresponde a g3-inventario.html y g4-menu.html del Management.

    Atributos del diagrama:
        ingrediente: String
        cantidad: Double
        nombre: String
        unidad: String
        stockMinimo: Double
    """

    def __init__(self, gerente_id: Optional[int] = None):
        self.gerente_id = gerente_id
        self.ingrediente: str = ""
        self.cantidad: float = 0.0
        self.nombre: str = ""
        self.unidad: str = ""
        self.stock_minimo: float = 0.0

    # ── CU50/CU51: consultar niveles ─────────────────────

    async def mostrar_niveles_inventario(
        self, solo_alertas: bool = False
    ) -> list:
        """
        Carga los niveles de inventario en g3-inventario.html.
        Corresponde a CU50 — Consultar niveles de inventario.
        CU51 — solo_alertas=True muestra solo los que están bajo mínimo.
        """
        params = {}
        if solo_alertas:
            params["alerta"] = "true"
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/inventory/ingredients", params=params
            )
        return r.json() if r.status_code == 200 else []

    async def mostrar_alertas_stock(self) -> dict:
        """
        Muestra solo los ingredientes bajo umbral mínimo.
        Corresponde a CU51 — Recibir alerta de stock bajo.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/inventory/ingredients/alerts")
        return r.json() if r.status_code == 200 else {}

    # ── CU56: registrar merma ─────────────────────────────

    async def seleccionar_registrar_merma(self) -> dict:
        """
        El gerente/empleado selecciona registrar merma en g3-inventario.html.
        Corresponde a seleccionarRegistrarMerma() — CU56.
        """
        return {"formulario": "merma", "activo": True}

    async def ingresar_ingrediente_y_cantidad(
        self, ingrediente: str, cantidad: float
    ) -> None:
        """
        Captura el ingrediente y cantidad de merma.
        Corresponde a ingresarIngredienteYCantidad() — CU56.
        """
        self.ingrediente = ingrediente
        self.cantidad = cantidad

    async def confirmar_registro_merma(
        self,
        ingrediente_id: int,
        cantidad: float,
        motivo: str,
    ) -> dict:
        """
        Envía la merma al backend.
        Corresponde a confirmarRegistro() — CU56.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/inventory/ingredients/waste",
                json={
                    "ingrediente_id": ingrediente_id,
                    "cantidad": cantidad,
                    "motivo": motivo,
                    "registrado_por": self.gerente_id,
                },
            )
        if r.status_code == 201:
            return await self.mostrar_confirmacion()
        return await self.error_cantidad_mayor_stock()

    async def error_cantidad_mayor_stock(self) -> dict:
        """
        Muestra error si la cantidad de merma supera el stock.
        Corresponde a errorCantidadMayorStock() — CU56.
        """
        return {
            "error": True,
            "mensaje": "La cantidad ingresada supera el stock disponible.",
        }

    # ── CU57/CU48: gestionar catálogo ────────────────────

    async def agregar_ingrediente(
        self,
        nombre: str,
        unidad: str,
        stock_minimo: float,
        categoria: str = "general",
        stock_optimo: float = 0.0,
    ) -> dict:
        """
        El gerente agrega un nuevo ingrediente desde g3-inventario.html.
        Corresponde a agregarIngrediente(nombre, unidad, stockMinimo) — CU57/CU48.
        """
        self.nombre = nombre
        self.unidad = unidad
        self.stock_minimo = stock_minimo
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/inventory/ingredients",
                json={
                    "nombre": nombre,
                    "categoria": categoria,
                    "unidad_medida": unidad,
                    "stock_minimo": stock_minimo,
                    "stock_optimo": stock_optimo or stock_minimo * 2,
                },
            )
        if r.status_code == 201:
            return await self.mostrar_confirmacion()
        return await self.mostrar_error()

    async def modificar_ingrediente(
        self, ingrediente_id: int, campos: dict
    ) -> dict:
        """
        Modifica un ingrediente existente.
        Corresponde a CU49 — Modificar información de ingrediente.
        """
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{BASE_URL}/inventory/ingredients/{ingrediente_id}",
                json=campos,
            )
        if r.status_code == 200:
            return await self.mostrar_confirmacion()
        return await self.mostrar_error()

    # ── CU52: actualizar manualmente ─────────────────────

    async def actualizar_stock_manual(
        self, ingrediente_id: int, nuevo_stock: float, motivo: str
    ) -> dict:
        """
        Actualiza el stock de un ingrediente manualmente.
        Corresponde a CU52 — Actualizar inventario manualmente.
        """
        async with httpx.AsyncClient() as client:
            r = await client.put(
                f"{BASE_URL}/inventory/ingredients/{ingrediente_id}/stock",
                json={"nuevo_stock": nuevo_stock, "motivo": motivo},
            )
        if r.status_code == 200:
            return await self.mostrar_confirmacion()
        return await self.mostrar_error()

    # ── CU53: entrada de mercancía ────────────────────────

    async def registrar_entrada_mercancia(
        self, ingrediente_id: int, cantidad: float,
        orden_compra_id: Optional[int] = None,
    ) -> dict:
        """
        Registra la entrada de mercancía del proveedor.
        Corresponde a CU53 — Registrar entrada de mercancía.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/inventory/ingredients/{ingrediente_id}/entry",
                json={"cantidad": cantidad, "orden_compra_id": orden_compra_id},
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU55: lista de compras ────────────────────────────

    async def generar_lista_compras(self) -> dict:
        """
        Genera la lista de compras automatizada.
        Corresponde a CU55 — Generar lista de compras automatizada.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/inventory/purchase-orders/suggested"
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU63: gestionar menú ──────────────────────────────

    async def activar_desactivar_bebida(
        self, drink_id: int, activo: bool
    ) -> dict:
        """
        Activa o desactiva una bebida del menú.
        Corresponde a CU63 — Gestionar menú. Alimenta g4-menu.html.
        """
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{BASE_URL}/admin/menu/drinks/{drink_id}/status",
                json={"activo": activo},
            )
        if r.status_code == 200:
            return await self.mostrar_confirmacion()
        return await self.mostrar_error()

    async def actualizar_precio_bebida(
        self, drink_id: int,
        precio_chico: Optional[float] = None,
        precio_mediano: Optional[float] = None,
        precio_grande: Optional[float] = None,
    ) -> dict:
        """Actualiza precios de una bebida. CU63."""
        async with httpx.AsyncClient() as client:
            r = await client.patch(
                f"{BASE_URL}/admin/menu/drinks/{drink_id}/prices",
                json={
                    "precio_chico": precio_chico,
                    "precio_mediano": precio_mediano,
                    "precio_grande": precio_grande,
                },
            )
        return r.json() if r.status_code == 200 else {}

    # ── Feedback UI ───────────────────────────────────────

    async def mostrar_confirmacion(self) -> dict:
        """Muestra mensaje de éxito en la pantalla. CU48/CU56/CU57."""
        return {"exito": True, "mensaje": "✅ Operación completada correctamente."}

    async def mostrar_error(self) -> dict:
        """Muestra mensaje de error en la pantalla. CU48/CU56/CU57."""
        return {"error": True, "mensaje": "❌ Ocurrió un error. Intenta nuevamente."}


# ══════════════════════════════════════════════════════════
# ReportsScreen — g1-dashboard.html, g2-auditoria.html,
#                 g6-reportes.html, g7-configuracion.html
# CU54, CU60, CU61, CU62, CU64, CU65
# ══════════════════════════════════════════════════════════

class ReportsScreen:
    """
    Pantalla de reportes y configuración del gerente.
    Corresponde a g1-dashboard, g2-auditoria, g6-reportes, g7-configuracion.

    Atributos del diagrama:
        inicio: Date
        fin: Date
    """

    def __init__(self):
        self.inicio: Optional[datetime] = None
        self.fin: Optional[datetime] = None
        self._reporte_actual: Optional[dict] = None

    async def seleccionar_rango_fechas(
        self, inicio: datetime, fin: datetime
    ) -> dict:
        """
        El gerente establece el rango de fechas del reporte.
        Corresponde a seleccionarRangoFechas(inicio, fin) — CU54.
        """
        if inicio > fin:
            return {"error": "La fecha de inicio no puede ser posterior a la fin."}
        self.inicio = inicio
        self.fin = fin
        return {
            "rango_configurado": True,
            "inicio": inicio.isoformat(),
            "fin": fin.isoformat(),
        }

    async def mostrar_reporte_en_pantalla(self) -> Optional[dict]:
        """
        Genera y retorna el reporte para g6-reportes.html.
        Corresponde a mostrarReporteEnPantalla() — CU54.
        """
        if not self.inicio or not self.fin:
            return {"error": "Selecciona un rango de fechas primero."}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/reports/full",
                params={
                    "fecha_inicio": self.inicio.isoformat(),
                    "fecha_fin": self.fin.isoformat(),
                },
            )
        if r.status_code == 200:
            self._reporte_actual = r.json()
        return self._reporte_actual

    async def generar_reporte_por_partes_o_enviar_email(
        self,
        enviar_email: bool = False,
        email_destino: str = "",
    ) -> dict:
        """
        Exporta el reporte o lo envía por email.
        Corresponde a generarReportePorPartesOEnviarEmail() — CU54.
        """
        if not self._reporte_actual:
            return {"error": "Genera un reporte primero."}
        if enviar_email and email_destino:
            return {"enviado": True, "destino": email_destino}
        return {"exportado": True, "formato": "json"}

    # ── CU60: reporte de ventas ───────────────────────────

    async def ver_reporte_ventas(self) -> dict:
        """Carga reporte de ventas en g6-reportes.html. CU60."""
        if not self.inicio or not self.fin:
            return {}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/reports/sales",
                params={
                    "fecha_inicio": self.inicio.isoformat(),
                    "fecha_fin": self.fin.isoformat(),
                },
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU61: bebidas populares ───────────────────────────

    async def ver_bebidas_populares(self, top: int = 10) -> dict:
        """Carga análisis de bebidas populares. CU61."""
        if not self.inicio or not self.fin:
            return {}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/reports/drinks/popular",
                params={
                    "fecha_inicio": self.inicio.isoformat(),
                    "fecha_fin": self.fin.isoformat(),
                    "top": top,
                },
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU62: eficiencia ──────────────────────────────────

    async def ver_eficiencia_preparacion(self) -> dict:
        """Carga reporte de eficiencia en g1-dashboard.html. CU62."""
        if not self.inicio or not self.fin:
            return {}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/reports/orders/efficiency",
                params={
                    "fecha_inicio": self.inicio.isoformat(),
                    "fecha_fin": self.fin.isoformat(),
                },
            )
        return r.json() if r.status_code == 200 else {}

    # ── CU64: configurar umbrales ─────────────────────────

    async def acceder_configuracion_alertas(self) -> dict:
        """
        Carga la configuración actual de umbrales en g7-configuracion.html.
        Corresponde a Acceder_configuracion_alertas() — CU64.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/admin/thresholds")
        return r.json() if r.status_code == 200 else {}

    async def aplicar_configuracion_umbrales(
        self,
        umbral_stock_minimo: Optional[float] = None,
        umbral_tiempo_prep: Optional[int] = None,
        umbral_ventas_bajas: Optional[float] = None,
        umbral_desperdicio: Optional[float] = None,
    ) -> dict:
        """
        Guarda la configuración de umbrales desde g7-configuracion.html.
        Corresponde a Aplicar_configuracion_umbrales() — CU64.
        """
        payload = {}
        if umbral_stock_minimo is not None:
            payload["umbral_stock_minimo"] = umbral_stock_minimo
        if umbral_tiempo_prep is not None:
            payload["umbral_tiempo_prep"] = umbral_tiempo_prep
        if umbral_ventas_bajas is not None:
            payload["umbral_ventas_bajas"] = umbral_ventas_bajas
        if umbral_desperdicio is not None:
            payload["umbral_desperdicio"] = umbral_desperdicio

        async with httpx.AsyncClient() as client:
            r = await client.put(f"{BASE_URL}/admin/thresholds", json=payload)
        return r.json() if r.status_code == 200 else {}

    async def confirmar_configuracion_exitosa(self) -> dict:
        """
        Muestra confirmación de umbrales guardados.
        Corresponde a Confirmar_configuracion_exitosa() — CU64.
        """
        return {"configurado": True, "mensaje": "✅ Umbrales actualizados correctamente."}

    # ── CU65: auditoría ───────────────────────────────────

    async def seleccionar_filtros_busqueda(self) -> dict:
        """
        Inicializa los filtros de búsqueda de auditoría en g2-auditoria.html.
        Corresponde a Seleccionar_filtros_busqueda() — CU65.
        """
        return {"filtros_disponibles": True, "pantalla": "auditoria"}

    async def confirmar_busqueda_auditoria(
        self,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        tipo_evento: Optional[str] = None,
        usuario_id: Optional[int] = None,
        limit: int = 100,
    ) -> dict:
        """
        Ejecuta la búsqueda en el registro de auditoría.
        Corresponde a Confirmar_busqueda_auditoria() — CU65.
        Alimenta g2-auditoria.html con los resultados.
        """
        params = {"limit": limit}
        if fecha_inicio:
            params["fecha_inicio"] = fecha_inicio.isoformat()
        if fecha_fin:
            params["fecha_fin"] = fecha_fin.isoformat()
        if tipo_evento:
            params["tipo_evento"] = tipo_evento
        if usuario_id:
            params["usuario_id"] = usuario_id

        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/admin/audit", params=params)
        return r.json() if r.status_code == 200 else {}

    async def mostrar_registros_auditoria(
        self, registros: list
    ) -> list:
        """
        Retorna los registros formateados para g2-auditoria.html.
        Corresponde a Mostrar_registros_auditoria() — CU65.
        """
        return registros