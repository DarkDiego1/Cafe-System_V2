"""
controllers/m01_controllers.py
Módulo 01 — Experiencia del Cliente (CEM)

Todos los controladores del M01 en un archivo para facilitar imports.
Cada clase corresponde al controlador de su diagrama de secuencia.

Controladores:
  AuthController        — CU16, CU17, CU18, CU19
  MenuRouter            — CU01, CU20
  DrinkController       — CU02, CU03, CU04, CU06, CU11
  PricingController     — CU05
  OrderController       — CU12, CU14, CU22, CU23, CU24
  PaymentController     — CU29, CU30, CU32, CU33, CU34, CU35
  CouponController      — CU31, CU68, CU70
  PromotionsController  — CU15, CU73
  WalletPaymentController — CU30
  VisualizationController — CU06
"""

from typing import Optional
from fastapi import HTTPException

from services.auth_service import AuthService
from services.menu_service import MenuService, DrinkService
from services.order_service import OrderService
from services.payment_service import (
    PaymentGatewayService, WalletSdkService,
    CouponService, EmailService, PromotionsService,
)
from services.experience_service import DrinkRenderer, RecommendationEngine


# ══════════════════════════════════════════════════════════
# AuthController — CU16, CU17, CU18, CU19
# ══════════════════════════════════════════════════════════

class AuthController:
    def __init__(self):
        self._service = AuthService()

    async def registrar_usuario(
        self, nombre: str, correo: str, contrasena: str,
        telefono: Optional[str] = None, fecha_cumpleanos: Optional[str] = None,
    ) -> dict:
        """CU16 — Registrar nuevo usuario."""
        try:
            user = await self._service.crear_cuenta(
                nombre, correo, contrasena, telefono, fecha_cumpleanos
            )
            return user.to_dict()
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    async def iniciar_sesion(self, correo: str, contrasena: str) -> dict:
        """CU17 — Iniciar sesión."""
        try:
            return await self._service.iniciar_sesion(correo, contrasena)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))

    async def enviar_enlace_recuperacion(self, correo: str) -> dict:
        """CU18 — Recuperar contraseña."""
        if not await self._service.verificar_correo_existente(correo):
            raise HTTPException(status_code=404, detail="Correo no registrado.")
        token = await self._service.generar_enlace_recuperacion(correo)
        email_svc = EmailService()
        return await email_svc.enviar_correo_recuperacion(correo, token)

    async def restablecer_contrasena(self, token: str, nueva: str) -> dict:
        ok = await self._service.restablecer_contrasena(token, nueva)
        if not ok:
            raise HTTPException(status_code=400, detail="Token inválido o expirado.")
        return {"mensaje": "Contraseña restablecida exitosamente."}

    async def actualizar_perfil(self, user_id: str, campos: dict) -> dict:
        """CU19 — Gestionar perfil."""
        try:
            user = await self._service.actualizar_perfil(user_id, campos)
            return user.to_dict()
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def cerrar_sesion(self, user_id: str) -> dict:
        await self._service.cerrar_sesion(user_id)
        return {"mensaje": "Sesión cerrada."}


# ══════════════════════════════════════════════════════════
# MenuRouter — CU01, CU20
# ══════════════════════════════════════════════════════════

class MenuRouter:
    """
    Nota: se llama MenuRouter en el diagrama para diferenciarlo
    del router de FastAPI. Actúa como controlador.
    """
    def __init__(self):
        self._service = MenuService()

    async def get_categorias(self) -> list[dict]:
        """CU01 — Obtener categorías."""
        return await self._service.obtener_categorias()

    async def get_bebidas(self, categoria_id: int, filtros: Optional[dict] = None) -> list[dict]:
        """CU01 — Obtener bebidas por categoría."""
        return await self._service.obtener_bebidas_por_categoria(categoria_id, filtros)

    async def get_menu_completo(self) -> list[dict]:
        """CU20 — Explorar menú completo."""
        return await self._service.obtener_menu_completo()


# ══════════════════════════════════════════════════════════
# DrinkController — CU02, CU03, CU04, CU06, CU09, CU11
# ══════════════════════════════════════════════════════════

