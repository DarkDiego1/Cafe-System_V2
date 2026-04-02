"""
entities/supplier.py
Módulo 03 — Gestión y Administración (MAM)

Entidad de dominio: Supplier
Casos de uso: CU55, CU57
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Supplier:
    """
    Representa un proveedor de ingredientes.
    Mapea contra la tabla `suppliers` de PostgreSQL.
    """

    id: int
    nombre: str
    contacto: str
    telefono: str
    email: str
    activo: bool = True
    notas: Optional[str] = None
    fecha_registro: datetime = field(default_factory=datetime.now)

    # ── CU55: validarProveedorActivo / resaltarProveedorInactivo ──────

    def validar_proveedor_activo(self) -> bool:
        """
        Verifica si el proveedor puede recibir órdenes.
        Corresponde a validarProveedorActivo() del diagrama CU55.
        """
        return self.activo

    def resaltar_proveedor_inactivo(self) -> Optional[str]:
        """
        Retorna mensaje de advertencia si el proveedor está inactivo.
        Corresponde a resaltarProveedorInactivo() del diagrama CU55.
        Retorna None si el proveedor está activo.
        """
        if not self.activo:
            return (
                f"⚠ El proveedor '{self.nombre}' está inactivo. "
                "Se debe seleccionar un proveedor alternativo."
            )
        return None

    # ── CU57: activar / desactivar ────────────────────────────────────

    def activar(self) -> None:
        """Reactiva al proveedor para que pueda recibir órdenes."""
        self.activo = True

    def desactivar(self) -> None:
        """Marca al proveedor como inactivo sin eliminarlo."""
        self.activo = False

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "contacto": self.contacto,
            "telefono": self.telefono,
            "email": self.email,
            "activo": self.activo,
            "notas": self.notas,
            "fecha_registro": self.fecha_registro.isoformat(),
            "advertencia": self.resaltar_proveedor_inactivo(),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Supplier":
        """Construye un Supplier desde un asyncpg Record."""
        return cls(
            id=row["id"],
            nombre=row["nombre"],
            contacto=row.get("contacto", ""),
            telefono=row.get("telefono", ""),
            email=row.get("email", ""),
            activo=row.get("activo", True),
            notas=row.get("notas"),
            fecha_registro=row.get("fecha_registro") or datetime.now(),
        )