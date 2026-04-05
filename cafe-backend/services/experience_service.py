"""
services/experience_service.py
Módulo 01 — Experiencia del Cliente (CEM)

Servicios: DrinkRenderer, RecommendationEngine
Componente: MiniGame
Casos de uso: CU06, CU08, CU09, CU69, CU71, CU74, CU75
"""

from typing import Optional
import database


class DrinkRenderer:
    """
    Genera la visualización 3D de la bebida personalizada.
    Casos de uso: CU06 — Visualizar bebida personalizada en 3D.

    Atributos del diagrama:
        configuracion: Object
        modelo3D: Object
    """

    def renderizar_bebida(self, configuracion: dict) -> dict:
        """
        Genera la configuración de render 3D.
        Corresponde a renderizarBebida(configuracion) — CU06.
        En producción enviaría la config a un motor 3D (Three.js).

        Args:
            configuracion: {bebida_id, tamano, ingredientes, colores}

        Returns:
            dict con modelo3D, capas, instrucciones de render.
        """
        return {
            "modelo3D": {
                "base": configuracion.get("bebida_id"),
                "tamano": configuracion.get("tamano", "mediano"),
                "capas": self.aplicar_capas(configuracion.get("ingredientes", [])),
                "opacidad": 0.85,
                "animacion": "fill",
            },
            "listo": True,
        }

    def aplicar_capas(self, ingredientes: list) -> list[dict]:
        """
        Genera las capas visuales de cada ingrediente.
        Corresponde a aplicarCapas() — CU06.
        """
        colores_defecto = {
            "café": "#3d1a00",
            "leche": "#f5f0e8",
            "chocolate": "#4a1c00",
            "caramelo": "#c8860a",
            "crema": "#fffde7",
        }
        capas = []
        for i, ing in enumerate(ingredientes):
            nombre = ing.get("nombre", "").lower()
            color = colores_defecto.get(nombre, "#888888")
            capas.append({
                "orden": i,
                "nombre": ing.get("nombre"),
                "color": color,
                "altura_pct": round(100 / max(len(ingredientes), 1), 1),
            })
        return capas

    def actualizar_modelo_3d(self, modelo_actual: dict, cambio: dict) -> dict:
        """
        Actualiza el modelo 3D cuando el cliente cambia personalización.
        Corresponde a actualizarModelo3D() — CU06.
        """
        modelo_actual.update(cambio)
        return modelo_actual


