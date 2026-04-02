"""
services/report_generator.py
Módulo 03 — Gestión y Administración (MAM)

Utilitario: ReportGenerator
Casos de uso: CU54, CU60, CU61, CU62

No accede a BD directamente; recibe datos ya procesados de los servicios
y los transforma en documentos estructurados.
"""

from datetime import datetime
from typing import Any


class ReportGenerator:
    """
    Formatea datos de ventas e inventario en documentos de reporte.
    Corresponde a generarDocumentoReporte() del diagrama CU54.
    """

    # ── Método base ───────────────────────────────────────────────────

    def generar_documento_reporte(
        self,
        tipo: str,
        datos: dict,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        formato: str = "json",
    ) -> dict:
        """
        Envuelve los datos con metadatos estándar.
        Corresponde a generarDocumentoReporte() — diagrama CU54.

        Args:
            tipo: 'ventas' | 'consumo' | 'eficiencia' | 'inventario'
            datos: Datos ya calculados por los servicios.
            fecha_inicio / fecha_fin: Rango del reporte.
            formato: 'json' | 'csv' (para extensión futura).
        """
        return {
            "metadata": {
                "tipo": tipo,
                "periodo": {
                    "inicio": fecha_inicio.isoformat(),
                    "fin": fecha_fin.isoformat(),
                },
                "generado_en": datetime.now().isoformat(),
                "formato": formato,
                "version": "1.0",
            },
            "contenido": datos,
        }

    # ── CU60 — Reporte de ventas ──────────────────────────────────────

    def generar_reporte_ventas(
        self,
        datos_ventas: dict,
        bebidas_populares: list,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> dict:
        """Combina datos de ventas con el ranking de bebidas."""
        contenido = {
            "resumen_ventas": datos_ventas,
            "bebidas_populares": bebidas_populares,
        }
        return self.generar_documento_reporte(
            tipo="ventas",
            datos=contenido,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    # ── CU54 — Reporte de consumo ─────────────────────────────────────

    def generar_reporte_consumo(
        self,
        consumo_teorico_vs_real: dict,
        ingredientes_descontados: list,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> dict:
        """Combina análisis teórico vs real con detalle de ingredientes."""
        contenido = {
            "consumo_teorico_vs_real": consumo_teorico_vs_real,
            "detalle_ingredientes": ingredientes_descontados,
        }
        return self.generar_documento_reporte(
            tipo="consumo",
            datos=contenido,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    # ── CU62 — Reporte de eficiencia ──────────────────────────────────

    def generar_reporte_eficiencia(
        self,
        datos_eficiencia: dict,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> dict:
        return self.generar_documento_reporte(
            tipo="eficiencia",
            datos=datos_eficiencia,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    # ── CU50 — Snapshot de inventario ────────────────────────────────

    def generar_reporte_inventario(
        self,
        niveles: list,
        alertas: list,
    ) -> dict:
        ahora = datetime.now()
        contenido = {
            "niveles": niveles,
            "alertas_activas": alertas,
            "total_ingredientes": len(niveles),
            "con_alerta": len(alertas),
            "valor_total_bodega": round(
                sum(n.get("stock_actual", 0) * n.get("costo_unitario", 0) for n in niveles), 2
            ),
        }
        return self.generar_documento_reporte(
            tipo="inventario",
            datos=contenido,
            fecha_inicio=ahora,
            fecha_fin=ahora,
        )

    # ── Exportación CSV (extensible) ──────────────────────────────────

    def exportar_csv(self, datos: list[dict], campos: list[str]) -> str:
        """
        Convierte una lista de dicts a formato CSV string.
        Útil para el botón 'Descargar CSV' de ReportsScreen.
        """
        lineas = [",".join(campos)]
        for fila in datos:
            lineas.append(",".join(str(fila.get(c, "")) for c in campos))
        return "\n".join(lineas)