"""
views/kiosk/screens_m01_part2.py
Módulo 01 — Experiencia del Cliente (CEM)

Clases Vista (continuación):
  s6-pago.html        → PaymentScreen
  s7-confirmacion.html→ TrackingScreen
  s8-espera.html      → WaitingScreen

Clases Vista de Auth (sin HTML propio — son modales/secciones):
  LoginScreen
  RegisterScreen
  PasswordRecoveryScreen
  PromotionsScreen
  MobileApp
  PaymentModule
"""

import httpx
from typing import Optional

BASE_URL = "http://localhost:8000/api"


# ══════════════════════════════════════════════════════════
# PaymentScreen — s6-pago.html
# CU13, CU28, CU29, CU33, CU34, CU35
# ══════════════════════════════════════════════════════════

class PaymentScreen:
    """
    Pantalla de pago de la orden.
    Corresponde a s6-pago.html del Kiosk.

    Atributos del diagrama:
        correo: String
        pdf: Blob
        datosPago: Object
    """

    def __init__(self, orden_id: str, total: float):
        self.orden_id = orden_id
        self.total = total
        self.correo: str = ""
        self.datos_pago: dict = {}
        self._metodo_seleccionado: str = ""

    async def seleccionar_metodo_pago(self, metodo: str) -> dict:
        """
        El cliente elige el método de pago en s6-pago.html.
        Corresponde a CU28 — Seleccionar método de pago.
        metodo: 'tarjeta' | 'apple_pay' | 'google_pay'
        """
        self._metodo_seleccionado = metodo
        return {
            "metodo": metodo,
            "orden_id": self.orden_id,
            "total": self.total,
        }

    async def procesar_pago(self, datos_pago: dict) -> dict:
        """
        Envía los datos de pago al backend.
        Corresponde a procesarPago(datosPago) — CU29.
        """
        self.datos_pago = datos_pago
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/payments/card",
                json={
                    "orden_id": self.orden_id,
                    "monto": self.total,
                    "token_tarjeta": datos_pago.get("token", ""),
                },
            )
        return r.json()

    async def enviar_orden_produccion(self) -> dict:
        """
        Confirma el pago y envía la orden a producción.
        Corresponde a enviarOrdenProduccion() — CU29.
        La orden pasa de 'Pagado' a la cola del barista.
        """
        return {
            "enviada_produccion": True,
            "orden_id": self.orden_id,
            "mensaje": "Tu orden fue enviada a preparación.",
        }

    async def mostrar_motivo_rechazo(self, motivo: str) -> dict:
        """
        Muestra el motivo del rechazo del pago.
        Corresponde a mostrarMotivoRechazo() — CU29/CU33.
        """
        return {"rechazado": True, "motivo": motivo}

    async def permitir_ingresar_nueva_tarjeta(self) -> dict:
        """
        Habilita el formulario para reintentar con otra tarjeta.
        Corresponde a permitirIngresarNuevaTarjeta() — CU33.
        """
        self.datos_pago = {}
        return {"reintentar": True}

    async def ingresar_correo(self, correo: str) -> dict:
        """
        El cliente ingresa su correo para recibir el recibo.
        Corresponde a ingresarCorreo(correo) — CU13.
        """
        if "@" not in correo:
            return await self.marcar_campo_correo_invalido()
        self.correo = correo
        return {"correo_valido": True, "correo": correo}

    async def marcar_campo_correo_invalido(self) -> dict:
        """
        Marca el campo de correo como inválido en s6-pago.html.
        Corresponde a marcarCampoCorreoInvalido() — CU13.
        """
        return {"correo_invalido": True, "mensaje": "Ingresa un correo válido."}

    async def solicitar_recibo_digital(self) -> dict:
        """
        Solicita el envío del recibo por correo.
        Corresponde a CU13 — Solicitar recibo digital por correo.
        """
        if not self.correo:
            return {"enviado": False, "motivo": "No hay correo registrado."}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/payments/{self.orden_id}/receipt",
                params={"correo": self.correo},
            )
        return r.json()

    async def dejar_propina(self, monto: float) -> dict:
        """
        El cliente agrega una propina digital.
        Corresponde a CU35 — Dejar propina digital.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/payments/{self.orden_id}/tip",
                json={"monto": monto},
            )
        return r.json()


# ══════════════════════════════════════════════════════════
# PaymentModule — módulo de pago embebido en s6-pago.html
# CU30, CU32
# ══════════════════════════════════════════════════════════

class PaymentModule:
    """
    Módulo de pago (componente de billetera digital y webhook).
    Embebido en s6-pago.html del Kiosk.

    Atributos del diagrama: (ninguno)
    """

    def __init__(self, orden_id: str, total: float):
        self.orden_id = orden_id
        self.total = total

    async def seleccionar_billetera_digital(self, tipo: str = "apple_pay") -> dict:
        """
        Activa el flujo de pago con billetera.
        Corresponde a seleccionarBilleteraDigital() — CU30.
        """
        return {"tipo": tipo, "orden_id": self.orden_id, "iniciado": True}

    async def confirmar_pago_exitoso(self, wallet_token: str, tipo: str) -> dict:
        """
        Procesa el token de la billetera y confirma el pago.
        Corresponde a confirmarPagoExitoso() — CU30.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/payments/wallet",
                json={
                    "orden_id": self.orden_id,
                    "monto": self.total,
                    "wallet_token": wallet_token,
                    "tipo": tipo,
                },
            )
        return r.json()

    async def regresar_seleccion_metodo_pago(self) -> dict:
        """
        Cancela el flujo de billetera y regresa al selector.
        Corresponde a regresarSeleccionMetodoPago() — CU30.
        """
        return {"cancelado": True, "accion": "mostrar_selector_pago"}

    async def recibir_webhook(self, payload: dict) -> dict:
        """
        Recibe la confirmación de pago desde la pasarela.
        Corresponde a recibirWebhook(status) — CU32.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/payments/webhook",
                json=payload,
            )
        return r.json()


# ══════════════════════════════════════════════════════════
# TrackingScreen — s7-confirmacion.html
# CU14
# ══════════════════════════════════════════════════════════

class TrackingScreen:
    """
    Pantalla de confirmación y seguimiento del pedido.
    Corresponde a s7-confirmacion.html del Kiosk.

    Atributos del diagrama:
        numeroPedido: String
    """

    def __init__(self, orden_id: str, codigo_orden: str):
        self.numero_pedido = codigo_orden
        self.orden_id = orden_id

    async def cancelar_pedido(self, numero_pedido: str) -> dict:
        """
        El cliente intenta cancelar su pedido desde s7-confirmacion.html.
        Corresponde a cancelarPedido(numeroPedido) — CU14.
        """
        async with httpx.AsyncClient() as client:
            r = await client.delete(
                f"{BASE_URL}/customer/orders/{self.orden_id}"
            )
        resultado = r.json()
        if resultado.get("cancelada"):
            return await self.notificar_cancelacion_exitosa()
        return await self.mostrar_mensaje_no_cancelable()

    async def notificar_cancelacion_exitosa(self) -> dict:
        """
        Muestra confirmación de cancelación exitosa.
        Corresponde a notificarCancelacionExitosa() — CU14.
        """
        return {
            "cancelada": True,
            "mensaje": "Tu pedido ha sido cancelado exitosamente.",
        }

    async def mostrar_mensaje_no_cancelable(self) -> dict:
        """
        Informa que el pedido ya no puede cancelarse.
        Corresponde a mostrarMensajeNoCancelable() — CU14.
        """
        return {
            "cancelada": False,
            "mensaje": "Tu pedido ya está en preparación y no puede cancelarse.",
        }

    async def mostrar_mensaje_acudir_barra(self) -> dict:
        """
        Indica al cliente que debe acudir a la barra para cancelar.
        Corresponde a mostrarMensajeAcudirBarra() — CU14.
        """
        return {
            "cancelada": False,
            "mensaje": "Por favor acude a la barra para cancelar tu pedido.",
        }


# ══════════════════════════════════════════════════════════
# WaitingScreen — s8-espera.html
# CU69, CU43
# ══════════════════════════════════════════════════════════

class WaitingScreen:
    """
    Pantalla de espera mientras se prepara la orden.
    Corresponde a s8-espera.html del Kiosk.
    Integra el mini-juego (CU69) y detecta cuando la orden está lista (CU43).
    """

    def __init__(self, orden_id: str):
        self.orden_id = orden_id
        self._juego_activo: bool = False

    async def abrir_pantalla_espera(self) -> dict:
        """
        Inicializa s8-espera.html cuando la orden pasa a 'en preparación'.
        Corresponde a abrirPantallaEspera() — CU69.
        """
        estado = await self._verificar_estado_orden()
        return {
            "pantalla": "espera",
            "orden_id": self.orden_id,
            "estado": estado,
            "juego_disponible": True,
        }

    async def habilitar_boton_jugar(self) -> dict:
        """
        Habilita el botón de jugar en s8-espera.html.
        Corresponde a habilitarBotonJugar() — CU69.
        """
        return {"boton_jugar": True, "habilitado": True}

    async def presionar_jugar(self) -> dict:
        """
        El cliente toca el botón de jugar.
        Corresponde a presionarJugar() — CU69.
        """
        self._juego_activo = True
        return await self.iniciar_mini_juego()

    async def iniciar_mini_juego(self) -> dict:
        """
        Inicia el mini-juego desde s8-espera.html.
        Corresponde a iniciarMiniJuego() — CU69.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/customer/minigame/start")
        return r.json() if r.status_code == 200 else {}

    async def detectar_orden_en_preparacion(self) -> bool:
        """
        Verifica periódicamente si la orden está en preparación.
        Corresponde a detectarOrdenEnPreparacion() — CU69 (OrderController).
        """
        estado = await self._verificar_estado_orden()
        return estado in ("EnPreparacion", "ListaParaRecoger")

    async def _verificar_estado_orden(self) -> str:
        """Consulta el estado actual de la orden."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/production/orders/{self.orden_id}"
            )
        if r.status_code == 200:
            return r.json().get("estado", "")
        return ""


# ══════════════════════════════════════════════════════════
# LoginScreen — modal/sección en e1-login.html
# CU17
# ══════════════════════════════════════════════════════════

class LoginScreen:
    """
    Pantalla de inicio de sesión.
    Corresponde a e1-login.html del Employee (y modal del Kiosk).

    Atributos del diagrama:
        correo: String
        contraseña: String
    """

    def __init__(self):
        self.correo: str = ""
        self.contrasena: str = ""

    async def ingresar_credenciales(
        self, correo: str, contrasena: str
    ) -> dict:
        """
        El usuario ingresa sus credenciales.
        Corresponde a ingresarCredenciales(correo, contraseña) — CU17.
        """
        self.correo = correo
        self.contrasena = contrasena
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/auth/login",
                json={"correo": correo, "contrasena": contrasena},
            )
        if r.status_code == 200:
            return await self.mostrar_perfil(r.json())
        return await self.mostrar_credenciales_invalidas()

    async def mostrar_perfil(self, datos_sesion: dict) -> dict:
        """
        Muestra el perfil del usuario tras inicio de sesión exitoso.
        Corresponde a mostrarPerfil() — CU17.
        """
        return {"autenticado": True, "sesion": datos_sesion}

    async def mostrar_credenciales_invalidas(self) -> dict:
        """
        Muestra mensaje de error de credenciales.
        Corresponde a mostrarCredencialesInvalidas() — CU17.
        """
        return {
            "autenticado": False,
            "error": "Correo o contraseña incorrectos.",
        }


# ══════════════════════════════════════════════════════════
# RegisterScreen — modal del Kiosk
# CU16
# ══════════════════════════════════════════════════════════

class RegisterScreen:
    """
    Pantalla de registro de cuenta nueva.

    Atributos del diagrama:
        nombre: String
        correo: String
        contraseña: String
    """

    def __init__(self):
        self.nombre: str = ""
        self.correo: str = ""
        self.contrasena: str = ""

    async def seleccionar_registrarse(self) -> dict:
        """Abre el formulario de registro. CU16."""
        return {"pantalla": "registro", "activa": True}

    async def crear_cuenta(
        self, nombre: str, correo: str, contrasena: str,
        telefono: Optional[str] = None,
        fecha_cumpleanos: Optional[str] = None,
    ) -> dict:
        """
        Envía los datos de registro al backend.
        Corresponde a registrarUsuario() — CU16.
        """
        self.nombre = nombre
        self.correo = correo
        self.contrasena = contrasena
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/auth/register",
                json={
                    "nombre": nombre,
                    "correo": correo,
                    "contrasena": contrasena,
                    "telefono": telefono,
                    "fecha_cumpleanos": fecha_cumpleanos,
                },
            )
        if r.status_code == 201:
            return await self.mostrar_registro_exitoso()
        return await self.mostrar_correo_en_uso()

    async def mostrar_registro_exitoso(self) -> dict:
        """Corresponde a mostrarRegistroExitoso() — CU16."""
        return {"registrado": True, "mensaje": "¡Cuenta creada exitosamente!"}

    async def mostrar_correo_en_uso(self) -> dict:
        """Corresponde a mostrarCorreoEnUso() — CU16."""
        return {"registrado": False, "error": "El correo ya está en uso."}


# ══════════════════════════════════════════════════════════
# PasswordRecoveryScreen — modal del Kiosk
# CU18
# ══════════════════════════════════════════════════════════

class PasswordRecoveryScreen:
    """
    Pantalla de recuperación de contraseña.

    Atributos del diagrama:
        correo: String
    """

    def __init__(self):
        self.correo: str = ""

    async def solicitar_recuperacion(self, correo: str) -> dict:
        """
        Envía la solicitud de recuperación.
        Corresponde a solicitarRecuperacion(correo) — CU18.
        """
        self.correo = correo
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/auth/password-recovery",
                json={"correo": correo},
            )
        if r.status_code == 200:
            return await self.mostrar_mensaje_enviado()
        return await self.mostrar_error_correo()

    async def mostrar_mensaje_enviado(self) -> dict:
        """Corresponde a mostrarMensajeEnviado() — CU18."""
        return {
            "enviado": True,
            "mensaje": f"Se envió un enlace de recuperación a {self.correo}.",
        }

    async def mostrar_error_correo(self) -> dict:
        """Corresponde a mostrarErrorCorreo() — CU18."""
        return {"enviado": False, "error": "El correo no está registrado."}


# ══════════════════════════════════════════════════════════
# PromotionsScreen — sección del Kiosk
# CU15, CU73
# ══════════════════════════════════════════════════════════

class PromotionsScreen:
    """
    Pantalla de promociones vigentes.

    Atributos del diagrama:
        listaPromociones: List<Promocion>
    """

    def __init__(self):
        self.lista_promociones: list = []

    async def acceder_seccion_promociones(self) -> list:
        """
        El cliente abre la sección de promociones.
        Corresponde a accederSeccionPromociones() — CU15.
        """
        return await self.mostrar_promociones()

    async def mostrar_promociones(self) -> list:
        """
        Carga y retorna las promociones vigentes.
        Corresponde a mostrarPromociones(listaPromociones) — CU15.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/customer/promotions")
        if r.status_code == 200:
            self.lista_promociones = r.json()
        return self.lista_promociones

    async def mostrar_mensaje_sin_ofertas(self) -> dict:
        """
        Muestra mensaje cuando no hay promociones activas.
        Corresponde a mostrarMensajeSinOfertas() — CU15.
        """
        return {"sin_ofertas": True, "mensaje": "No hay promociones disponibles en este momento."}

    async def aplicar_qr(self, codigo_qr: str, orden_id: str) -> dict:
        """
        Aplica la promoción escaneada por QR.
        Corresponde a CU73 — Escanear código QR.
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/customer/promotions/qr",
                json={"codigo_qr": codigo_qr, "orden_id": orden_id},
            )
        return r.json()


# ══════════════════════════════════════════════════════════
# MobileApp — s6-pago.html (billetera) / s4-personalizar.html
# CU30
# ══════════════════════════════════════════════════════════

class MobileApp:
    """
    Componente de la app móvil embebido en las pantallas del Kiosk.
    Gestiona la billetera digital y notificaciones push.

    Atributos del diagrama: (ninguno propio)
    """

    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self._payment_module: Optional[PaymentModule] = None

    def seleccionar_billetera_digital(self, orden_id: str, total: float) -> PaymentModule:
        """
        Activa el módulo de billetera digital.
        Corresponde a seleccionarBilleteraDigital() — CU30.
        """
        self._payment_module = PaymentModule(orden_id, total)
        return self._payment_module

    async def confirmar_pago_exitoso(
        self, wallet_token: str, tipo: str = "apple_pay"
    ) -> dict:
        """
        Confirma el pago con biometría/billetera.
        Corresponde a confirmarPagoExitoso() — CU30.
        """
        if not self._payment_module:
            return {"error": "No hay módulo de pago activo."}
        return await self._payment_module.confirmar_pago_exitoso(wallet_token, tipo)

    async def regresar_seleccion_metodo_pago(self) -> dict:
        """
        Cancela la billetera y regresa al selector.
        Corresponde a regresarSeleccionMetodoPago() — CU30.
        """
        self._payment_module = None
        return {"cancelado": True}