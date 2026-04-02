"""
schemas/inventory_schemas.py
Módulo 03 — Gestión y Administración (MAM)

Schemas Pydantic para validación de request/response en FastAPI.
Cubren: Ingredient, Supplier, PurchaseOrder, WasteLog, Reports
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ══════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════

class EstadoOrdenCompra(str, Enum):
    borrador  = "borrador"
    enviada   = "enviada"
    recibida  = "recibida"
    cancelada = "cancelada"


# ══════════════════════════════════════════════════════════
# INGREDIENT — CU48, CU49, CU52, CU53, CU56
# ══════════════════════════════════════════════════════════

class IngredientCreateSchema(BaseModel):
    """CU48 — Registrar nuevo ingrediente"""
    nombre:         str   = Field(..., min_length=2, max_length=100)
    categoria:      str   = Field(..., max_length=60)
    unidad_medida:  str   = Field(..., max_length=20)
    stock_minimo:   float = Field(..., ge=0)
    stock_optimo:   float = Field(..., ge=0)
    costo_unitario: float = Field(default=0.0, ge=0)
    descripcion:    Optional[str] = None
    imagen_url:     Optional[str] = None


class IngredientUpdateSchema(BaseModel):
    """CU49 — Modificar información de ingrediente"""
    nombre:         Optional[str]   = Field(None, min_length=2, max_length=100)
    categoria:      Optional[str]   = Field(None, max_length=60)
    unidad_medida:  Optional[str]   = Field(None, max_length=20)
    stock_minimo:   Optional[float] = Field(None, ge=0)
    stock_optimo:   Optional[float] = Field(None, ge=0)
    costo_unitario: Optional[float] = Field(None, ge=0)
    descripcion:    Optional[str]   = None
    imagen_url:     Optional[str]   = None
    disponible:     Optional[bool]  = None


class StockManualUpdateSchema(BaseModel):
    """CU52 — Actualizar inventario manualmente"""
    nuevo_stock: float = Field(..., ge=0, description="Nuevo valor absoluto de stock")
    motivo:      str   = Field(..., min_length=3, max_length=255)


class EntradaMercanciaSchema(BaseModel):
    """CU53 — Registrar entrada de mercancía"""
    cantidad:        float          = Field(..., gt=0)
    orden_compra_id: Optional[int]  = None
    notas:           Optional[str]  = None


class WasteLogCreateSchema(BaseModel):
    """CU56 — Registrar merma / desperdicio"""
    ingrediente_id: int            = Field(..., gt=0)
    cantidad:       float          = Field(..., gt=0)
    motivo:         str            = Field(..., min_length=3, max_length=255)
    registrado_por: Optional[int]  = None   # employee_id


# ══════════════════════════════════════════════════════════
# SUPPLIER — CU57
# ══════════════════════════════════════════════════════════

class SupplierCreateSchema(BaseModel):
    """CU57 — Registrar proveedor"""
    nombre:   str           = Field(..., min_length=2, max_length=150)
    contacto: str           = Field(..., max_length=100)
    telefono: str           = Field(..., max_length=20)
    email:    str           = Field(..., max_length=150)
    notas:    Optional[str] = None


class SupplierUpdateSchema(BaseModel):
    """CU57 — Modificar proveedor"""
    nombre:   Optional[str]  = Field(None, min_length=2, max_length=150)
    contacto: Optional[str]  = Field(None, max_length=100)
    telefono: Optional[str]  = Field(None, max_length=20)
    email:    Optional[str]  = Field(None, max_length=150)
    notas:    Optional[str]  = None
    activo:   Optional[bool] = None


# ══════════════════════════════════════════════════════════
# PURCHASE ORDER — CU55, CU53
# ══════════════════════════════════════════════════════════

class PurchaseOrderItemSchema(BaseModel):
    ingrediente_id: int   = Field(..., gt=0)
    cantidad:       float = Field(..., gt=0)


class PurchaseOrderCreateSchema(BaseModel):
    """CU55 — Crear orden de compra"""
    proveedor_id: int                          = Field(..., gt=0)
    items:        List[PurchaseOrderItemSchema]
    notas:        Optional[str]                = None


class EstadoOrdenCompraSchema(BaseModel):
    """Actualizar estado de una orden de compra"""
    estado: EstadoOrdenCompra


# ══════════════════════════════════════════════════════════
# REPORTS — CU54, CU60, CU61, CU62
# ══════════════════════════════════════════════════════════

class ReportParamsSchema(BaseModel):
    """Parámetros comunes para generación de reportes"""
    fecha_inicio: datetime
    fecha_fin:    datetime