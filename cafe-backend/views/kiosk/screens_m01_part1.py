"""
views/kiosk/screens_m01.py
Módulo 01 — Experiencia del Cliente (CEM)

Clases Vista del Kiosk que corresponden a los archivos HTML:
  s1-bienvenida.html  → CustomerApp
  s2-categorias.html  → MenuScreen
  s3-detalle.html     → DrinkDetailScreen
  s4-personalizar.html→ CustomizationScreen
  s5-carrito.html     → CartScreen
  s6-pago.html        → PaymentScreen
  s7-confirmacion.html→ TrackingScreen
  s8-espera.html      → WaitingScreen

Cada clase:
  - Define los atributos del diagrama de clases
  - Implementa los métodos del diagrama de secuencia
  - Se comunica con el backend via HTTP (httpx)
  - Representa el contrato entre frontend y backend
"""

import httpx
from typing import Optional

BASE_URL = "http://localhost:8000/api"


# ══════════════════════════════════════════════════════════
# CustomerApp — s1-bienvenida.html
# CU70, CU27, CU69
# ══════════════════════════════════════════════════════════

class CustomerApp:
    """
    Pantalla principal de la app del cliente (bienvenida/splash).
    Corresponde a s1-bienvenida.html del Kiosk.

    Atributos del diagrama:
        (ninguno — es el punto de entrada)
    """

    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self._notificaciones: list = []

    async def notificar_en_app(self, titulo: str, mensaje: str) -> dict:
        """
        Muestra una notificación dentro de la app.
        Corresponde a notificarEnApp() — CU70.
        """
        notif = {"titulo": titulo, "mensaje": mensaje, "leida": False}
        self._notificaciones.append(notif)
        return notif

    async def guardar_en_mis_beneficios(self, cupon_codigo: str) -> dict:
        """
        Guarda un cupón en la sección de beneficios del usuario.
        Corresponde a guardarEnMisBeneficios() — CU70.
        """
        if not self.user_id:
            return {"guardado": False, "motivo": "Sesión no iniciada."}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/coupons/validate",
                json={"codigo": cupon_codigo},
                headers={"x-user-id": self.user_id},
            )
        return r.json()

    async def obtener_notificaciones(self) -> list:
        """
        Recupera notificaciones del usuario desde el backend.
        Corresponde a CU27 — Recibir notificaciones push.
        """
        if not self.user_id:
            return []
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/customer/notifications/{self.user_id}"
            )
        return r.json() if r.status_code == 200 else []


# ══════════════════════════════════════════════════════════
# MenuScreen — s2-categorias.html
# CU01, CU20, CU66
# ══════════════════════════════════════════════════════════

class MenuScreen:
    """
    Pantalla del catálogo de categorías y bebidas.
    Corresponde a s2-categorias.html del Kiosk.

    Atributos del diagrama:
        listaCategorias: List<Categoria>
        bebidas: List<Bebida>
    """

    def __init__(self):
        self.lista_categorias: list = []
        self.bebidas: list = []
        self._categoria_activa: Optional[int] = None

    async def seleccionar_ver_menu(self) -> list:
        """
        El cliente abre la pantalla del menú.
        Corresponde a seleccionarVerMenu() — CU01.
        Carga las categorías desde el backend.
        """
        self.lista_categorias = await self.mostrar_categorias()
        return self.lista_categorias

    async def mostrar_categorias(self) -> list:
        """
        Obtiene y retorna las categorías activas.
        Corresponde a mostrarCategorias() — CU01.
        Alimenta s2-categorias.html con los datos del backend.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/customer/menu/categories")
        self.lista_categorias = r.json() if r.status_code == 200 else []
        return self.lista_categorias

    async def mostrar_bebidas(self) -> list:
        """
        Retorna las bebidas de la categoría activa.
        Corresponde a mostrarBebidas() — CU01.
        """
        if not self._categoria_activa:
            return []
        return await self.seleccionar_categoria(self._categoria_activa)

    async def seleccionar_categoria(
        self,
        categoria_id: int,
        filtros: Optional[dict] = None,
    ) -> list:
        """
        El cliente toca una categoría en s2-categorias.html.
        Corresponde a seleccionarCategoria(categoriaId) — CU01.
        """
        self._categoria_activa = categoria_id
        params = {}
        if filtros:
            params.update(filtros)
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/customer/menu/categories/{categoria_id}/drinks",
                params=params,
            )
        self.bebidas = r.json() if r.status_code == 200 else []
        return self.bebidas

    async def mostrar_menu_completo(self) -> list:
        """
        Carga el menú completo para la vista de exploración.
        Corresponde a CU20 — Explorar menú completo en app.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/customer/menu/full")
        return r.json() if r.status_code == 200 else []


