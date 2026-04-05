"""
routers/customer.py
Módulo 01 — Experiencia del Cliente (CEM)

Router principal del M01 — todos los endpoints del cliente.
Cubre: CU01–CU35, CU66–CU75
"""

from fastapi import APIRouter, Query, Header
from typing import Optional
from pydantic import BaseModel, Field

from controllers.m01_controllers import (
    AuthController, MenuRouter, DrinkController,
    PricingController, OrderController, PaymentController,
    WalletPaymentController, CouponController,
    PromotionsController, VisualizationController,
)
from services.experience_service import RecommendationEngine, MiniGame
from services.auth_service import AuthService

router = APIRouter()

# Instancias de controladores
auth_ctrl   = AuthController()
menu_ctrl   = MenuRouter()
drink_ctrl  = DrinkController()
price_ctrl  = PricingController()
order_ctrl  = OrderController()
pay_ctrl    = PaymentController()
wallet_ctrl = WalletPaymentController()
coupon_ctrl = CouponController()
promo_ctrl  = PromotionsController()
viz_ctrl    = VisualizationController()
rec_engine  = RecommendationEngine()
mini_game   = MiniGame()


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterSchema(BaseModel):
    nombre: str = Field(..., min_length=2)
    correo: str = Field(..., min_length=5)
    contrasena: str = Field(..., min_length=6)
    telefono: Optional[str] = None
    fecha_cumpleanos: Optional[str] = None   # YYYY-MM-DD

class LoginSchema(BaseModel):
    correo: str
    contrasena: str

class PasswordResetRequestSchema(BaseModel):
    correo: str

class PasswordResetSchema(BaseModel):
    token: str
    nueva_contrasena: str = Field(..., min_length=6)

class ProfileUpdateSchema(BaseModel):
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    fecha_cumpleanos: Optional[str] = None
    preferencias_alimenticias: Optional[list] = None

class PricingSchema(BaseModel):
    bebida_id: int
    tamano: str
    ingredientes: list = Field(default_factory=list)

class OrderItemSchema(BaseModel):
    bebida_id: int
    tamano: str
    cantidad: int = 1
    precio_base: float
    precio_final: float
    notas_item: Optional[str] = None

class CreateOrderSchema(BaseModel):
    cliente_id: str
    items: list[OrderItemSchema]
    notas_generales: Optional[str] = None
    cupon_codigo: Optional[str] = None

class PaymentCardSchema(BaseModel):
    orden_id: str
    monto: float
    token_tarjeta: str

class PaymentWalletSchema(BaseModel):
    orden_id: str
    monto: float
    wallet_token: str
    tipo: str = "apple_pay"

class WebhookSchema(BaseModel):
    orden_id: str
    transaccion_id: str
    status: str

class PropinaSchema(BaseModel):
    monto: float = Field(..., ge=0)

class CouponSchema(BaseModel):
    codigo: str

class QRSchema(BaseModel):
    codigo_qr: str
    orden_id: str

class RenderSchema(BaseModel):
    bebida_id: int
    tamano: str = "mediano"
    ingredientes: list = Field(default_factory=list)

class FavoritaSchema(BaseModel):
    bebida_id: int
    nombre: str


# ══════════════════════════════════════════════════════════
# AUTH — CU16, CU17, CU18, CU19
# ══════════════════════════════════════════════════════════

@router.post("/auth/register", status_code=201)
async def register(data: RegisterSchema):
    """CU16 — Registrar nueva cuenta de cliente."""
    return await auth_ctrl.registrar_usuario(**data.model_dump())

@router.post("/auth/login")
async def login(data: LoginSchema):
    """CU17 — Iniciar sesión."""
    return await auth_ctrl.iniciar_sesion(data.correo, data.contrasena)

@router.post("/auth/logout")
async def logout(x_user_id: str = Header(...)):
    """CU17 — Cerrar sesión."""
    return await auth_ctrl.cerrar_sesion(x_user_id)

@router.post("/auth/password-recovery")
async def request_password_recovery(data: PasswordResetRequestSchema):
    """CU18 — Solicitar enlace de recuperación de contraseña."""
    return await auth_ctrl.enviar_enlace_recuperacion(data.correo)

@router.post("/auth/password-reset")
async def reset_password(data: PasswordResetSchema):
    """CU18 — Restablecer contraseña con token."""
    return await auth_ctrl.restablecer_contrasena(data.token, data.nueva_contrasena)

