"""
services/inventory_service.py
Módulo 03 — Gestión y Administración (MAM)

Servicio: InventoryService
Casos de uso: CU48, CU49, CU50, CU51, CU52, CU53, CU54, CU55, CU56, CU57

Toda operación de BD usa el pool asyncpg que viene de database.get_db().
"""

from datetime import datetime
from typing import Optional, List

import database
from entities.ingredient import Ingredient
from entities.inventory import Inventory
from entities.supplier import Supplier
from entities.purchase_order import PurchaseOrder, PurchaseOrderItem
from entities.waste_log import WasteLog


class InventoryService:
    """
    Capa de servicio para el inventario.

    Orquesta la lógica de negocio entre entidades y persiste
    los cambios en PostgreSQL mediante asyncpg.
    """

    # ══════════════════════════════════════════════════════
    # CU50 / CU51 — Consultar niveles y alertas
    # ══════════════════════════════════════════════════════

    async def obtener_niveles_inventario(
        self, solo_alertas: bool = False
    ) -> List[dict]:
        """
        Retorna todos los ingredientes con su nivel de stock.
        Si solo_alertas=True filtra únicamente los que están bajo mínimo (CU51).
        """
        db = await database.get_db()

        filtro = "AND i.stock_actual < i.stock_minimo" if solo_alertas else ""
        rows = await db.fetch(f"""
            SELECT
                i.id, i.nombre, i.categoria, i.unidad_medida,
                i.stock_actual, i.stock_minimo, i.stock_optimo,
                i.costo_unitario, i.disponible, i.descripcion,
                i.imagen_url, i.ultima_actualizacion,
                (i.stock_actual < i.stock_minimo) AS alerta_stock,
                ROUND(
                    (i.stock_actual / NULLIF(i.stock_minimo, 0) * 100)::numeric, 1
                ) AS nivel_pct
            FROM ingredients i
            WHERE i.activo = TRUE {filtro}
            ORDER BY (i.stock_actual < i.stock_minimo) DESC, nivel_pct ASC
        """)

        ingredientes = [Ingredient.from_db_row(dict(r)) for r in rows]
        return [ing.to_dict() for ing in ingredientes]

    async def obtener_alertas_stock(self) -> dict:
        """
        Retorna solo los ingredientes bajo umbral mínimo con resumen (CU51).
        """
        ingredientes = await self.obtener_niveles_inventario(solo_alertas=True)
        return {
            "total_alertas": len(ingredientes),
            "ingredientes": ingredientes,
        }

    # ══════════════════════════════════════════════════════
    # CU48 — Registrar nuevo ingrediente
    # ══════════════════════════════════════════════════════

    async def registrar_ingrediente(
        self,
        nombre: str,
        categoria: str,
        unidad_medida: str,
        stock_minimo: float,
        stock_optimo: float,
        costo_unitario: float = 0.0,
        descripcion: Optional[str] = None,
        imagen_url: Optional[str] = None,
    ) -> Ingredient:
        """
        Crea y persiste un nuevo ingrediente.
        Valida duplicado antes de insertar (validarDuplicado — CU57).

        Raises:
            ValueError: Si ya existe un ingrediente con ese nombre.
        """
        db = await database.get_db()

        # validarDuplicado()
        existe = await db.fetchval(
            "SELECT id FROM ingredients WHERE LOWER(nombre) = LOWER($1) AND activo = TRUE",
            nombre,
        )
        if existe:
            raise ValueError(f"Ya existe un ingrediente con el nombre '{nombre}'.")

        row = await db.fetchrow("""
            INSERT INTO ingredients
                (nombre, categoria, unidad_medida, stock_actual, stock_minimo,
                 stock_optimo, costo_unitario, descripcion, imagen_url,
                 disponible, activo, ultima_actualizacion)
            VALUES ($1, $2, $3, 0, $4, $5, $6, $7, $8, TRUE, TRUE, NOW())
            RETURNING *
        """, nombre, categoria, unidad_medida, stock_minimo, stock_optimo,
            costo_unitario, descripcion, imagen_url)

        return Ingredient.from_db_row(dict(row))

    # ══════════════════════════════════════════════════════
    # CU49 — Modificar información de ingrediente
    # ══════════════════════════════════════════════════════

    async def modificar_ingrediente(
        self,
        ingrediente_id: int,
        campos: dict,
    ) -> Ingredient:
        """
        Actualiza los campos enviados del ingrediente.

        Args:
            ingrediente_id: ID del ingrediente.
            campos: Diccionario con los campos a actualizar.

        Raises:
            KeyError: Si el ingrediente no existe.
        """
        db = await database.get_db()

        existe = await db.fetchval(
            "SELECT id FROM ingredients WHERE id = $1 AND activo = TRUE",
            ingrediente_id,
        )
        if not existe:
            raise KeyError(f"Ingrediente {ingrediente_id} no encontrado.")

        set_clauses = ", ".join(
            f"{k} = ${i + 2}" for i, k in enumerate(campos)
        )
        values = list(campos.values())

        row = await db.fetchrow(
            f"""
            UPDATE ingredients
               SET {set_clauses}, ultima_actualizacion = NOW()
             WHERE id = $1
         RETURNING *
            """,
            ingrediente_id, *values,
        )
        return Ingredient.from_db_row(dict(row))

    # ══════════════════════════════════════════════════════
    # CU52 — Actualizar inventario manualmente
    # ══════════════════════════════════════════════════════

    async def actualizar_stock_manual(
        self,
        ingrediente_id: int,
        nuevo_stock: float,
        motivo: str,
    ) -> dict:
        """
        Sobrescribe stock_actual con el valor exacto indicado.
        Registra el ajuste en inventory_adjustments para auditoría.

        Corresponde a:
          InventoryScreen.confirmarRegistro() →
          InventoryController.descontarInventario() →
          InventoryService.calcularConsumoTeoricoVsReal()
        """
        db = await database.get_db()

        ing_row = await db.fetchrow(
            "SELECT id, nombre, stock_actual FROM ingredients WHERE id = $1 AND activo = TRUE",
            ingrediente_id,
        )
        if not ing_row:
            raise KeyError(f"Ingrediente {ingrediente_id} no encontrado.")

        ing = Ingredient.from_db_row(dict(ing_row))
        stock_anterior = ing.stock_actual

        # Aplicar lógica de dominio
        ing.aplicar_actualizacion_manual(nuevo_stock)

        async with db.transaction():
            updated = await db.fetchrow("""
                UPDATE ingredients
                   SET stock_actual = $2, ultima_actualizacion = NOW()
                 WHERE id = $1
             RETURNING id, nombre, stock_actual, stock_minimo, unidad_medida
            """, ingrediente_id, ing.stock_actual)

            await db.execute("""
                INSERT INTO inventory_adjustments
                    (ingrediente_id, stock_anterior, stock_nuevo, motivo, tipo, fecha)
                VALUES ($1, $2, $3, $4, 'ajuste_manual', NOW())
            """, ingrediente_id, stock_anterior, ing.stock_actual, motivo)

        resultado = Ingredient.from_db_row(dict(updated))
        return {
            "mensaje": "Stock actualizado correctamente.",
            "ingrediente": resultado.to_dict(),
            "stock_anterior": stock_anterior,
            "stock_nuevo": ing.stock_actual,
        }

    # ══════════════════════════════════════════════════════
    # CU53 — Registrar entrada de mercancía
    # ══════════════════════════════════════════════════════

    async def registrar_entrada_mercancia(
        self,
        ingrediente_id: int,
        cantidad: float,
        orden_compra_id: Optional[int] = None,
        notas: Optional[str] = None,
    ) -> dict:
        """
        Suma la cantidad recibida al stock actual y cierra la orden de
        compra asociada si se proporcionó una.
        """
        db = await database.get_db()

        ing_row = await db.fetchrow(
            "SELECT * FROM ingredients WHERE id = $1 AND activo = TRUE",
            ingrediente_id,
        )
        if not ing_row:
            raise KeyError(f"Ingrediente {ingrediente_id} no encontrado.")

        ing = Ingredient.from_db_row(dict(ing_row))
        stock_anterior = ing.stock_actual
        ing.registrar_entrada(cantidad)

        async with db.transaction():
            updated = await db.fetchrow("""
                UPDATE ingredients
                   SET stock_actual = $2, ultima_actualizacion = NOW()
                 WHERE id = $1
             RETURNING id, nombre, stock_actual, stock_minimo, unidad_medida
            """, ingrediente_id, ing.stock_actual)

            await db.execute("""
                INSERT INTO inventory_adjustments
                    (ingrediente_id, stock_anterior, stock_nuevo, motivo,
                     tipo, orden_compra_id, fecha)
                VALUES ($1, $2, $3, $4, 'entrada_mercancia', $5, NOW())
            """, ingrediente_id, stock_anterior, ing.stock_actual,
                notas or "Entrada de mercancía", orden_compra_id)

            if orden_compra_id:
                await db.execute("""
                    UPDATE purchase_orders
                       SET estado = 'recibida', fecha_recepcion = NOW()
                     WHERE id = $1 AND estado = 'enviada'
                """, orden_compra_id)

        return {
            "mensaje": "Entrada de mercancía registrada.",
            "ingrediente": Ingredient.from_db_row(dict(updated)).to_dict(),
            "cantidad_añadida": cantidad,
            "stock_anterior": stock_anterior,
        }

    # ══════════════════════════════════════════════════════
    # CU56 — Registrar merma / desperdicio
    # ══════════════════════════════════════════════════════

    async def registrar_merma(
        self,
        ingrediente_id: int,
        cantidad: float,
        motivo: str,
        registrado_por: Optional[int] = None,
    ) -> WasteLog:
        """
        Valida cantidad, descuenta stock y persiste el WasteLog.

        Flujo del diagrama CU56:
          validarCantidadMenorIgualStock()
          → descontarInventario()
          → registrarPerdidaContable(motivo)
        """
        db = await database.get_db()

        ing_row = await db.fetchrow(
            "SELECT * FROM ingredients WHERE id = $1 AND activo = TRUE",
            ingrediente_id,
        )
        if not ing_row:
            raise KeyError(f"Ingrediente {ingrediente_id} no encontrado.")

        ing = Ingredient.from_db_row(dict(ing_row))

        # validarCantidadMenorIgualStock()
        if not ing.validar_cantidad_menor_igual_stock(cantidad):
            raise ValueError(
                f"La cantidad de merma ({cantidad} {ing.unidad_medida}) "
                f"supera el stock disponible ({ing.stock_actual} {ing.unidad_medida})."
            )

        # descontarInventario() — lógica de dominio
        ing.descontar_stock(cantidad)

        # registrarPerdidaContable(motivo)
        waste = WasteLog.registrar_perdida_contable(
            id=0,  # será reemplazado por el RETURNING de la BD
            ingrediente_id=ingrediente_id,
            cantidad=cantidad,
            motivo=motivo,
            costo_unitario=ing.costo_unitario,
            registrado_por=registrado_por,
            nombre_ingrediente=ing.nombre,
            unidad_medida=ing.unidad_medida,
        )

        async with db.transaction():
            await db.execute("""
                UPDATE ingredients
                   SET stock_actual = $2, ultima_actualizacion = NOW()
                 WHERE id = $1
            """, ingrediente_id, ing.stock_actual)

            row = await db.fetchrow("""
                INSERT INTO waste_logs
                    (ingrediente_id, cantidad, motivo, costo_estimado,
                     registrado_por, fecha)
                VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING *
            """, ingrediente_id, cantidad, motivo, waste.costo_estimado, registrado_por)

        waste.id = row["id"]
        return waste

    # ══════════════════════════════════════════════════════
    # CU55 — Lista de compras automatizada
    # ══════════════════════════════════════════════════════

    async def generar_lista_compras_automatizada(self) -> dict:
        """
        Identifica ingredientes bajo mínimo, los agrupa por proveedor
        y calcula cantidades hasta stock_optimo.

        Flujo del diagrama CU55:
          identificarIngredientesBajoMinimo()
          → agruparPorProveedor()
          → calcularCantidadHastaStockOptimo()
          → generarBorradorPedidoCompra()
        """
        db = await database.get_db()

        # identificarIngredientesBajoMinimo()
        rows = await db.fetch("""
            SELECT
                i.id, i.nombre, i.categoria, i.unidad_medida,
                i.stock_actual, i.stock_minimo, i.stock_optimo,
                i.costo_unitario, i.disponible, i.activo,
                i.ultima_actualizacion,
                GREATEST(0, i.stock_optimo - i.stock_actual) AS cantidad_sugerida,
                s.id   AS proveedor_id,
                s.nombre AS proveedor_nombre,
                s.activo AS proveedor_activo,
                s.email  AS proveedor_email
            FROM ingredients i
            LEFT JOIN ingredient_suppliers isu
                   ON isu.ingrediente_id = i.id AND isu.principal = TRUE
            LEFT JOIN suppliers s ON s.id = isu.proveedor_id
            WHERE i.activo = TRUE
              AND i.stock_actual < i.stock_minimo
            ORDER BY s.nombre NULLS LAST, i.nombre
        """)

        # agruparPorProveedor() — en memoria con entidades de dominio
        grupos: dict = {}
        sin_proveedor: list = []

        for r in rows:
            d = dict(r)
            ing = Ingredient.from_db_row(d)
            prov_id = d.get("proveedor_id")

            if prov_id is None:
                sin_proveedor.append({
                    **ing.to_dict(),
                    "cantidad_sugerida": ing.calcular_cantidad_hasta_stock_optimo(),
                })
                continue

            # validarProveedorActivo()
            supplier = Supplier(
                id=prov_id,
                nombre=d["proveedor_nombre"],
                contacto="",
                telefono="",
                email=d.get("proveedor_email", ""),
                activo=d["proveedor_activo"],
            )
            advertencia = supplier.resaltar_proveedor_inactivo()

            if prov_id not in grupos:
                grupos[prov_id] = {
                    "proveedor_id": prov_id,
                    "proveedor": d["proveedor_nombre"],
                    "proveedor_activo": d["proveedor_activo"],
                    "advertencia": advertencia,
                    "items": [],
                    "total_estimado": 0.0,
                }

            # calcularCantidadHastaStockOptimo()
            cantidad = ing.calcular_cantidad_hasta_stock_optimo()
            grupos[prov_id]["items"].append({
                **ing.to_dict(),
                "cantidad_sugerida": cantidad,
                "costo_estimado_item": round(cantidad * ing.costo_unitario, 2),
            })
            grupos[prov_id]["total_estimado"] = round(
                grupos[prov_id]["total_estimado"] + cantidad * ing.costo_unitario, 2
            )

        return {
            "total_ingredientes_bajo_minimo": len(rows),
            "ordenes_sugeridas": list(grupos.values()),
            "sin_proveedor_asignado": sin_proveedor,
        }

    # ══════════════════════════════════════════════════════
    # CU54 — Consumo teórico vs real (para ReportsController)
    # ══════════════════════════════════════════════════════

    async def calcular_consumo_teorico_vs_real(
        self, fecha_inicio: datetime, fecha_fin: datetime
    ) -> dict:
        """
        Compara consumo teórico (ventas × receta) contra mermas registradas.
        Corresponde a calcularConsumoTeoricoVsReal() — diagrama CU54.
        """
        db = await database.get_db()

        teorico = await db.fetch("""
            SELECT
                i.id AS ingrediente_id,
                i.nombre AS ingrediente,
                i.unidad_medida,
                i.costo_unitario,
                COALESCE(SUM(oi.cantidad * di.cantidad_base), 0) AS consumo_teorico,
                COALESCE(SUM(oi.cantidad * di.cantidad_base) * i.costo_unitario, 0) AS costo_teorico
            FROM ingredients i
            LEFT JOIN drink_ingredients di ON di.ingrediente_id = i.id
            LEFT JOIN order_items oi ON oi.bebida_id = di.bebida_id
            LEFT JOIN orders o ON o.id = oi.orden_id
                AND o.estado NOT IN ('cancelada', 'rechazada')
                AND o.fecha_creacion BETWEEN $1 AND $2
            WHERE i.activo = TRUE
            GROUP BY i.id, i.nombre, i.unidad_medida, i.costo_unitario
            ORDER BY consumo_teorico DESC
        """, fecha_inicio, fecha_fin)

        mermas = await db.fetch("""
            SELECT ingrediente_id,
                   SUM(cantidad) AS total_merma,
                   SUM(costo_estimado) AS costo_merma
            FROM waste_logs
            WHERE fecha BETWEEN $1 AND $2
            GROUP BY ingrediente_id
        """, fecha_inicio, fecha_fin)

        mermas_map = {r["ingrediente_id"]: dict(r) for r in mermas}

        resultado = []
        for row in teorico:
            d = dict(row)
            merma_data = mermas_map.get(d["ingrediente_id"], {})
            d["merma_registrada"] = float(merma_data.get("total_merma", 0))
            d["costo_merma"] = float(merma_data.get("costo_merma", 0))
            resultado.append(d)

        return {
            "periodo": {"inicio": fecha_inicio.isoformat(), "fin": fecha_fin.isoformat()},
            "ingredientes": resultado,
            "total_costo_teorico": round(sum(r["costo_teorico"] for r in resultado), 2),
            "total_costo_mermas": round(sum(r["costo_merma"] for r in resultado), 2),
        }