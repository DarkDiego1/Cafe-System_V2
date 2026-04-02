"""
entities/purchase_order.py
Módulo 03 — Gestión y Administración (MAM)

Entidad de dominio: PurchaseOrder + PurchaseOrderItem
Casos de uso: CU55, CU53
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .supplier import Supplier
    from .ingredient import Ingredient


@dataclass
class PurchaseOrderItem:
    """
    Línea individual dentro de una PurchaseOrder.
    Mapea contra `purchase_order_items`.
    """

    ingrediente_id: int
    nombre_ingrediente: str
    cantidad: float
    unidad_medida: str
    costo_unitario: float = 0.0

    @property
    def subtotal(self) -> float:
        return round(self.cantidad * self.costo_unitario, 2)

    def to_dict(self) -> dict:
        return {
            "ingrediente_id": self.ingrediente_id,
            "nombre_ingrediente": self.nombre_ingrediente,
            "cantidad": self.cantidad,
            "unidad_medida": self.unidad_medida,
            "costo_unitario": self.costo_unitario,
            "subtotal": self.subtotal,
        }


@dataclass
class PurchaseOrder:
    """
    Orden de compra hacia un proveedor.
    Mapea contra `purchase_orders` + `purchase_order_items`.
    """

    id: int
    proveedor_id: int
    estado: str = "borrador"          # borrador | enviada | recibida | cancelada
    items: List[PurchaseOrderItem] = field(default_factory=list)
    notas: Optional[str] = None
    fecha_creacion: datetime = field(default_factory=datetime.now)
    fecha_envio: Optional[datetime] = None
    fecha_recepcion: Optional[datetime] = None
    # Datos enriquecidos (join con suppliers)
    proveedor_nombre: str = ""
    proveedor_activo: bool = True

    # ── CU55: generarBorradorPedidoCompra ─────────────────────────────

    @classmethod
    def generar_borrador_pedido_compra(
        cls,
        id: int,
        proveedor_id: int,
        proveedor_nombre: str,
        items: List[PurchaseOrderItem],
        notas: Optional[str] = None,
    ) -> "PurchaseOrder":
        """
        Factory method — crea un borrador de orden de compra.
        Corresponde a generarBorradorPedidoCompra() del diagrama CU55.
        """
        return cls(
            id=id,
            proveedor_id=proveedor_id,
            proveedor_nombre=proveedor_nombre,
            items=items,
            estado="borrador",
            notas=notas,
        )

    def mostrar_lista_sugerida(self) -> List[dict]:
        """
        Retorna los ítems en formato legible para la vista.
        Corresponde a mostrarListaSugerida() del diagrama CU55.
        """
        return [item.to_dict() for item in self.items]

    def solicitar_proveedor_alterno(self, nuevo_proveedor_id: int, nuevo_nombre: str) -> None:
        """
        Reasigna la orden a un proveedor alternativo cuando el original está inactivo.
        Corresponde a solicitarProveedorAlterno() del diagrama CU55.
        """
        self.proveedor_id = nuevo_proveedor_id
        self.proveedor_nombre = nuevo_nombre
        nota_extra = f"Proveedor reasignado el {datetime.now().strftime('%Y-%m-%d %H:%M')}."
        self.notas = f"{self.notas} | {nota_extra}" if self.notas else nota_extra

    # ── CU53: confirmación de recepción ───────────────────────────────

    def confirmar_recepcion(self) -> None:
        """Marca la orden como recibida tras confirmar entrega física."""
        if self.estado not in ("enviada",):
            raise ValueError("Solo se puede confirmar una orden en estado 'enviada'.")
        self.estado = "recibida"
        self.fecha_recepcion = datetime.now()

    def enviar(self) -> None:
        """Cambia el estado a 'enviada' y registra la fecha de envío."""
        if self.estado != "borrador":
            raise ValueError("Solo se pueden enviar órdenes en estado 'borrador'.")
        self.estado = "enviada"
        self.fecha_envio = datetime.now()

    def cancelar(self) -> None:
        """Cancela la orden si aún no fue recibida."""
        if self.estado == "recibida":
            raise ValueError("No se puede cancelar una orden ya recibida.")
        self.estado = "cancelada"

    # ── Cálculos ──────────────────────────────────────────────────────

    @property
    def total_estimado(self) -> float:
        return round(sum(i.subtotal for i in self.items), 2)

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "proveedor_id": self.proveedor_id,
            "proveedor": self.proveedor_nombre,
            "estado": self.estado,
            "items": [i.to_dict() for i in self.items],
            "total_estimado": self.total_estimado,
            "notas": self.notas,
            "fecha_creacion": self.fecha_creacion.isoformat(),
            "fecha_envio": self.fecha_envio.isoformat() if self.fecha_envio else None,
            "fecha_recepcion": self.fecha_recepcion.isoformat() if self.fecha_recepcion else None,
        }

    @classmethod
    def from_db_row(cls, row: dict, items: Optional[List[PurchaseOrderItem]] = None) -> "PurchaseOrder":
        """Construye una PurchaseOrder desde un asyncpg Record."""
        return cls(
            id=row["id"],
            proveedor_id=row["proveedor_id"],
            proveedor_nombre=row.get("proveedor", ""),
            proveedor_activo=row.get("proveedor_activo", True),
            estado=row.get("estado", "borrador"),
            notas=row.get("notas"),
            fecha_creacion=row.get("fecha_creacion") or datetime.now(),
            fecha_envio=row.get("fecha_envio"),
            fecha_recepcion=row.get("fecha_recepcion"),
            items=items or [],
        )