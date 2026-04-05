"""
entities/coupon.py
Módulo 01 — Experiencia del Cliente (CEM)

Columnas reales de la tabla coupons:
  - valor_descuento  → alias: descuento
  - usos_maximos     → alias: uso_maximo
  - activo           → alias: valido
  - usuario_especifico_id → alias: user_id
  - tipo_descuento: 'Porcentaje' | 'MontoFijo' | 'BebidaGratis'
  - fecha_inicio / fecha_fin: tipo DATE
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import uuid


@dataclass
class Coupon:
    id: int
    codigo: str
    descuento: float                     # = valor_descuento
    tipo_descuento: str = "Porcentaje"   # Porcentaje | MontoFijo | BebidaGratis
    valido: bool = True                  # = activo
    motivo_invalido: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    uso_maximo: Optional[int] = None     # = usos_maximos
    usos_actuales: int = 0
    solo_primera_compra: bool = False
    user_id: Optional[str] = None        # = usuario_especifico_id

    # ── CU31 ─────────────────────────────────────────────────────────

    def esta_vigente(self) -> bool:
        hoy = date.today()
        if self.fecha_inicio and hoy < self.fecha_inicio:
            return False
        if self.fecha_fin and hoy > self.fecha_fin:
            return False
        return True

    def tiene_usos_disponibles(self) -> bool:
        if self.uso_maximo is None:
            return True
        return self.usos_actuales < self.uso_maximo

    def es_valido(self) -> tuple[bool, Optional[str]]:
        """Corresponde a verificarCupon() — CU31."""
        if not self.valido:
            return False, "El cupón ha sido desactivado."
        if not self.esta_vigente():
            return False, "El cupón ha expirado o aún no está vigente."
        if not self.tiene_usos_disponibles():
            return False, "El cupón ha alcanzado su límite de usos."
        return True, None

    def calcular_descuento(self, subtotal: float) -> float:
        """Corresponde a aplicarDescuento() — CU31."""
        tipo = self.tipo_descuento.lower()
        if tipo == "porcentaje":
            return round(subtotal * (self.descuento / 100), 2)
        elif tipo == "montofijo":
            return min(self.descuento, subtotal)
        return 0.0  # BebidaGratis — se maneja aparte

    # ── CU70 ─────────────────────────────────────────────────────────

    @classmethod
    def generar_cupon_unico(
        cls,
        descuento: float = 15.0,
        tipo_descuento: str = "Porcentaje",
        user_id: Optional[str] = None,
        dias_vigencia: int = 7,
    ) -> "Coupon":
        """Corresponde a generarCuponUnico() — CU70."""
        from datetime import timedelta
        codigo = f"BDAY-{uuid.uuid4().hex[:8].upper()}"
        hoy    = date.today()
        return cls(
            id=0,
            codigo=codigo,
            descuento=descuento,
            tipo_descuento=tipo_descuento,
            valido=True,
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=dias_vigencia),
            uso_maximo=1,
            user_id=user_id,
        )

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        valido, motivo = self.es_valido()
        return {
            "id": self.id,
            "codigo": self.codigo,
            "descuento": self.descuento,
            "tipo_descuento": self.tipo_descuento,
            "valido": valido,
            "motivo_invalido": motivo,
            "fecha_fin": self.fecha_fin.isoformat() if self.fecha_fin else None,
            "usos_disponibles": (
                self.uso_maximo - self.usos_actuales
                if self.uso_maximo else None
            ),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Coupon":
        """Soporta columnas originales y alias añadidos."""
        descuento  = row.get("descuento") or row.get("valor_descuento") or 0
        uso_maximo = row.get("uso_maximo") or row.get("usos_maximos")
        valido     = row.get("valido")
        if valido is None:
            valido = row.get("activo", True)
        user_id = row.get("user_id") or row.get("usuario_especifico_id")

        def to_date(val):
            if val is None:
                return None
            if isinstance(val, date):
                return val
            if isinstance(val, datetime):
                return val.date()
            return None

        return cls(
            id=row["id"],
            codigo=row["codigo"],
            descuento=float(descuento),
            tipo_descuento=row.get("tipo_descuento", "Porcentaje"),
            valido=bool(valido),
            fecha_inicio=to_date(row.get("fecha_inicio")),
            fecha_fin=to_date(row.get("fecha_fin")),
            uso_maximo=uso_maximo,
            usos_actuales=row.get("usos_actuales", 0),
            solo_primera_compra=row.get("solo_primera_compra", False),
            user_id=str(user_id) if user_id else None,
        )