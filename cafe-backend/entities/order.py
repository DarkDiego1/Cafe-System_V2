"""
entities/order.py
Módulo 02 — Producción y Operaciones (POM)
Compartida con M01 — Experiencia del Cliente
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List

ESTADOS_VALIDOS = [
    "pendiente", "pagado", "en_preparacion",
    "lista", "entregada", "cancelada", "con_problema",
]

TRANSICIONES_VALIDAS: dict[str, list[str]] = {
    "pendiente":      ["en_preparacion", "cancelada"],
    "pagado":         ["en_preparacion", "cancelada"],
    "en_preparacion": ["lista", "con_problema", "cancelada"],
    "lista":          ["entregada", "en_preparacion"],
    "entregada":      [],
    "cancelada":      [],
    "con_problema":   ["en_preparacion", "cancelada"],
}

ESTADO_BD_A_DOMINIO = {
    "Pendiente":        "pendiente",
    "Pagado":           "pagado",
    "EnPreparacion":    "en_preparacion",
    "ListaParaRecoger": "lista",
    "Entregada":        "entregada",
    "Cancelada":        "cancelada",
    "Rechazada":        "cancelada",
}


def _naive(dt: datetime) -> datetime:
    """Quita timezone para poder comparar fechas de distintas fuentes."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


@dataclass
class OrderItem:
    id: int
    bebida_id: int
    nombre_bebida: str
    tamano: str
    cantidad: int
    precio_final: float
    notas_item: Optional[str] = None
    imagen_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bebida_id": self.bebida_id,
            "nombre_bebida": self.nombre_bebida,
            "tamano": self.tamano,
            "cantidad": self.cantidad,
            "precio_final": self.precio_final,
            "notas_item": self.notas_item,
            "imagen_url": self.imagen_url,
        }


@dataclass
class Order:
    id: str
    codigo_orden: str
    estado: str = "pendiente"
    nombre_cliente: str = ""
    notas_generales: Optional[str] = None
    total: float = 0.0
    subtotal: float = 0.0
    descuento: float = 0.0
    propina: float = 0.0
    items: List[OrderItem] = field(default_factory=list)
    empleado_asignado_id: Optional[int] = None
    tiempo_preparacion_seg: Optional[int] = None
    entregada_a_tiempo: Optional[bool] = None
    fecha_creacion: datetime = field(default_factory=datetime.now)
    fecha_inicio_prep: Optional[datetime] = None
    fecha_lista: Optional[datetime] = None
    fecha_entrega: Optional[datetime] = None
    reporte_problema: Optional[str] = None

    def cambiar_estado(self, nuevo_estado: str) -> None:
        transiciones = TRANSICIONES_VALIDAS.get(self.estado, [])
        if nuevo_estado not in transiciones:
            raise ValueError(
                f"Transición inválida: '{self.estado}' → '{nuevo_estado}'. "
                f"Transiciones permitidas: {transiciones}"
            )
        self.estado = nuevo_estado
        self._registrar_timestamp(nuevo_estado)

    def _registrar_timestamp(self, estado: str) -> None:
        # Usar naive datetime para consistencia con la BD
        ahora = datetime.now()
        if estado == "en_preparacion" and not self.fecha_inicio_prep:
            self.fecha_inicio_prep = ahora
        elif estado == "lista":
            self.fecha_lista = ahora
        elif estado == "entregada":
            self.fecha_entrega = ahora

    def confirmacion_actualizacion_estado(self) -> dict:
        return {
            "orden_id":     self.id,
            "codigo":       self.codigo_orden,
            "estado":       self.estado,
            "estado_nuevo": self.estado,
            "timestamp":    datetime.now().isoformat(),
        }

    def revertir_a_en_preparacion(self) -> None:
        if self.estado != "lista":
            raise ValueError("Solo se puede revertir una orden en estado 'lista'.")
        self.estado = "en_preparacion"
        self.fecha_lista = None

    def obtener_datos_notificacion(self) -> dict:
        return {
            "orden_id":       self.id,
            "codigo_orden":   self.codigo_orden,
            "nombre_cliente": self.nombre_cliente,
            "estado":         self.estado,
            "items":          len(self.items),
        }

    def registrar_tiempo_preparacion(self, umbral_seg: int = 600) -> int:
        if not self.fecha_inicio_prep or not self.fecha_lista:
            raise ValueError(
                "La orden debe tener fecha_inicio_prep y fecha_lista."
            )
        # Normalizar a naive para evitar TypeError con timezones mixtas
        fl = _naive(self.fecha_lista)
        fi = _naive(self.fecha_inicio_prep)
        delta = (fl - fi).total_seconds()
        self.tiempo_preparacion_seg = int(delta)
        self.entregada_a_tiempo = self.tiempo_preparacion_seg <= umbral_seg
        return self.tiempo_preparacion_seg

    def reportar_problema(self, descripcion: str) -> None:
        self.reporte_problema = descripcion
        self.cambiar_estado("con_problema")

    def tiene_notas_especiales(self) -> bool:
        if self.notas_generales:
            return True
        return any(item.notas_item for item in self.items)

    def to_dict(self) -> dict:
        return {
            "id":                     self.id,
            "codigo_orden":           self.codigo_orden,
            "estado":                 self.estado,
            "nombre_cliente":         self.nombre_cliente,
            "notas_generales":        self.notas_generales,
            "tiene_notas":            self.tiene_notas_especiales(),
            "total":                  self.total,
            "items":                  [i.to_dict() for i in self.items],
            "empleado_asignado_id":   self.empleado_asignado_id,
            "tiempo_preparacion_seg": self.tiempo_preparacion_seg,
            "entregada_a_tiempo":     self.entregada_a_tiempo,
            "fecha_creacion":         self.fecha_creacion.isoformat(),
            "fecha_inicio_prep":      self.fecha_inicio_prep.isoformat() if self.fecha_inicio_prep else None,
            "fecha_lista":            self.fecha_lista.isoformat() if self.fecha_lista else None,
            "fecha_entrega":          self.fecha_entrega.isoformat() if self.fecha_entrega else None,
            "reporte_problema":       self.reporte_problema,
        }

    @classmethod
    def from_db_row(cls, row: dict, items: Optional[List[OrderItem]] = None) -> "Order":
        def parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(str(val))

        estado_raw = row.get("estado", "pendiente")
        estado = ESTADO_BD_A_DOMINIO.get(estado_raw, estado_raw.lower())

        return cls(
            id=str(row["id"]),
            codigo_orden=row.get("codigo_orden", ""),
            estado=estado,
            nombre_cliente=row.get("cliente", "") or row.get("nombre_cliente", ""),
            notas_generales=row.get("notas_generales"),
            total=float(row.get("total", 0)),
            subtotal=float(row.get("subtotal", 0)),
            descuento=float(row.get("descuento", 0)),
            propina=float(row.get("propina", 0)),
            items=items or [],
            empleado_asignado_id=row.get("empleado_asignado_id"),
            tiempo_preparacion_seg=row.get("tiempo_preparacion_seg"),
            entregada_a_tiempo=row.get("entregada_a_tiempo"),
            fecha_creacion=parse_dt(row.get("fecha_creacion")) or datetime.now(),
            fecha_inicio_prep=parse_dt(row.get("fecha_inicio_prep")),
            fecha_lista=parse_dt(row.get("fecha_lista")),
            fecha_entrega=parse_dt(row.get("fecha_entrega")),
            reporte_problema=row.get("reporte_problema"),
        )