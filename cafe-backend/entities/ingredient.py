"""
entities/ingredient.py
Módulo 03 — Gestión y Administración (MAM)

Entidad de dominio: Ingredient
Casos de uso: CU48, CU49, CU50, CU51, CU52, CU53, CU55, CU57
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Ingredient:
    """
    Representa un ingrediente del catálogo del inventario.

    Mapea directamente contra la tabla `ingredients` de PostgreSQL.
    Los métodos de negocio implementan la lógica del diagrama de secuencia
    sin acceder a la base de datos — eso es responsabilidad de InventoryService.
    """

    id: int
    nombre: str
    categoria: str
    unidad_medida: str
    stock_actual: float
    stock_minimo: float
    stock_optimo: float
    costo_unitario: float
    disponible: bool = True
    activo: bool = True
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    ultima_actualizacion: datetime = field(default_factory=datetime.now)

    # ── CU57: crearIngrediente / validarDuplicado ─────────────────────

    @classmethod
    def crear_ingrediente(
        cls,
        id: int,
        nombre: str,
        categoria: str,
        unidad_medida: str,
        stock_minimo: float,
        stock_optimo: float,
        costo_unitario: float = 0.0,
        descripcion: Optional[str] = None,
        imagen_url: Optional[str] = None,
    ) -> "Ingredient":
        """
        Factory method — equivale a crearIngrediente() del diagrama.
        El stock inicial es siempre 0.0; se actualiza vía CU53.
        """
        return cls(
            id=id,
            nombre=nombre,
            categoria=categoria,
            unidad_medida=unidad_medida,
            stock_actual=0.0,
            stock_minimo=stock_minimo,
            stock_optimo=stock_optimo,
            costo_unitario=costo_unitario,
            descripcion=descripcion,
            imagen_url=imagen_url,
        )

    def validar_duplicado(self, nombre_candidato: str) -> bool:
        """
        Retorna True si el nombre candidato coincide con este ingrediente.
        Llamado por InventoryController.validar_duplicado() — CU57.
        """
        return self.nombre.strip().lower() == nombre_candidato.strip().lower()

    # ── CU51: alerta de stock bajo ────────────────────────────────────

    def esta_bajo_minimo(self) -> bool:
        """True cuando stock_actual < stock_minimo. Dispara CU51."""
        return self.stock_actual < self.stock_minimo

    def nivel_porcentaje(self) -> float:
        """Porcentaje relativo de stock: (actual / minimo) * 100."""
        if self.stock_minimo <= 0:
            return 100.0
        return round((self.stock_actual / self.stock_minimo) * 100, 1)

    # ── CU55: calcularCantidadHastaStockOptimo ────────────────────────

    def calcular_cantidad_hasta_stock_optimo(self) -> float:
        """
        Unidades a pedir para alcanzar el stock óptimo.
        Retorna 0 si ya está por encima del óptimo.
        """
        return max(0.0, self.stock_optimo - self.stock_actual)

    # ── CU52: actualizar manualmente ──────────────────────────────────

    def aplicar_actualizacion_manual(self, nuevo_valor: float) -> None:
        """
        Sobrescribe stock_actual con el valor exacto ingresado.
        Corresponde a Confirmar_actualizacion() en el diagrama CU52.

        Raises:
            ValueError: Si el valor es negativo.
        """
        if nuevo_valor < 0:
            raise ValueError("El stock no puede ser un valor negativo.")
        self.stock_actual = nuevo_valor
        self.ultima_actualizacion = datetime.now()

    # ── CU53: entrada de mercancía ────────────────────────────────────

    def registrar_entrada(self, cantidad: float) -> None:
        """Incrementa el stock al recibir mercancía del proveedor."""
        if cantidad <= 0:
            raise ValueError("La cantidad de entrada debe ser positiva.")
        self.stock_actual += cantidad
        self.ultima_actualizacion = datetime.now()

    # ── CU56: merma ───────────────────────────────────────────────────

    def validar_cantidad_menor_igual_stock(self, cantidad: float) -> bool:
        """
        Verifica que la cantidad a descontar no supere el stock disponible.
        Llamado por InventoryController.validar_cantidad_menor_igual_stock().
        """
        return cantidad <= self.stock_actual

    def descontar_stock(self, cantidad: float) -> None:
        """
        Descuenta cantidad del stock (merma o consumo).
        Raises ValueError si la cantidad supera el stock.
        """
        if not self.validar_cantidad_menor_igual_stock(cantidad):
            raise ValueError(
                f"La cantidad ({cantidad} {self.unidad_medida}) supera el "
                f"stock disponible ({self.stock_actual} {self.unidad_medida})."
            )
        self.stock_actual -= cantidad
        self.ultima_actualizacion = datetime.now()

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "unidad_medida": self.unidad_medida,
            "stock_actual": self.stock_actual,
            "stock_minimo": self.stock_minimo,
            "stock_optimo": self.stock_optimo,
            "costo_unitario": self.costo_unitario,
            "disponible": self.disponible,
            "descripcion": self.descripcion,
            "imagen_url": self.imagen_url,
            "alerta_stock": self.esta_bajo_minimo(),
            "nivel_pct": self.nivel_porcentaje(),
            "ultima_actualizacion": self.ultima_actualizacion.isoformat(),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Ingredient":
        """Construye un Ingredient desde un asyncpg Record."""
        return cls(
            id=row["id"],
            nombre=row["nombre"],
            categoria=row.get("categoria", ""),
            unidad_medida=row["unidad_medida"],
            stock_actual=float(row.get("stock_actual", 0)),
            stock_minimo=float(row.get("stock_minimo", 0)),
            stock_optimo=float(row.get("stock_optimo", 0)),
            costo_unitario=float(row.get("costo_unitario", 0)),
            disponible=row.get("disponible", True),
            activo=row.get("activo", True),
            descripcion=row.get("descripcion"),
            imagen_url=row.get("imagen_url"),
            ultima_actualizacion=row.get("ultima_actualizacion") or datetime.now(),
        )