"""
routers/reports.py
Módulo 03 — Gestión y Administración (MAM)

Router FastAPI que delega en ReportsController.
Cubre: CU54, CU60, CU61, CU62
"""

from fastapi import APIRouter, Query
from datetime import datetime

from controllers.reports_controller import ReportsController

router = APIRouter()
ctrl   = ReportsController()


@router.get("/full")
async def get_full_report(
    fecha_inicio: datetime = Query(...),
    fecha_fin:    datetime = Query(...),
):
    """CU54 — Reporte completo de ventas + consumo de ingredientes."""
    return await ctrl.generar_reporte_completo(fecha_inicio, fecha_fin)


@router.get("/sales")
async def get_sales_report(
    fecha_inicio: datetime = Query(...),
    fecha_fin:    datetime = Query(...),
):
    """CU60 — Reporte de ventas del periodo."""
    return await ctrl.generar_reporte_ventas(fecha_inicio, fecha_fin)


@router.get("/drinks/popular")
async def get_popular_drinks(
    fecha_inicio: datetime = Query(...),
    fecha_fin:    datetime = Query(...),
    top:          int      = Query(default=10, ge=1, le=50),
):
    """CU61 — Análisis de bebidas populares."""
    return await ctrl.generar_reporte_bebidas_populares(fecha_inicio, fecha_fin, top)


@router.get("/orders/efficiency")
async def get_efficiency_report(
    fecha_inicio: datetime = Query(...),
    fecha_fin:    datetime = Query(...),
):
    """CU62 — Eficiencia de preparación."""
    return await ctrl.generar_reporte_eficiencia(fecha_inicio, fecha_fin)


@router.get("/inventory/snapshot")
async def get_inventory_snapshot():
    """CU50 — Snapshot actual del inventario con valor en bodega."""
    return await ctrl.generar_snapshot_inventario()