# ══════════════════════════════════════════════════════════
# DrinkDetailScreen — s3-detalle.html
# CU02, CU08, CU09, CU11
# ══════════════════════════════════════════════════════════

class DrinkDetailScreen:
    """
    Pantalla de detalle de una bebida con galería de ingredientes.
    Corresponde a s3-detalle.html del Kiosk.

    Atributos del diagrama:
        bebidaId: String
        listaIngredientes: List<Ingrediente>
    """

    def __init__(self):
        self.bebida_id: Optional[int] = None
        self.lista_ingredientes: list = []
        self._detalle_bebida: Optional[dict] = None

    async def seleccionar_bebida(self, bebida_id: int) -> dict:
        """
        El cliente selecciona una bebida de s2-categorias.html.
        Corresponde a seleccionarBebida(bebidaId) — CU02.
        Navega a s3-detalle.html con los datos de la bebida.
        """
        self.bebida_id = bebida_id
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/customer/drinks/{bebida_id}")
        if r.status_code == 200:
            self._detalle_bebida = r.json()
            self.lista_ingredientes = self._detalle_bebida.get("ingredientes", [])
        return self._detalle_bebida or {}

    async def mostrar_galeria_ingredientes(self) -> list:
        """
        Muestra los ingredientes con imágenes en s3-detalle.html.
        Corresponde a mostrarGaleriaIngredientes() — CU02.
        """
        return self.lista_ingredientes

    async def verificar_disponibilidad(self) -> dict:
        """
        Verifica si la bebida está disponible antes de personalizar.
        Corresponde a CU11 — Notificación ingrediente no disponible.
        """
        if not self.bebida_id:
            return {"disponible": False}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/customer/drinks/{self.bebida_id}/availability"
            )
        return r.json() if r.status_code == 200 else {"disponible": False}

    async def obtener_sugerencias(self, cliente_id: Optional[str] = None) -> list:
        """
        Muestra sugerencias de combinaciones en s3-detalle.html.
        Corresponde a CU08 — Recibir sugerencias.
        """
        if not self.bebida_id:
            return []
        params = {}
        if cliente_id:
            params["cliente_id"] = cliente_id
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/customer/drinks/{self.bebida_id}/suggestions",
                params=params,
            )
        return r.json() if r.status_code == 200 else []


# ══════════════════════════════════════════════════════════
# CustomizationScreen — s4-personalizar.html
# CU03, CU04, CU05, CU06, CU07, CU09, CU10
# ══════════════════════════════════════════════════════════