class DrinkController:
    def __init__(self):
        self._drink_svc = DrinkService()
        self._renderer  = DrinkRenderer()

    async def get_ingredientes(self, bebida_id: int) -> list[dict]:
        """CU02 — Obtener ingredientes de bebida."""
        try:
            return await self._drink_svc.obtener_ingredientes(bebida_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def get_detalle_bebida(self, bebida_id: int) -> dict:
        """CU02 — Detalle completo de la bebida."""
        try:
            return await self._drink_svc.obtener_bebida_detalle(bebida_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def actualizar_precio_base(self, bebida_id: int, tamano: str) -> dict:
        """CU03 — Precio según tamaño."""
        try:
            precio = await self._drink_svc.calcular_precio_base(bebida_id, tamano)
            return {"bebida_id": bebida_id, "tamano": tamano, "precio_base": precio}
        except (KeyError, ValueError) as e:
            code = 404 if isinstance(e, KeyError) else 422
            raise HTTPException(status_code=code, detail=str(e))

    async def validar_limite_receta(self, bebida_id: int) -> dict:
        """CU04 — Verifica disponibilidad para personalizar."""
        return await self._drink_svc.verificar_disponibilidad(bebida_id)

    async def solicitar_render(self, configuracion: dict) -> dict:
        """CU06 — Renderizar bebida en 3D."""
        return self._renderer.renderizar_bebida(configuracion)


# ══════════════════════════════════════════════════════════
# PricingController — CU05
# ══════════════════════════════════════════════════════════

class PricingController:
    def __init__(self):
        self._order_svc = OrderService()

    async def recalcular_total(
        self, bebida_id: int, tamano: str, ingredientes: list[dict]
    ) -> dict:
        """
        CU05 — Calcular precio en tiempo real.
        Corresponde a detectarCambioOrden() → recalcularTotal().
        """
        return await self._order_svc.recalcular_total(bebida_id, tamano, ingredientes)


# ══════════════════════════════════════════════════════════
# OrderController — CU12, CU14, CU22, CU23
# ══════════════════════════════════════════════════════════

class OrderController:
    def __init__(self):
        self._service = OrderService()

    async def crear_orden(self, cliente_id: str, items: list, **kwargs) -> dict:
        """CU12 — Confirmar y realizar pedido."""
        try:
            return await self._service.crear_orden(cliente_id, items, **kwargs)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))

    async def solicitar_cancelacion(self, orden_id: str) -> dict:
        """CU14 — Cancelar pedido."""
        try:
            return await self._service.solicitar_cancelacion(orden_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def get_historial(self, cliente_id: str) -> list[dict]:
        """CU22 — Ver historial de pedidos."""
        return await self._service.obtener_historial(cliente_id)

    async def reordenar(self, orden_id: str, cliente_id: str) -> dict:
        """CU23 — Reordenar con un clic."""
        try:
            return await self._service.reordenar(orden_id, cliente_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def get_favoritas(self, cliente_id: str) -> list[dict]:
        """CU21 — Favoritas."""
        return await self._service.obtener_favoritas(cliente_id)

    async def guardar_favorita(
        self, cliente_id: str, bebida_id: int, nombre: str
    ) -> dict:
        """CU21 — Guardar favorita."""
        return await self._service.guardar_favorita(cliente_id, bebida_id, nombre)


# ══════════════════════════════════════════════════════════
# PaymentController — CU29, CU32, CU33, CU34, CU35
# ══════════════════════════════════════════════════════════

class PaymentController:
    def __init__(self):
        self._gateway = PaymentGatewayService()
        self._email   = EmailService()

    async def procesar_pago_tarjeta(
        self, orden_id: str, monto: float, token: str
    ) -> dict:
        """CU29 — Pago con tarjeta."""
        resultado = await self._gateway.procesar_pago_tarjeta(orden_id, monto, token)
        if resultado["exitoso"]:
            await self._gateway.registrar_transaccion(orden_id, resultado["transaccion_id"])
        return resultado

    def registrar_id_transaccion(self, transaccion_id: str) -> dict:
        """CU32 — Registrar ID de transacción."""
        return {"transaccion_id": transaccion_id, "registrado": True}

    async def actualizar_estado_pedido(self, payload: dict) -> dict:
        """CU32 — Webhook confirma pago."""
        return await self._gateway.procesar_webhook(payload)

    async def generar_recibo_pdf(self, orden_id: str, correo: str) -> dict:
        """CU13/CU34 — Generar y enviar recibo."""
        return await self._email.enviar_correo_recibo(correo, orden_id)

    async def dejar_propina(self, orden_id: str, monto: float) -> dict:
        """CU35 — Dejar propina digital."""
        return await self._gateway.dejar_propina(orden_id, monto)


# ══════════════════════════════════════════════════════════
# WalletPaymentController — CU30
# ══════════════════════════════════════════════════════════

class WalletPaymentController:
    def __init__(self):
        self._wallet = WalletSdkService()

    async def procesar_pago_billetera(
        self, orden_id: str, monto: float, token: str, tipo: str = "apple_pay"
    ) -> dict:
        """CU30 — Pago con billetera digital."""
        return await self._wallet.procesar_pago_billetera(orden_id, monto, token, tipo)


# ══════════════════════════════════════════════════════════
# CouponController — CU31, CU68, CU70
# ══════════════════════════════════════════════════════════

class CouponController:
    def __init__(self):
        self._service = CouponService()

    async def validar_cupon(
        self, codigo: str, cliente_id: Optional[str] = None
    ) -> dict:
        """CU31 — Validar cupón."""
        return await self._service.verificar_cupon(codigo, cliente_id)

    async def aplicar_cupon(self, orden_id: str, codigo: str) -> dict:
        """CU31 — Aplicar descuento."""
        return await self._service.aplicar_cupon(orden_id, codigo)

    async def canjear_puntos(self, user_id: str, puntos: int) -> dict:
        """CU68 — Canjear puntos por recompensas."""
        import database
        db = await database.get_db()
        saldo = await db.fetchval(
            "SELECT puntos_lealtad FROM users WHERE id = $1::uuid", user_id
        )
        if saldo is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        if saldo < puntos:
            raise HTTPException(
                status_code=422,
                detail=f"Saldo insuficiente: {saldo} puntos disponibles."
            )
        await db.execute(
            "UPDATE users SET puntos_lealtad = puntos_lealtad - $2 WHERE id = $1::uuid",
            user_id, puntos,
        )
        return {"canjeado": True, "puntos_usados": puntos, "saldo_nuevo": saldo - puntos}

    async def generar_cupon_cumpleanos(self, user_id: str) -> dict:
        """CU70 — Cupón de cumpleaños."""
        cupon = await self._service.generar_cupon_cumpleanos(user_id)
        return cupon.to_dict()


# ══════════════════════════════════════════════════════════
# PromotionsController — CU15, CU73
# ══════════════════════════════════════════════════════════

class PromotionsController:
    def __init__(self):
        self._service = PromotionsService()

    async def get_promociones_vigentes(self) -> list[dict]:
        """CU15 — Ver promociones vigentes."""
        return await self._service.obtener_promociones_vigentes()

    async def aplicar_qr(self, codigo_qr: str, orden_id: str) -> dict:
        """CU73 — Escanear QR para promoción."""
        try:
            return await self._service.aplicar_promocion_qr(codigo_qr, orden_id)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))


# ══════════════════════════════════════════════════════════
# VisualizationController — CU06
# ══════════════════════════════════════════════════════════

class VisualizationController:
    def __init__(self):
        self._renderer = DrinkRenderer()

    def solicitar_render(self, configuracion: dict) -> dict:
        """CU06 — Solicitar render 3D."""
        return self._renderer.renderizar_bebida(configuracion)

    def actualizar_modelo_3d(self, modelo: dict, cambio: dict) -> dict:
        """CU06 — Actualizar modelo en tiempo real."""
        return self._renderer.actualizar_modelo_3d(modelo, cambio)