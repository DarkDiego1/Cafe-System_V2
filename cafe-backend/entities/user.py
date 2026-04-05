"""
entities/user.py
Módulo 01 — Experiencia del Cliente (CEM)

Columnas reales de la tabla users:
  - password_hash (original) + contrasena_hash (alias)
  - rol: 'Cliente' | 'Barista' | 'Empleado' | 'Gerente' | 'Admin'
  - fecha_nacimiento (original) + fecha_cumpleanos (alias añadido)
  - fecha_creacion  (no fecha_registro)
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class User:
    id: str                              # UUID
    nombre_completo: str
    email: str
    rol: str = "Cliente"
    telefono: Optional[str] = None
    fecha_registro: datetime = field(default_factory=datetime.now)
    fecha_cumpleanos: Optional[date] = None
    puntos_lealtad: int = 0
    activo: bool = True
    metodo_pago_defecto: Optional[str] = None
    preferencias_alimenticias: list = field(default_factory=list)

    # ── CU67/CU68: programa de lealtad ───────────────────────────────

    def agregar_puntos(self, puntos: int) -> None:
        if puntos < 0:
            raise ValueError("Los puntos deben ser positivos.")
        self.puntos_lealtad += puntos

    def canjear_puntos(self, puntos: int) -> None:
        """CU68 — Canjear puntos."""
        if puntos > self.puntos_lealtad:
            raise ValueError(
                f"Saldo insuficiente: {self.puntos_lealtad} pts disponibles."
            )
        self.puntos_lealtad -= puntos

    # ── CU70: cupón de cumpleaños ─────────────────────────────────────

    def es_cumpleanos_hoy(self) -> bool:
        """Corresponde a buscarCumpleanerosHoy() — CU70."""
        if not self.fecha_cumpleanos:
            return False
        hoy = date.today()
        return (
            self.fecha_cumpleanos.month == hoy.month
            and self.fecha_cumpleanos.day == hoy.day
        )

    # ── CU66 ─────────────────────────────────────────────────────────

    def actualizar_preferencias(self, preferencias: list) -> None:
        self.preferencias_alimenticias = preferencias

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre_completo": self.nombre_completo,
            "email": self.email,
            "rol": self.rol,
            "telefono": self.telefono,
            "fecha_registro": self.fecha_registro.isoformat(),
            "fecha_cumpleanos": self.fecha_cumpleanos.isoformat() if self.fecha_cumpleanos else None,
            "puntos_lealtad": self.puntos_lealtad,
            "activo": self.activo,
            "metodo_pago_defecto": self.metodo_pago_defecto,
            "preferencias_alimenticias": self.preferencias_alimenticias,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "User":
        """
        Soporta tanto fecha_nacimiento (original) como
        fecha_cumpleanos (columna añadida).
        """
        fecha_nac = row.get("fecha_cumpleanos") or row.get("fecha_nacimiento")

        # preferencias puede ser JSON string o lista
        prefs = row.get("preferencias_alimenticias") or []
        if isinstance(prefs, str):
            import json
            try:
                prefs = json.loads(prefs)
            except Exception:
                prefs = []

        return cls(
            id=str(row["id"]),
            nombre_completo=row.get("nombre_completo", ""),
            email=row.get("email", ""),
            rol=row.get("rol", "Cliente"),
            telefono=row.get("telefono"),
            fecha_registro=row.get("fecha_creacion") or datetime.now(),
            fecha_cumpleanos=fecha_nac,
            puntos_lealtad=row.get("puntos_lealtad", 0),
            activo=row.get("activo", True),
            metodo_pago_defecto=row.get("metodo_pago_defecto"),
            preferencias_alimenticias=prefs,
        )