@router.patch("/auth/profile/{user_id}")
async def update_profile(user_id: str, data: ProfileUpdateSchema):
    """CU19 — Actualizar perfil del usuario."""
    campos = data.model_dump(exclude_none=True)
    return await auth_ctrl.actualizar_perfil(user_id, campos)


# ══════════════════════════════════════════════════════════
# MENÚ — CU01, CU20
# ══════════════════════════════════════════════════════════

@router.get("/menu/categories")
async def get_categories():
    """CU01 — Categorías del menú."""
    return await menu_ctrl.get_categorias()

@router.get("/menu/categories/{categoria_id}/drinks")
async def get_drinks_by_category(
    categoria_id: int,
    vegetariano: Optional[bool] = Query(None),
    sin_lactosa: Optional[bool] = Query(None),
    sin_cafeina: Optional[bool] = Query(None),
):
    """CU01/CU66 — Bebidas de una categoría con filtros alimenticios."""
    filtros = {
        "vegetariano": vegetariano,
        "sin_lactosa": sin_lactosa,
        "sin_cafeina": sin_cafeina,
    }
    return await menu_ctrl.get_bebidas(categoria_id, filtros)

@router.get("/menu/full")
async def get_full_menu():
    """CU20 — Menú completo con todas las categorías y bebidas."""
    return await menu_ctrl.get_menu_completo()


# ══════════════════════════════════════════════════════════
# BEBIDAS — CU02, CU03, CU04, CU06, CU08, CU11
# ══════════════════════════════════════════════════════════

@router.get("/drinks/{drink_id}")
async def get_drink_detail(drink_id: int):
    """CU02 — Detalle de bebida con ingredientes."""
    return await drink_ctrl.get_detalle_bebida(drink_id)

@router.get("/drinks/{drink_id}/price/{tamano}")
async def get_drink_price(drink_id: int, tamano: str):
    """CU03 — Precio según tamaño seleccionado."""
    return await drink_ctrl.actualizar_precio_base(drink_id, tamano)

@router.get("/drinks/{drink_id}/availability")
async def check_availability(drink_id: int):
    """CU11 — Verificar disponibilidad de ingredientes."""
    return await drink_ctrl.validar_limite_receta(drink_id)

@router.post("/drinks/render")
async def render_drink(data: RenderSchema):
    """CU06 — Visualización 3D de la bebida personalizada."""
    return viz_ctrl.solicitar_render(data.model_dump())

@router.get("/drinks/{drink_id}/suggestions")
async def get_suggestions(
    drink_id: int, cliente_id: Optional[str] = Query(None)
):
    """CU08 — Sugerencias de combinaciones."""
    return await rec_engine.recomendar_combinaciones(drink_id, cliente_id)


# ══════════════════════════════════════════════════════════
# PRECIO EN TIEMPO REAL — CU05
# ══════════════════════════════════════════════════════════

@router.post("/pricing/calculate")
async def calculate_price(data: PricingSchema):
    """CU05 — Calcular precio en tiempo real con personalizaciones."""
    return await price_ctrl.recalcular_total(
        data.bebida_id, data.tamano, data.ingredientes
    )


# ══════════════════════════════════════════════════════════
# ÓRDENES — CU12, CU14, CU21, CU22, CU23
# ══════════════════════════════════════════════════════════

@router.post("/orders", status_code=201)
async def create_order(data: CreateOrderSchema):
    """CU12 — Confirmar y crear pedido."""
    return await order_ctrl.crear_orden(
        cliente_id=data.cliente_id,
        items=[i.model_dump() for i in data.items],
        notas_generales=data.notas_generales,
        cupon_codigo=data.cupon_codigo,
    )

@router.delete("/orders/{orden_id}")
async def cancel_order(orden_id: str):
    """CU14 — Cancelar pedido."""
    return await order_ctrl.solicitar_cancelacion(orden_id)

@router.get("/orders/history/{cliente_id}")
async def get_order_history(cliente_id: str):
    """CU22 — Historial de pedidos del cliente."""
    return await order_ctrl.get_historial(cliente_id)

@router.post("/orders/{orden_id}/reorder")
async def reorder(orden_id: str, x_user_id: str = Header(...)):
    """CU23 — Reordenar con un clic."""
    return await order_ctrl.reordenar(orden_id, x_user_id)

