"""
services/knowledge_base.py
Módulo 02 — Producción y Operaciones (POM)

Servicio: KnowledgeBase
Casos de uso: CU39 — Consultar receta detallada
              CU41 — Solicitar ficha técnica de ingrediente

Provee al barista fichas técnicas, recetas, proporciones y advertencias
de alérgenos directamente desde la base de datos.
"""

from typing import Optional
import database


class KnowledgeBase:
    """
    Base de conocimiento de recetas y fichas técnicas de ingredientes.

    Atributos conceptuales del diagrama:
        fichaTecnica: Object — retornado por consultarFichaTecnica()
    """

    # ══════════════════════════════════════════════════════
    # CU39 — Consultar receta detallada
    # ══════════════════════════════════════════════════════

    async def consultar_receta(self, bebida_id: int) -> dict:
        """
        Retorna la receta completa de una bebida con proporciones
        y método de preparación.
        Corresponde a consultarFichaTecnica() — CU39.
        """
        db = await database.get_db()

        bebida = await db.fetchrow("""
            SELECT
                d.id, d.nombre, d.descripcion, d.imagen_url,
                d.precio_chico, d.precio_mediano, d.precio_grande,
                c.nombre AS categoria
            FROM drinks d
            JOIN categories c ON c.id = d.categoria_id
            WHERE d.id = $1 AND d.activo = TRUE
        """, bebida_id)

        if not bebida:
            raise KeyError(f"Bebida {bebida_id} no encontrada.")

        ingredientes = await db.fetch("""
            SELECT
                i.id, i.nombre, i.unidad_medida,
                i.descripcion, i.imagen_url,
                di.cantidad_base, di.cantidad_minima,
                di.cantidad_maxima, di.es_opcional
            FROM drink_ingredients di
            JOIN ingredients i ON i.id = di.ingrediente_id
            WHERE di.bebida_id = $1 AND i.disponible = TRUE
            ORDER BY di.es_opcional, i.nombre
        """, bebida_id)

        return {
            "bebida": dict(bebida),
            "ingredientes": [dict(r) for r in ingredientes],
            "total_ingredientes": len(ingredientes),
            "tiene_opcionales": any(r["es_opcional"] for r in ingredientes),
        }

    # ══════════════════════════════════════════════════════
    # CU41 — Consultar ficha técnica de ingrediente
    # ══════════════════════════════════════════════════════

    async def consultar_ficha_tecnica(self, ingrediente_id: int) -> dict:
        """
        Retorna la ficha técnica completa de un ingrediente:
        proporciones, método de uso y advertencias.
        Corresponde a consultarFichaTecnica() — CU41.
        """
        db = await database.get_db()

        ing = await db.fetchrow("""
            SELECT
                i.id, i.nombre, i.categoria,
                i.unidad_medida, i.descripcion,
                i.imagen_url, i.stock_actual,
                i.stock_minimo, i.costo_unitario,
                i.disponible
            FROM ingredients i
            WHERE i.id = $1 AND i.activo = TRUE
        """, ingrediente_id)

        if not ing:
            raise KeyError(f"Ingrediente {ingrediente_id} no encontrado.")

        # Bebidas que usan este ingrediente (para contexto del barista)
        bebidas = await db.fetch("""
            SELECT
                d.nombre AS bebida,
                di.cantidad_base,
                di.cantidad_minima,
                di.cantidad_maxima,
                di.es_opcional
            FROM drink_ingredients di
            JOIN drinks d ON d.id = di.bebida_id
            WHERE di.ingrediente_id = $1 AND d.activo = TRUE
            ORDER BY d.nombre
        """, ingrediente_id)

        ficha = dict(ing)
        ficha["usado_en_bebidas"] = [dict(r) for r in bebidas]
        ficha["advertencias"] = self._generar_advertencias(ficha)
        ficha["tiene_imagen"] = bool(ing.get("imagen_url"))

        return ficha

    def _generar_advertencias(self, ing: dict) -> list[str]:
        """
        Genera advertencias automáticas según el estado del ingrediente.
        Corresponde a detectarFaltaImagenes() y advertencias — CU41.
        """
        advertencias = []
        if not ing.get("imagen_url"):
            advertencias.append("⚠ Sin imagen de referencia disponible.")
        if not ing.get("disponible"):
            advertencias.append("🚫 Ingrediente marcado como no disponible.")
        if ing.get("stock_actual", 0) < ing.get("stock_minimo", 0):
            advertencias.append(
                f"⚠ Stock bajo: {ing.get('stock_actual', 0)} "
                f"{ing.get('unidad_medida', '')} disponibles."
            )
        return advertencias

    def detectar_falta_imagenes(self, ficha: dict) -> bool:
        """
        Verifica si el ingrediente no tiene imagen de referencia.
        Corresponde a detectarFaltaImagenes() — CU41.
        """
        return not ficha.get("tiene_imagen", False)

    # ══════════════════════════════════════════════════════
    # CU39 — Recetas por orden (todas las bebidas de una orden)
    # ══════════════════════════════════════════════════════

    async def obtener_recetas_orden(self, orden_id: str) -> list[dict]:
        """
        Retorna las recetas de todas las bebidas en una orden.
        Útil para que el barista vea todo lo que necesita preparar.
        """
        db = await database.get_db()

        bebidas = await db.fetch("""
            SELECT DISTINCT oi.bebida_id
            FROM order_items oi
            WHERE oi.orden_id = $1::uuid
        """, orden_id)

        recetas = []
        for b in bebidas:
            try:
                receta = await self.consultar_receta(b["bebida_id"])
                recetas.append(receta)
            except KeyError:
                pass
        return recetas