class RecommendationEngine:
    """
    Motor de recomendaciones basado en historial, clima y preferencias.
    Casos de uso: CU08, CU74, CU75.

    Atributos del diagrama:
        temp: Double — temperatura actual
    """

    async def recomendar_combinaciones(
        self, bebida_id: int, cliente_id: Optional[str] = None
    ) -> list[dict]:
        """
        Sugiere combinaciones o bebidas complementarias.
        Corresponde a CU08 — Recibir sugerencias de combinaciones.
        """
        db = await database.get_db()
        rows = await db.fetch("""
            SELECT d.id, d.nombre, d.imagen_url,
                   d.precio_mediano AS precio,
                   c.nombre AS categoria
            FROM drinks d
            JOIN categories c ON c.id = d.categoria_id
            WHERE d.id != $1
              AND d.activo = TRUE
              AND d.disponible = TRUE
            ORDER BY RANDOM()
            LIMIT 4
        """, bebida_id)
        return [dict(r) for r in rows]

    async def detectar_temperatura_actual(
        self, temperatura: float
    ) -> dict:
        """
        Detecta la temperatura y determina la categoría de bebida sugerida.
        Corresponde a detectarTemperaturaActual(temp) — CU75.
        """
        categoria = self.determinar_categoria_prioritaria(temperatura)
        return {
            "temperatura": temperatura,
            "categoria_sugerida": categoria,
            "mensaje": self.mostrar_mensaje_contextual(temperatura),
        }

    def determinar_categoria_prioritaria(self, temperatura: float) -> str:
        """
        Determina si recomendar frías o calientes según temperatura.
        Corresponde a determinarCategoriaPrioritaria(temp) — CU75.
        """
        if temperatura >= 25:
            return "frias"
        elif temperatura <= 18:
            return "calientes"
        return "cualquiera"

    def priorizar_bebidas_frias_o_calientes(self, temperatura: float) -> str:
        """Alias explícito del diagrama CU75."""
        return self.determinar_categoria_prioritaria(temperatura)

    def mostrar_mensaje_contextual(self, temperatura: float) -> str:
        """
        Genera mensaje contextual según el clima.
        Corresponde a mostrarMensajeContextual() — CU75.
        """
        if temperatura >= 28:
            return f"¡Hace {temperatura}°C! Te recomendamos algo bien frío 🧊"
        elif temperatura <= 15:
            return f"Con {temperatura}°C, caliéntate con una bebida caliente ☕"
        return "Día perfecto para cualquier bebida 😊"

    def gps_no_disponible(self) -> dict:
        """
        Maneja el caso en que no hay GPS disponible.
        Corresponde a GPSNoDisponible() — CU75.
        """
        return {
            "gps_disponible": False,
            "accion": "solicitar_codigo_postal",
            "mensaje": "Activa tu ubicación para recomendaciones personalizadas.",
        }

    async def solicitar_codigo_postal_o_recomendacion_generica(
        self, codigo_postal: Optional[str] = None
    ) -> list[dict]:
        """
        Retorna recomendaciones genéricas si no hay ubicación.
        Corresponde a solicitarCodigoPostalORecomendacionGenerica() — CU75.
        """
        db = await database.get_db()
        rows = await db.fetch("""
            SELECT d.id, d.nombre, d.imagen_url, d.precio_mediano AS precio
            FROM drinks d
            WHERE d.activo = TRUE AND d.disponible = TRUE
            ORDER BY RANDOM()
            LIMIT 5
        """)
        return [dict(r) for r in rows]

    async def recomendar_por_clima(
        self, temperatura: float, codigo_postal: Optional[str] = None
    ) -> dict:
        """
        Flujo completo de recomendaciones por clima.
        Corresponde al flujo CU74 completo.
        """
        db = await database.get_db()
        info_temp = await self.detectar_temperatura_actual(temperatura)
        categoria = info_temp["categoria_sugerida"]

        if categoria in ("frias", "calientes"):
            rows = await db.fetch("""
                SELECT d.id, d.nombre, d.imagen_url, d.precio_mediano AS precio
                FROM drinks d
                JOIN categories c ON c.id = d.categoria_id
                WHERE d.activo = TRUE AND d.disponible = TRUE
                  AND LOWER(c.nombre) LIKE $1
                ORDER BY RANDOM()
                LIMIT 5
            """, f"%{categoria[:4]}%")
        else:
            rows = await db.fetch("""
                SELECT d.id, d.nombre, d.imagen_url, d.precio_mediano AS precio
                FROM drinks d WHERE d.activo = TRUE AND d.disponible = TRUE
                ORDER BY RANDOM() LIMIT 5
            """)

        return {
            **info_temp,
            "bebidas_recomendadas": [dict(r) for r in rows],
        }

    async def mood_selector(self, estado_animo: str) -> list[dict]:
        """
        Sugiere bebidas según el estado de ánimo del cliente.
        Corresponde a CU71 — Mood selector para sugerencias.
        """
        db = await database.get_db()
        rows = await db.fetch("""
            SELECT d.id, d.nombre, d.imagen_url, d.precio_mediano AS precio
            FROM drinks d
            WHERE d.activo = TRUE AND d.disponible = TRUE
            ORDER BY RANDOM()
            LIMIT 4
        """)
        return [dict(r) for r in rows]


class MiniGame:
    """
    Componente del mini-juego mientras el cliente espera su orden.
    Casos de uso: CU69 — Jugar mini-juego mientras espera.
    """

    def ejecutar_juego_ligero(self) -> dict:
        """
        Inicializa el estado del mini-juego.
        Corresponde a ejecutarJuegoLigero() — CU69.
        """
        return {
            "juego": "cafe_match",
            "estado": "iniciado",
            "puntuacion": 0,
            "nivel": 1,
            "tiempo_max_seg": 120,
        }

    def interrumpir_juego_y_mostrar_notificacion(self, datos_orden: dict) -> dict:
        """
        Interrumpe el juego cuando la orden está lista.
        Corresponde a interrumpirJuegoYMostrarNotificacion() — CU69.
        Recibe el evento de CU43 (NotificationService).
        """
        return {
            "juego_pausado": True,
            "mensaje": f"¡Tu orden {datos_orden.get('codigo_orden')} está lista! 🎉",
            "accion": "mostrar_notificacion_orden_lista",
        }

    def recibir_evento_orden_lista(self, datos_orden: dict) -> dict:
        """
        Maneja el evento CU43 dentro del contexto del mini-juego.
        Corresponde a recibirEventoOrdenLista(UC43) — CU69.
        """
        return self.interrumpir_juego_y_mostrar_notificacion(datos_orden)