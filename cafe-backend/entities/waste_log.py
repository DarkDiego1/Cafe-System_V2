"""
entities/waste_log.py
Módulo 03 — Gestión y Administración (MAM)

Entidad de dominio: WasteLog
Casos de uso: CU56 — Registrar merma de inventario
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class WasteLog:
    """
    Registro contable de una merma o desperdicio de ingrediente.
    Mapea contra la tabla `waste_logs` de PostgreSQL.
    """

    id: int
    ingrediente_id: int
    cantidad: float
    motivo: str
    costo_estimado: float
    registrado_por: Optional[int]        # employee_id
    fecha: datetime = field(default_factory=datetime.now)
    # Datos enriquecidos (join)
    nombre_ingrediente: str = ""
    unidad_medida: str = ""
    nombre_empleado: str = ""

    # ── CU56: registrarPerdidaContable ────────────────────────────────

    @classmethod
    def registrar_perdida_contable(
        cls,
        id: int,
        ingrediente_id: int,
        cantidad: float,
        motivo: str,
        costo_unitario: float,
        registrado_por: Optional[int] = None,
        nombre_ingrediente: str = "",
        unidad_medida: str = "",
    ) -> "WasteLog":
        """
        Crea el registro de merma con el costo económico calculado.
        Corresponde a registrarPerdidaContable(motivo) del diagrama CU56.

        El costo_estimado = cantidad × costo_unitario del ingrediente.
        """
        return cls(
            id=id,
            ingrediente_id=ingrediente_id,
            cantidad=cantidad,
            motivo=motivo,
            costo_estimado=round(cantidad * costo_unitario, 2),
            registrado_por=registrado_por,
            nombre_ingrediente=nombre_ingrediente,
            unidad_medida=unidad_medida,
        )

    def resumen(self) -> str:
        """Texto de auditoría para logs y notificaciones."""
        return (
            f"[{self.fecha.strftime('%Y-%m-%d %H:%M')}] "
            f"Merma: {self.cantidad} {self.unidad_medida} de '{self.nombre_ingrediente}' "
            f"— Motivo: {self.motivo} "
            f"— Impacto: ${self.costo_estimado:.2f}"
        )

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ingrediente_id": self.ingrediente_id,
            "ingrediente": self.nombre_ingrediente,
            "unidad_medida": self.unidad_medida,
            "cantidad": self.cantidad,
            "motivo": self.motivo,
            "costo_estimado": self.costo_estimado,
            "registrado_por": self.registrado_por,
            "empleado": self.nombre_empleado,
            "fecha": self.fecha.isoformat(),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "WasteLog":
        return cls(
            id=row["id"],
            ingrediente_id=row["ingrediente_id"],
            cantidad=float(row["cantidad"]),
            motivo=row["motivo"],
            costo_estimado=float(row.get("costo_estimado", 0)),
            registrado_por=row.get("registrado_por"),
            fecha=row.get("fecha") or datetime.now(),
            nombre_ingrediente=row.get("ingrediente", ""),
            unidad_medida=row.get("unidad_medida", ""),
            nombre_empleado=row.get("registrado_por_nombre", ""),
        )