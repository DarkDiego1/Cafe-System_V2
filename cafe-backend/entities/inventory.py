"""
entities/inventory.py
Módulo 03 — Gestión y Administración (MAM)

Entidad de dominio: Inventory
Casos de uso: CU50, CU51, CU52, CU55, CU56

Inventory actúa como agregado raíz que orquesta operaciones
sobre la colección de ingredientes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

from .ingredient import Ingredient
from .supplier import Supplier
from .purchase_order import PurchaseOrder, PurchaseOrderItem


@dataclass
class Inventory:
    """
    Agregado de inventario: mantiene la colección de ingredientes
    y orquesta las operaciones de stock.

    En producción este objeto se hidrata desde PostgreSQL a través
    de InventoryService; no guarda estado persistente propio.
    """

    ingredientes: Dict[int, Ingredient] = field(default_factory=dict)
    ultima_actualizacion: datetime = field(default_factory=datetime.now)
    alertas_activas: List[int] = field(default_factory=list)  # ingredient_ids

    # ── Propiedades calculadas ────────────────────────────────────────

    @property
    def stock_total(self) -> float:
        return sum(i.stock_actual for i in self.ingredientes.values())

    @property
    def costo_total(self) -> float:
        return round(
            sum(i.stock_actual * i.costo_unitario for i in self.ingredientes.values()), 2
        )

    # ── CU50/CU51: consultar niveles y alertas ────────────────────────

    def verificar_alertas_stock(self) -> List[int]:
        """
        Recorre los ingredientes y actualiza alertas_activas.
        Corresponde al flujo CU51 — Recibir alerta de stock bajo.

        Returns:
            Lista de IDs de ingredientes bajo el stock mínimo.
        """
        self.alertas_activas = [
            ing_id
            for ing_id, ing in self.ingredientes.items()
            if ing.esta_bajo_minimo()
        ]
        self.ultima_actualizacion = datetime.now()
        return self.alertas_activas

    def obtener_niveles_inventario(self) -> List[dict]:
        """
        Retorna estado de todos los ingredientes ordenados por nivel relativo.
        Corresponde al flujo CU50 — Consultar niveles de inventario.
        """
        niveles = [ing.to_dict() for ing in self.ingredientes.values()]
        return sorted(niveles, key=lambda x: x["nivel_pct"])

    # ── CU56: validar y descontar ─────────────────────────────────────

    def validar_cantidad_menor_igual_stock(
        self, ingrediente_id: int, cantidad: float
    ) -> bool:
        """
        Verifica que la cantidad a descontar no supere el stock disponible.
        Corresponde a validarCantidadMenorIgualStock() del diagrama CU56.
        """
        ing = self.ingredientes.get(ingrediente_id)
        if ing is None:
            return False
        return ing.validar_cantidad_menor_igual_stock(cantidad)

    def descontar_inventario(self, ingrediente_id: int, cantidad: float) -> None:
        """
        Descuenta stock del ingrediente indicado.
        Corresponde a descontarInventario() del diagrama CU56.

        Raises:
            KeyError: Si el ingrediente no existe.
            ValueError: Si la cantidad supera el stock.
        """
        ing = self.ingredientes.get(ingrediente_id)
        if ing is None:
            raise KeyError(f"Ingrediente {ingrediente_id} no encontrado en inventario.")
        ing.descontar_stock(cantidad)
        self.verificar_alertas_stock()

    # ── CU55: lista de compras automatizada ───────────────────────────

    def identificar_ingredientes_bajo_minimo(self) -> List[Ingredient]:
        """
        Retorna ingredientes que necesitan reabastecimiento.
        Corresponde a identificarIngredientesBajoMinimo() — diagrama CU55.
        """
        return [ing for ing in self.ingredientes.values() if ing.esta_bajo_minimo()]

    def agrupar_por_proveedor(
        self,
        ingredientes: List[Ingredient],
        mapa_proveedor: Dict[int, Supplier],
    ) -> Dict[Optional[Supplier], List[Ingredient]]:
        """
        Agrupa los ingredientes a reabastecer por su proveedor principal.
        Corresponde a agruparPorProveedor() — diagrama CU55.

        Args:
            ingredientes: Lista de ingredientes bajo mínimo.
            mapa_proveedor: {ingrediente_id: Supplier}

        Returns:
            Diccionario {Supplier | None: [Ingredient]}
            None como clave indica ingredientes sin proveedor asignado.
        """
        grupos: Dict[Optional[Supplier], List[Ingredient]] = {}
        for ing in ingredientes:
            proveedor = mapa_proveedor.get(ing.id)
            grupos.setdefault(proveedor, []).append(ing)
        return grupos

    def calcular_cantidad_hasta_stock_optimo(self, ingrediente_id: int) -> float:
        """
        Delega en el ingrediente el cálculo de unidades a pedir.
        Corresponde a calcularCantidadHastaStockOptimo() — diagrama CU55.
        """
        ing = self.ingredientes.get(ingrediente_id)
        if ing is None:
            return 0.0
        return ing.calcular_cantidad_hasta_stock_optimo()

    def generar_borrador_pedido_compra(
        self,
        orden_id: int,
        proveedor: Supplier,
        ingredientes: List[Ingredient],
    ) -> PurchaseOrder:
        """
        Crea un borrador de PurchaseOrder para el proveedor dado.
        Corresponde a generarBorradorPedidoCompra() — diagrama CU55.
        """
        items = [
            PurchaseOrderItem(
                ingrediente_id=ing.id,
                nombre_ingrediente=ing.nombre,
                cantidad=ing.calcular_cantidad_hasta_stock_optimo(),
                unidad_medida=ing.unidad_medida,
                costo_unitario=ing.costo_unitario,
            )
            for ing in ingredientes
            if ing.calcular_cantidad_hasta_stock_optimo() > 0
        ]
        return PurchaseOrder.generar_borrador_pedido_compra(
            id=orden_id,
            proveedor_id=proveedor.id,
            proveedor_nombre=proveedor.nombre,
            items=items,
        )

    # ── Gestión de ingredientes ───────────────────────────────────────

    def agregar_ingrediente(self, ingrediente: Ingredient) -> None:
        self.ingredientes[ingrediente.id] = ingrediente
        self.ultima_actualizacion = datetime.now()

    def obtener_ingrediente(self, ingrediente_id: int) -> Optional[Ingredient]:
        return self.ingredientes.get(ingrediente_id)

    def to_dict(self) -> dict:
        return {
            "ultima_actualizacion": self.ultima_actualizacion.isoformat(),
            "total_ingredientes": len(self.ingredientes),
            "stock_total": self.stock_total,
            "costo_total": self.costo_total,
            "alertas_activas": self.alertas_activas,
        }