class CustomizationScreen:
    """
    Pantalla de personalización de la bebida.
    Corresponde a s4-personalizar.html del Kiosk.

    Atributos del diagrama:
        size: String
        precioBase: Double
        ingrediente: Ingrediente
        cantidad: Int
        limiteAlcanzado: Boolean
        totalMostrado: Double
        errorCalculo: Boolean
    """

    UMBRAL_COSTO_ELEVADO = 150.0  # CU10: advertencia si supera este monto

    def __init__(self, bebida_id: int):
        self.bebida_id = bebida_id
        self.size: str = "Mediano"
        self.precio_base: float = 0.0
        self.total_mostrado: float = 0.0
        self.error_calculo: bool = False
        self.limite_alcanzado: bool = False
        self.ingredientes_personalizados: list = []
        self.notas_especiales: str = ""
        self._modelo_3d: Optional[dict] = None

    async def mostrar_opciones_tamano(self) -> dict:
        """
        Carga los precios por tamaño al abrir s4-personalizar.html.
        Corresponde a mostrarOpcionesTamaño() — CU03.
        """
        precios = {}
        async with httpx.AsyncClient() as client:
            for tamano in ["Chico", "Mediano", "Grande"]:
                r = await client.get(
                    f"{BASE_URL}/customer/drinks/{self.bebida_id}/price/{tamano}"
                )
                if r.status_code == 200:
                    precios[tamano] = r.json().get("precio_base", 0)
        return precios

    async def seleccionar_tamano(self, size: str) -> float:
        """
        El cliente elige el tamaño en s4-personalizar.html.
        Corresponde a seleccionarTamaño(size) — CU03.
        """
        self.size = size
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/customer/drinks/{self.bebida_id}/price/{size}"
            )
        if r.status_code == 200:
            self.precio_base = r.json().get("precio_base", 0)
        await self.actualizar_vista_precio()
        return self.precio_base

    async def actualizar_vista_precio(self) -> float:
        """
        Recalcula y muestra el precio en tiempo real.
        Corresponde a actualizarVistaPrecio() — CU03 / refrescarMontoEnPantalla() — CU05.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/pricing/calculate",
                json={
                    "bebida_id": self.bebida_id,
                    "tamano": self.size,
                    "ingredientes": self.ingredientes_personalizados,
                },
            )
        if r.status_code == 200:
            data = r.json()
            self.total_mostrado = data.get("total", 0)
            self.error_calculo = False
            # CU10: advertencia si el precio es muy elevado
            if self.total_mostrado > self.UMBRAL_COSTO_ELEVADO:
                await self.advertencia_costo_elevado()
        else:
            self.error_calculo = True
        return self.total_mostrado

    async def advertencia_costo_elevado(self) -> dict:
        """
        Muestra advertencia cuando el precio supera el umbral.
        Corresponde a CU10 — Advertencia de costo elevado.
        """
        return {
            "advertencia": True,
            "mensaje": (
                f"⚠ El costo de tu bebida (${self.total_mostrado:.2f}) "
                f"es mayor al habitual. ¿Deseas continuar?"
            ),
            "total": self.total_mostrado,
        }

    async def modificar_ingrediente(
        self, ingrediente_id: int, cantidad: int
    ) -> dict:
        """
        El cliente ajusta la cantidad de un ingrediente con +/-.
        Corresponde a modificarIngrediente(+/-) — CU04.
        """
        # Actualizar ingredientes personalizados
        encontrado = False
        for ing in self.ingredientes_personalizados:
            if ing["ingrediente_id"] == ingrediente_id:
                ing["cantidad"] = max(0, cantidad)
                encontrado = True
                break
        if not encontrado and cantidad > 0:
            self.ingredientes_personalizados.append({
                "ingrediente_id": ingrediente_id,
                "cantidad": cantidad,
            })

        # Verificar incompatibilidades — CU09
        ids = [i["ingrediente_id"] for i in self.ingredientes_personalizados if i["cantidad"] > 0]
        advertencias = []
        if len(ids) >= 2:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{BASE_URL}/customer/drinks/incompatibilities",
                    json={"ingredientes_ids": ids},
                )
            if r.status_code == 200:
                advertencias = r.json()

        # Recalcular precio
        await self.actualizar_vista_precio()

        return {
            "ingredientes": self.ingredientes_personalizados,
            "total": self.total_mostrado,
            "advertencias_incompatibilidad": advertencias,
        }

    async def agregar_al_carrito(self) -> dict:
        """
        Envía la bebida personalizada al carrito.
        Corresponde a agregarAlCarrito() — CU04.
        Retorna los datos del ítem para que CartScreen los reciba.
        """
        return {
            "bebida_id": self.bebida_id,
            "tamano": self.size,
            "precio_base": self.precio_base,
            "precio_final": self.total_mostrado,
            "cantidad": 1,
            "ingredientes_personalizados": self.ingredientes_personalizados,
            "notas_item": self.notas_especiales or None,
        }

    async def anadir_notas_especiales(self, notas: str) -> str:
        """
        El cliente escribe notas especiales para su bebida.
        Corresponde a CU07 — Añadir notas especiales.
        Las notas se incluyen en el ítem al agregar al carrito.
        """
        self.notas_especiales = notas.strip()
        return self.notas_especiales

    async def trigger_renderizado(self) -> dict:
        """
        Solicita el renderizado 3D de la bebida personalizada.
        Corresponde a triggerRenderizado() — CU06.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/drinks/render",
                json={
                    "bebida_id": self.bebida_id,
                    "tamano": self.size,
                    "ingredientes": self.ingredientes_personalizados,
                },
            )
        if r.status_code == 200:
            self._modelo_3d = r.json()
        return self._modelo_3d or {}

    async def sincronizar_precios(self) -> float:
        """
        Sincroniza el precio mostrado con el calculado en backend.
        Corresponde a sincronizarPrecios() — CU05.
        """
        return await self.actualizar_vista_precio()


