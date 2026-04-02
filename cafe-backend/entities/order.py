"""
entities/order.py
Módulo 02 — Producción y Operaciones (POM)
Compartida con M01 — Experiencia del Cliente

Entidad de dominio: Order (Orden de Producción)
Casos de uso: CU36, CU37, CU38, CU42, CU43, CU44, CU45, CU47

NOTA DE ARQUITECTURA:
  Order pertenece al módulo donde tiene mayor protagonismo (M01 la crea,
  M02 la gestiona en producción). Esta clase sirve a ambos módulos:
  - M01 la crea cuando el cliente confirma el pedido
  - M02 la consume para gestionar estados de producción
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

# Estados válidos en el flujo de producción (CU38→CU42→CU44)
ESTADOS_VALIDOS = [
    "pendiente",        # recién creada por M01
    "en_preparacion",   # barista inició preparación — CU38
    "lista",            # lista para recoger — CU42
    "entregada",        # entregada al cliente — CU44
    "cancelada",        # cancelada antes de prepararse
    "con_problema",     # reportó problema — CU45
]

TRANSICIONES_VALIDAS: dict[str, list[str]] = {
    "pendiente":      ["en_preparacion", "cancelada"],
    "en_preparacion": ["lista", "con_problema", "cancelada"],
    "lista":          ["entregada", "en_preparacion"],  # en_preparacion = deshacer CU42
    "entregada":      [],
    "cancelada":      [],
    "con_problema":   ["en_preparacion", "cancelada"],
}


@dataclass
class OrderItem:
    """Ítem individual dentro de una orden (bebida + personalización)."""
    id: int
    bebida_id: int
    nombre_bebida: str
    tamano: str                         # chico | mediano | grande
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
    """
    Orden de producción — entidad central del Módulo 02.

    Atributos que M02 necesita además de los financieros de M01:
      - estado: flujo recibida → en_preparacion → lista → entregada
      - nombre_cliente: para pantalla pública (CU43)
      - notas_generales: nota especial del cliente (CU40)
      - tiempo_preparacion_seg: para métricas M03 (CU47)
      - empleado_asignado_id: barista que la prepara
    """

    id: str                             # UUID
    codigo_orden: str                   # código legible (ej. "ORD-0042")
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

    # ── CU38/CU42/CU44: cambiarEstado ────────────────────────────────

    def cambiar_estado(self, nuevo_estado: str) -> None:
        """
        Cambia el estado de la orden validando la transición.
        Corresponde a cambiarEstado(estado) — diagramas CU38, CU42, CU44.

        Raises:
            ValueError: Si la transición no es válida.
        """
        transiciones = TRANSICIONES_VALIDAS.get(self.estado, [])
        if nuevo_estado not in transiciones:
            raise ValueError(
                f"Transición inválida: '{self.estado}' → '{nuevo_estado}'. "
                f"Transiciones permitidas: {transiciones}"
            )
        self.estado = nuevo_estado
        self._registrar_timestamp(nuevo_estado)

    def _registrar_timestamp(self, estado: str) -> None:
        """Registra la fecha/hora en que se alcanzó cada estado clave."""
        ahora = datetime.now()
        if estado == "en_preparacion" and not self.fecha_inicio_prep:
            self.fecha_inicio_prep = ahora
        elif estado == "lista":
            self.fecha_lista = ahora
        elif estado == "entregada":
            self.fecha_entrega = ahora

    def confirmacion_actualizacion_estado(self) -> dict:
        """
        Retorna confirmación del cambio de estado para la vista.
        Corresponde a confirmacionActualizacionEstado() — CU38/CU42/CU44.
        """
        return {
            "orden_id": self.id,
            "codigo": self.codigo_orden,
            "estado_nuevo": self.estado,
            "timestamp": datetime.now().isoformat(),
        }

    # ── CU42: deshacer (revertir a en_preparacion) ───────────────────

    def revertir_a_en_preparacion(self) -> None:
        """
        Permite deshacer el marcado como lista durante 5 segundos.
        Corresponde a revertirEstado('EnPreparacion') — CU42.
        """
        if self.estado != "lista":
            raise ValueError("Solo se puede revertir una orden en estado 'lista'.")
        self.estado = "en_preparacion"
        self.fecha_lista = None

    # ── CU43: datos para notificación ────────────────────────────────

    def obtener_datos_notificacion(self) -> dict:
        """
        Retorna los datos necesarios para enviar la notificación push.
        Corresponde a datosOrden — CU43.
        """
        return {
            "orden_id": self.id,
            "codigo_orden": self.codigo_orden,
            "nombre_cliente": self.nombre_cliente,
            "estado": self.estado,
            "items": len(self.items),
        }

    # ── CU47: registrar tiempo de preparación ─────────────────────────

    def registrar_tiempo_preparacion(self, umbral_seg: int = 600) -> int:
        """
        Calcula y registra el tiempo de preparación.
        Corresponde a registrarTiempoPreparacion() — CU47.
        Actualiza también entregada_a_tiempo para métricas M03.

        Returns:
            Tiempo de preparación en segundos.
        """
        if not self.fecha_inicio_prep or not self.fecha_lista:
            raise ValueError(
                "La orden debe tener fecha_inicio_prep y fecha_lista para calcular el tiempo."
            )
        delta = (self.fecha_lista - self.fecha_inicio_prep).total_seconds()
        self.tiempo_preparacion_seg = int(delta)
        self.entregada_a_tiempo = self.tiempo_preparacion_seg <= umbral_seg
        return self.tiempo_preparacion_seg

    # ── CU45: reportar problema ───────────────────────────────────────

    def reportar_problema(self, descripcion: str) -> None:
        """
        Registra un problema con la orden y cambia el estado.
        Corresponde a reportarProblema() — CU45.
        """
        self.reporte_problema = descripcion
        self.cambiar_estado("con_problema")

    # ── CU40: notas especiales ────────────────────────────────────────

    def tiene_notas_especiales(self) -> bool:
        """True si la orden o algún ítem tiene notas especiales. CU40."""
        if self.notas_generales:
            return True
        return any(item.notas_item for item in self.items)

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "codigo_orden": self.codigo_orden,
            "estado": self.estado,
            "nombre_cliente": self.nombre_cliente,
            "notas_generales": self.notas_generales,
            "tiene_notas": self.tiene_notas_especiales(),
            "total": self.total,
            "items": [i.to_dict() for i in self.items],
            "empleado_asignado_id": self.empleado_asignado_id,
            "tiempo_preparacion_seg": self.tiempo_preparacion_seg,
            "entregada_a_tiempo": self.entregada_a_tiempo,
            "fecha_creacion": self.fecha_creacion.isoformat(),
            "fecha_inicio_prep": self.fecha_inicio_prep.isoformat() if self.fecha_inicio_prep else None,
            "fecha_lista": self.fecha_lista.isoformat() if self.fecha_lista else None,
            "fecha_entrega": self.fecha_entrega.isoformat() if self.fecha_entrega else None,
            "reporte_problema": self.reporte_problema,
        }

    @classmethod
    def from_db_row(cls, row: dict, items: Optional[List[OrderItem]] = None) -> "Order":
        """Construye una Order desde un asyncpg Record."""
        def parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(str(val))

        return cls(
            id=str(row["id"]),
            codigo_orden=row.get("codigo_orden", ""),
            estado=row.get("estado", "pendiente"),
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