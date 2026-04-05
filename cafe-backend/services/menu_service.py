"""
services/menu_service.py
Módulo 01 — Experiencia del Cliente (CEM)

Servicios: MenuService, DrinkService
Casos de uso: CU01, CU02, CU03, CU04, CU11, CU20
"""

from typing import Optional
import database


class MenuService:
    """
    Provee categorías y listados de bebidas al cliente.
    Corresponde a MenuService del diagrama — CU01.
    """

    async def obtener_categorias(self) -> list[dict]:
        """
        Retorna las categorías activas ordenadas para visualización.
        Corresponde a obtenerCategorias() — CU01.
        """
        db = await database.get_db()
        rows = await db.fetch("""
            SELECT id, nombre, descripcion, imagen_url
            FROM categories
            WHERE activa = TRUE
            ORDER BY orden_visualizacion
        """)
        return [dict(r) for r in rows]

    async def obtener_bebidas_por_categoria(
        self,
        categoria_id: int,
        filtros: Optional[dict] = None,
    ) -> list[dict]:
        """
        Retorna las bebidas de una categoría.
        Corresponde a obtenerBebidasPorCategoria() — CU01.
        Soporta filtros de preferencias alimenticias (CU66).
        """
        db = await database.get_db()

        query = """
            SELECT
                d.id, d.nombre, d.descripcion, d.imagen_url,
                d.precio_chico, d.precio_mediano, d.precio_grande,
                d.disponible
            FROM drinks d
            WHERE d.categoria_id = $1
              AND d.activo = TRUE
        """
        params = [categoria_id]

        # CU66: filtro de preferencias alimenticias
        if filtros and filtros.get("vegetariano"):
            query += " AND d.es_vegetariana = TRUE"
        if filtros and filtros.get("sin_lactosa"):
            query += " AND d.sin_lactosa = TRUE"
        if filtros and filtros.get("sin_cafeina"):
            query += " AND d.sin_cafeina = TRUE"

        query += " ORDER BY d.nombre"
        rows = await db.fetch(query, *params)
        return [dict(r) for r in rows]

    async def obtener_menu_completo(self) -> list[dict]:
        """
        Retorna todas las categorías con sus bebidas.
        Corresponde a CU20 — Explorar menú completo en app.
        """
        categorias = await self.obtener_categorias()
        for cat in categorias:
            cat["bebidas"] = await self.obtener_bebidas_por_categoria(cat["id"])
        return categorias


class DrinkService:
    """
    Provee detalles e ingredientes de bebidas individuales.
    Corresponde a DrinkService del diagrama — CU02, CU03, CU04.
    """

    async def obtener_ingredientes(self, bebida_id: int) -> list[dict]:
        """
        Retorna los ingredientes de una bebida con cantidades.
        Corresponde a obtenerIngredientes() — CU02.
        """
        db = await database.get_db()
        rows = await db.fetch("""
            SELECT
                i.id, i.nombre, i.unidad_medida,
                i.descripcion, i.imagen_url, i.disponible,
                di.cantidad_base, di.cantidad_minima,
                di.cantidad_maxima, di.es_opcional
            FROM drink_ingredients di
            JOIN ingredients i ON i.id = di.ingrediente_id
            WHERE di.bebida_id = $1 AND i.disponible = TRUE
            ORDER BY di.es_opcional, i.nombre
        """, bebida_id)
        return [dict(r) for r in rows]

    async def obtener_bebida_detalle(self, bebida_id: int) -> dict:
        """
        Retorna todos los datos de una bebida incluyendo ingredientes.
        Corresponde a seleccionarBebida() → mostrarGaleriaIngredientes() — CU02.
        """
        db = await database.get_db()
        row = await db.fetchrow("""
            SELECT d.*, c.nombre AS categoria
            FROM drinks d
            JOIN categories c ON c.id = d.categoria_id
            WHERE d.id = $1 AND d.activo = TRUE
        """, bebida_id)

        if not row:
            raise KeyError(f"Bebida {bebida_id} no encontrada.")

        resultado = dict(row)
        resultado["ingredientes"] = await self.obtener_ingredientes(bebida_id)
        resultado["disponible_completa"] = all(
            i["disponible"] for i in resultado["ingredientes"]
            if not i["es_opcional"]
        )
        return resultado

    async def verificar_disponibilidad(self, bebida_id: int) -> dict:
        """
        Verifica si todos los ingredientes requeridos están disponibles.
        Corresponde a CU11 — Notificación ingrediente no disponible.
        """
        ingredientes = await self.obtener_ingredientes(bebida_id)
        faltantes = [
            i["nombre"] for i in ingredientes
            if not i["disponible"] and not i["es_opcional"]
        ]
        return {
            "disponible": len(faltantes) == 0,
            "ingredientes_faltantes": faltantes,
        }

    async def calcular_precio_base(self, bebida_id: int, tamano: str) -> float:
        """
        Retorna el precio según el tamaño seleccionado.
        Corresponde a actualizarPrecioBase(size) — CU03.
        """
        db = await database.get_db()
        columna = {
            "chico": "precio_chico",
            "mediano": "precio_mediano",
            "grande": "precio_grande",
        }.get(tamano.lower())

        if not columna:
            raise ValueError(f"Tamaño '{tamano}' no válido. Opciones: chico, mediano, grande.")

        precio = await db.fetchval(
            f"SELECT {columna} FROM drinks WHERE id = $1 AND activo = TRUE",
            bebida_id,
        )
        if precio is None:
            raise KeyError(f"Bebida {bebida_id} no encontrada.")
        return float(precio)