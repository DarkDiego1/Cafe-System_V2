"""
controllers/inventory_controller.py
Módulo 03 — Gestión y Administración (MAM)

Controlador: InventoryController
Casos de uso: CU48, CU49, CU50, CU51, CU52, CU53, CU55, CU56, CU57

Recibe peticiones de los routers FastAPI, aplica validaciones
de negocio y delega la persistencia en InventoryService.
"""

from typing import Optional
from fastapi import HTTPException

from services.inventory_service import InventoryService
from entities.ingredient import Ingredient
from entities.waste_log import WasteLog


class InventoryController:
    """
    Intermediario entre los routers de FastAPI y InventoryService.

    Cada método corresponde a una acción del diagrama de secuencia;
    traduce excepciones de dominio a HTTPException con el código correcto.
    """

    def __init__(self) -> None:
        self._service = InventoryService()

    # ── CU48/CU57: crearIngrediente ───────────────────────────────────

    async def crear_ingrediente(
        self,
        nombre: str,
        categoria: str,
        unidad_medida: str,
        stock_minimo: float,
        stock_optimo: float,
        costo_unitario: float = 0.0,
        descripcion: Optional[str] = None,
        imagen_url: Optional[str] = None,
    ) -> dict:
        """
        Crea un nuevo ingrediente tras validar duplicado.
        Corresponde a crearIngrediente() + validarDuplicado() — CU57.
        """
        try:
            ingrediente = await self._service.registrar_ingrediente(
                nombre=nombre,
                categoria=categoria,
                unidad_medida=unidad_medida,
                stock_minimo=stock_minimo,
                stock_optimo=stock_optimo,
                costo_unitario=costo_unitario,
                descripcion=descripcion,
                imagen_url=imagen_url,
            )
            return ingrediente.to_dict()
        except ValueError as e:
            # mostrarError() — duplicado
            raise HTTPException(status_code=409, detail=str(e))

    # ── CU49: modificar ingrediente ───────────────────────────────────

    async def modificar_ingrediente(
        self, ingrediente_id: int, campos: dict
    ) -> dict:
        try:
            ingrediente = await self._service.modificar_ingrediente(ingrediente_id, campos)
            return ingrediente.to_dict()
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU50: consultar niveles ───────────────────────────────────────

    async def consultar_niveles_inventario(
        self, solo_alertas: bool = False
    ) -> list[dict]:
        """
        Retorna niveles de inventario para que InventoryScreen los muestre.
        """
        return await self._service.obtener_niveles_inventario(solo_alertas)

    # ── CU51: alertas de stock bajo ───────────────────────────────────

    async def obtener_alertas(self) -> dict:
        return await self._service.obtener_alertas_stock()

    # ── CU52: actualizar manualmente ──────────────────────────────────

    async def actualizar_stock_manual(
        self, ingrediente_id: int, nuevo_stock: float, motivo: str
    ) -> dict:
        """
        Corresponde a:
          InventoryScreen.confirmarRegistro()
          → InventoryController.validarCantidadMenorIgualStock()
          → InventoryController.descontarInventario()
        """
        if nuevo_stock < 0:
            # Validar_datos_ingresados() — CU52
            raise HTTPException(
                status_code=422,
                detail="El stock no puede ser un valor negativo."
            )
        try:
            return await self._service.actualizar_stock_manual(
                ingrediente_id, nuevo_stock, motivo
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # ── CU53: entrada de mercancía ────────────────────────────────────

    async def registrar_entrada_mercancia(
        self,
        ingrediente_id: int,
        cantidad: float,
        orden_compra_id: Optional[int] = None,
        notas: Optional[str] = None,
    ) -> dict:
        if cantidad <= 0:
            raise HTTPException(status_code=422, detail="La cantidad debe ser mayor a cero.")
        try:
            return await self._service.registrar_entrada_mercancia(
                ingrediente_id, cantidad, orden_compra_id, notas
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ── CU55: lista de compras ────────────────────────────────────────

    async def generar_lista_compras(self) -> dict:
        return await self._service.generar_lista_compras_automatizada()

    # ── CU56: merma ───────────────────────────────────────────────────

    async def validar_cantidad_menor_igual_stock(
        self, ingrediente_id: int, cantidad: float
    ) -> bool:
        """
        Verifica antes de descontar. Retorna False si la cantidad
        supera el stock o si el ingrediente no existe.
        Corresponde a validarCantidadMenorIgualStock() — CU56.
        """
        niveles = await self._service.obtener_niveles_inventario()
        for ing_dict in niveles:
            if ing_dict["id"] == ingrediente_id:
                return cantidad <= ing_dict["stock_actual"]
        return False

    async def registrar_perdida_contable(
        self,
        ingrediente_id: int,
        cantidad: float,
        motivo: str,
        registrado_por: Optional[int] = None,
    ) -> dict:
        """
        Orquesta descontarInventario() + registrarPerdidaContable().
        Corresponde al flujo CU56 completo.
        """
        try:
            waste = await self._service.registrar_merma(
                ingrediente_id=ingrediente_id,
                cantidad=cantidad,
                motivo=motivo,
                registrado_por=registrado_por,
            )
            return {
                "mensaje": "Merma registrada correctamente.",
                "waste_log": waste.to_dict(),
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            # errorCantidadMayorStock() — CU56
            raise HTTPException(status_code=422, detail=str(e))