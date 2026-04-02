"""
entities/alert_threshold.py
Módulo 03 — Gestión y Administración (MAM)

Entidad de dominio: AlertThreshold
Casos de uso: CU64 — Configurar umbrales de alertas de stock

Almacena los umbrales globales del sistema que disparan alertas
automáticas para el gerente:
  - umbral_stock_minimo   → porcentaje de stock que activa alerta
  - umbral_tiempo_prep    → segundos máximos de preparación
  - umbral_ventas_bajas   → monto mínimo de ventas diarias esperado
  - umbral_desperdicio    → porcentaje de merma aceptable vs. consumo
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AlertThreshold:
    """
    Configuración de umbrales del sistema para alertas automáticas.
    Mapea contra la tabla `alert_thresholds` de PostgreSQL.
    """

    id: int
    umbral_stock_minimo: float       # % relativo (ej. 20 = alerta cuando queda 20% del mínimo)
    umbral_tiempo_prep: int          # segundos máximos tolerables de preparación
    umbral_ventas_bajas: float       # ventas mínimas diarias esperadas (pesos)
    umbral_desperdicio: float        # % de merma aceptable vs. consumo teórico
    modificado_por: Optional[int]    # employee_id del gerente que hizo el cambio
    fecha_modificacion: datetime = field(default_factory=datetime.now)

    # ── CU64: métodos del diagrama de secuencia ───────────────────────

    def configurar_umbral_stock_minimo(self, valor: float) -> None:
        """
        Configura el porcentaje de stock mínimo que activa alerta.
        Corresponde a Configurar_umbral_stock_minimo() — CU64.
        """
        if valor < 0 or valor > 100:
            raise ValueError("El umbral de stock mínimo debe estar entre 0 y 100%.")
        self.umbral_stock_minimo = valor
        self.fecha_modificacion = datetime.now()

    def configurar_umbral_tiempo_preparacion(self, segundos: int) -> None:
        """
        Configura el tiempo máximo de preparación en segundos.
        Corresponde a Configurar_umbral_tiempo_preparacion() — CU64.
        """
        if segundos <= 0:
            raise ValueError("El umbral de tiempo debe ser un valor positivo.")
        self.umbral_tiempo_prep = segundos
        self.fecha_modificacion = datetime.now()

    def configurar_umbral_ventas_bajas(self, monto: float) -> None:
        """
        Configura el mínimo de ventas diarias esperado.
        Corresponde a Configurar_umbral_ventas_bajas() — CU64.
        """
        if monto < 0:
            raise ValueError("El monto mínimo de ventas no puede ser negativo.")
        self.umbral_ventas_bajas = monto
        self.fecha_modificacion = datetime.now()

    def configurar_umbral_desperdicio(self, porcentaje: float) -> None:
        """
        Configura el porcentaje máximo de desperdicio aceptable.
        Corresponde a Configurar_umbral_desperdicio() — CU64.
        """
        if porcentaje < 0 or porcentaje > 100:
            raise ValueError("El porcentaje de desperdicio debe estar entre 0 y 100%.")
        self.umbral_desperdicio = porcentaje
        self.fecha_modificacion = datetime.now()

    def aplicar_configuracion(self, modificado_por: int) -> None:
        """
        Registra quién aplicó los cambios.
        Corresponde a Aplicar_configuracion_umbrales() — CU64.
        """
        self.modificado_por = modificado_por
        self.fecha_modificacion = datetime.now()

    # ── Validación de alertas ─────────────────────────────────────────

    def evaluar_stock(self, nivel_pct: float) -> bool:
        """True si el nivel de stock está por debajo del umbral configurado."""
        return nivel_pct <= self.umbral_stock_minimo

    def evaluar_tiempo_prep(self, tiempo_seg: int) -> bool:
        """True si el tiempo de preparación supera el umbral."""
        return tiempo_seg > self.umbral_tiempo_prep

    def evaluar_ventas(self, ventas_dia: float) -> bool:
        """True si las ventas del día están por debajo del mínimo."""
        return ventas_dia < self.umbral_ventas_bajas

    def evaluar_desperdicio(self, pct_merma: float) -> bool:
        """True si el porcentaje de merma supera el umbral aceptable."""
        return pct_merma > self.umbral_desperdicio

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "umbral_stock_minimo": self.umbral_stock_minimo,
            "umbral_tiempo_prep": self.umbral_tiempo_prep,
            "umbral_ventas_bajas": self.umbral_ventas_bajas,
            "umbral_desperdicio": self.umbral_desperdicio,
            "modificado_por": self.modificado_por,
            "fecha_modificacion": self.fecha_modificacion.isoformat(),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "AlertThreshold":
        return cls(
            id=row["id"],
            umbral_stock_minimo=float(row.get("umbral_stock_minimo", 20.0)),
            umbral_tiempo_prep=int(row.get("umbral_tiempo_prep", 600)),
            umbral_ventas_bajas=float(row.get("umbral_ventas_bajas", 1000.0)),
            umbral_desperdicio=float(row.get("umbral_desperdicio", 5.0)),
            modificado_por=row.get("modificado_por"),
            fecha_modificacion=row.get("fecha_modificacion") or datetime.now(),
        )

    @classmethod
    def defaults(cls) -> "AlertThreshold":
        """Retorna umbrales por defecto para primer uso del sistema."""
        return cls(
            id=1,
            umbral_stock_minimo=20.0,    # alerta cuando queda ≤20% sobre el mínimo
            umbral_tiempo_prep=600,       # 10 minutos máximo de preparación
            umbral_ventas_bajas=1000.0,  # $1,000 MXN mínimo por día
            umbral_desperdicio=5.0,      # máximo 5% de merma vs. consumo teórico
            modificado_por=None,
        )