# ══════════════════════════════════════════════════════════
# CartScreen — s5-carrito.html
# CU31, CU12
# ══════════════════════════════════════════════════════════

class CartScreen:
    """
    Pantalla del carrito de compras.
    Corresponde a s5-carrito.html del Kiosk.

    Atributos del diagrama:
        codigo: String
        descuento: Double
    """

    def __init__(self, cliente_id: str):
        self.cliente_id = cliente_id
        self.codigo: str = ""
        self.descuento: float = 0.0
        self._items: list = []
        self._orden_id: Optional[str] = None
        self._subtotal: float = 0.0

    def agregar_item(self, item: dict) -> None:
        """Agrega un ítem al carrito (llamado desde CustomizationScreen)."""
        self._items.append(item)
        self._subtotal += item.get("precio_final", 0) * item.get("cantidad", 1)

    async def ingresar_codigo_cupon(self, codigo: str) -> dict:
        """
        El cliente ingresa un código de cupón en s5-carrito.html.
        Corresponde a ingresarCodigoCupon(codigo) — CU31.
        """
        self.codigo = codigo
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/coupons/validate",
                json={"codigo": codigo},
                headers={"x-user-id": self.cliente_id},
            )
        resultado = r.json()
        if resultado.get("valido"):
            self.descuento = resultado.get("descuento", 0)
        else:
            await self.mostrar_motivo_cupon_invalido(resultado.get("motivo", ""))
        return resultado

    async def aplicar_descuento(self) -> dict:
        """
        Aplica el cupón a la orden activa.
        Corresponde a aplicarDescuento() — CU31.
        """
        if not self._orden_id or not self.codigo:
            return {"aplicado": False}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/coupons/{self._orden_id}/apply",
                json={"codigo": self.codigo},
            )
        return r.json()

    async def actualizar_monto_total(self) -> float:
        """
        Recalcula y muestra el total con descuento aplicado.
        Corresponde a actualizarMontoTotal() — CU31.
        """
        total = self._subtotal - self.descuento
        return max(0.0, round(total, 2))

    async def mostrar_motivo_cupon_invalido(self, motivo: str) -> dict:
        """
        Muestra el motivo por el que el cupón no es válido.
        Corresponde a mostrarMotivoCuponInvalido() — CU31.
        """
        return {"error": True, "motivo": motivo}

    async def confirmar_pedido(self, notas_generales: Optional[str] = None) -> dict:
        """
        El cliente confirma el pedido desde s5-carrito.html.
        Corresponde a CU12 — Confirmar y realizar pedido.
        Crea la orden en el backend y navega a s6-pago.html.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/orders",
                json={
                    "cliente_id": self.cliente_id,
                    "items": self._items,
                    "notas_generales": notas_generales,
                    "cupon_codigo": self.codigo or None,
                },
            )
        if r.status_code == 201:
            data = r.json()
            self._orden_id = data.get("orden_id")
            return data
        return {"error": True, "detalle": r.text}