@router.get("/orders/favorites/{cliente_id}")
async def get_favorites(cliente_id: str):
    """CU21 — Ver bebidas favoritas."""
    return await order_ctrl.get_favoritas(cliente_id)

@router.post("/orders/favorites/{cliente_id}")
async def save_favorite(cliente_id: str, data: FavoritaSchema):
    """CU21 — Guardar bebida favorita."""
    return await order_ctrl.guardar_favorita(cliente_id, data.bebida_id, data.nombre)


# ══════════════════════════════════════════════════════════
# PAGOS — CU29, CU30, CU32, CU33, CU34, CU35
# ══════════════════════════════════════════════════════════

@router.post("/payments/card")
async def pay_with_card(data: PaymentCardSchema):
    """CU29 — Pago con tarjeta."""
    return await pay_ctrl.procesar_pago_tarjeta(
        data.orden_id, data.monto, data.token_tarjeta
    )

@router.post("/payments/wallet")
async def pay_with_wallet(data: PaymentWalletSchema):
    """CU30 — Pago con billetera digital."""
    return await wallet_ctrl.procesar_pago_billetera(
        data.orden_id, data.monto, data.wallet_token, data.tipo
    )

@router.post("/payments/webhook")
async def payment_webhook(data: WebhookSchema):
    """CU32 — Webhook de confirmación de pago."""
    return await pay_ctrl.actualizar_estado_pedido(data.model_dump())

@router.post("/payments/{orden_id}/receipt")
async def send_receipt(orden_id: str, correo: str = Query(...)):
    """CU13/CU34 — Enviar recibo por correo."""
    return await pay_ctrl.generar_recibo_pdf(orden_id, correo)

@router.post("/payments/{orden_id}/tip")
async def add_tip(orden_id: str, data: PropinaSchema):
    """CU35 — Dejar propina digital."""
    return await pay_ctrl.dejar_propina(orden_id, data.monto)


# ══════════════════════════════════════════════════════════
# CUPONES — CU31, CU68, CU70, CU73
# ══════════════════════════════════════════════════════════

@router.post("/coupons/validate")
async def validate_coupon(
    data: CouponSchema, x_user_id: Optional[str] = Header(None)
):
    """CU31 — Validar código de cupón."""
    return await coupon_ctrl.validar_cupon(data.codigo, x_user_id)

@router.post("/coupons/{orden_id}/apply")
async def apply_coupon(orden_id: str, data: CouponSchema):
    """CU31 — Aplicar cupón a una orden."""
    return await coupon_ctrl.aplicar_cupon(orden_id, data.codigo)

@router.post("/loyalty/{user_id}/redeem")
async def redeem_points(user_id: str, puntos: int = Query(..., gt=0)):
    """CU68 — Canjear puntos por recompensas."""
    return await coupon_ctrl.canjear_puntos(user_id, puntos)

@router.post("/loyalty/{user_id}/birthday-coupon")
async def birthday_coupon(user_id: str):
    """CU70 — Generar cupón de cumpleaños."""
    return await coupon_ctrl.generar_cupon_cumpleanos(user_id)


# ══════════════════════════════════════════════════════════
# PROMOCIONES — CU15, CU73
# ══════════════════════════════════════════════════════════

@router.get("/promotions")
async def get_promotions():
    """CU15 — Ver promociones vigentes."""
    return await promo_ctrl.get_promociones_vigentes()

@router.post("/promotions/qr")
async def apply_qr_promotion(data: QRSchema):
    """CU73 — Escanear código QR para aplicar promoción."""
    return await promo_ctrl.aplicar_qr(data.codigo_qr, data.orden_id)


# ══════════════════════════════════════════════════════════
# EXPERIENCIA MEJORADA — CU69, CU71, CU74, CU75
# ══════════════════════════════════════════════════════════

@router.get("/minigame/start")
async def start_minigame():
    """CU69 — Iniciar mini-juego mientras espera."""
    return mini_game.ejecutar_juego_ligero()

@router.post("/recommendations/mood")
async def mood_recommendations(estado_animo: str = Query(...)):
    """CU71 — Recomendaciones por estado de ánimo (mood selector)."""
    return await rec_engine.mood_selector(estado_animo)

@router.get("/recommendations/weather")
async def weather_recommendations(
    temperatura: float = Query(...),
    codigo_postal: Optional[str] = Query(None),
):
    """CU74/CU75 — Recomendaciones basadas en temperatura/clima."""
    return await rec_engine.recomendar_por_clima(temperatura, codigo_postal)