"""
controllers/reports_controller.py
Módulo 03 — Gestión y Administración (MAM)

Controlador: ReportsController
Casos de uso: CU54, CU60, CU61, CU62

Orquesta SalesService e InventoryService para construir
los reportes que ReportsScreen necesita mostrar o exportar.
"""

from datetime import datetime
from typing import Optional
from fastapi import HTTPException

from services.sales_service import SalesService
from services.inventory_service import InventoryService
from services.report_generator import ReportGenerator

TIMEOUT_SEG = 30


class ReportsController:
    """
    Intermediario entre los routers de reportes y los servicios.

    Corresponde a los métodos:
      solicitarVentasPeriodo()
      obtenerIngredientesDescontados()
      calcularConsumoTeoricoVsReal()
      detectarTimeout()
    del diagrama CU54.
    """

    def __init__(self) -> None:
        self._sales_service     = SalesService()
        self._inventory_service = InventoryService()
        self._report_generator  = ReportGenerator()

    # ── CU54: reporte completo ────────────────────────────────────────

    async def generar_reporte_completo(
        self,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        formato: str = "json",
    ) -> dict:
        """
        Orquesta todos los sub-reportes en una sola respuesta.
        Corresponde al flujo:
          seleccionarRangoFechas()
          → solicitarVentasPeriodo()
          → obtenerIngredientesDescontados()
          → calcularConsumoTeoricoVsReal()
          → generarDocumentoReporte()
        del diagrama CU54.
        """
        if fecha_inicio > fecha_fin:
            raise HTTPException(
                status_code=422,
                detail="La fecha de inicio no puede ser posterior a la fecha de fin."
            )

        t0 = datetime.now()

        ventas    = await self.solicitar_ventas_periodo(fecha_inicio, fecha_fin)
        ing_desc  = await self.obtener_ingredientes_descontados(fecha_inicio, fecha_fin)
        consumo   = await self.calcular_consumo_teorico_vs_real(fecha_inicio, fecha_fin)
        bebidas   = await self._sales_service.obtener_bebidas_populares(fecha_inicio, fecha_fin)

        # detectarTimeout()
        if self.detectar_timeout(t0):
            raise HTTPException(
                status_code=504,
                detail="El reporte tardó demasiado en generarse. Reduzca el rango de fechas."
            )

        reporte_ventas   = self._report_generator.generar_reporte_ventas(ventas, bebidas, fecha_inicio, fecha_fin)
        reporte_consumo  = self._report_generator.generar_reporte_consumo(consumo, ing_desc, fecha_inicio, fecha_fin)

        return {
            "ventas":   reporte_ventas,
            "consumo":  reporte_consumo,
            "generado_en": datetime.now().isoformat(),
        }

    async def solicitar_ventas_periodo(
        self, fecha_inicio: datetime, fecha_fin: datetime
    ) -> dict:
        """
        Corresponde a solicitarVentasPeriodo() — diagrama CU54.
        """
        return await self._sales_service.obtener_ventas_periodo(fecha_inicio, fecha_fin)

    async def obtener_ingredientes_descontados(
        self, fecha_inicio: datetime, fecha_fin: datetime
    ) -> list[dict]:
        """
        Corresponde a obtenerIngredientesDescontados() — diagrama CU54.
        """
        return await self._sales_service.obtener_ingredientes_descontados(fecha_inicio, fecha_fin)

    async def calcular_consumo_teorico_vs_real(
        self, fecha_inicio: datetime, fecha_fin: datetime
    ) -> dict:
        """
        Corresponde a calcularConsumoTeoricoVsReal() — diagrama CU54.
        """
        return await self._inventory_service.calcular_consumo_teorico_vs_real(
            fecha_inicio, fecha_fin
        )

    def detectar_timeout(self, inicio: datetime) -> bool:
        """
        Corresponde a detectarTimeout() — diagrama CU54.
        Retorna True si la operación superó TIMEOUT_SEG.
        """
        return (datetime.now() - inicio).total_seconds() > TIMEOUT_SEG

    # ── CU60: reporte de ventas ───────────────────────────────────────

    async def generar_reporte_ventas(
        self, fecha_inicio: datetime, fecha_fin: datetime
    ) -> dict:
        ventas  = await self._sales_service.obtener_ventas_periodo(fecha_inicio, fecha_fin)
        bebidas = await self._sales_service.obtener_bebidas_populares(fecha_inicio, fecha_fin)
        return self._report_generator.generar_reporte_ventas(
            ventas, bebidas, fecha_inicio, fecha_fin
        )

    # ── CU61: bebidas populares ───────────────────────────────────────

    async def generar_reporte_bebidas_populares(
        self, fecha_inicio: datetime, fecha_fin: datetime, top: int = 10
    ) -> dict:
        bebidas = await self._sales_service.obtener_bebidas_populares(fecha_inicio, fecha_fin, top)
        return {
            "periodo": {"inicio": fecha_inicio.isoformat(), "fin": fecha_fin.isoformat()},
            "top": top,
            "bebidas": bebidas,
        }

    # ── CU62: eficiencia ──────────────────────────────────────────────

    async def generar_reporte_eficiencia(
        self, fecha_inicio: datetime, fecha_fin: datetime
    ) -> dict:
        datos = await self._sales_service.obtener_eficiencia_preparacion(
            fecha_inicio, fecha_fin
        )
        return self._report_generator.generar_reporte_eficiencia(
            datos, fecha_inicio, fecha_fin
        )

    # ── CU50: snapshot de inventario ──────────────────────────────────

    async def generar_snapshot_inventario(self) -> dict:
        niveles = await self._inventory_service.obtener_niveles_inventario()
        alertas_ids = [n["id"] for n in niveles if n.get("alerta_stock")]
        return self._report_generator.generar_reporte_inventario(niveles, alertas_ids)