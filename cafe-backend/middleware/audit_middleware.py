"""
middleware/audit_middleware.py
Módulo 03 — Gestión y Administración (MAM)

Middleware FastAPI que registra automáticamente eventos de auditoría
en cada petición a endpoints sensibles del Módulo 03.

Implementa el patrón de auditoría transversal requerido por CU65.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import database

# Rutas que deben auditarse automáticamente
# formato: (método_HTTP, prefijo_ruta) → tipo_evento
RUTAS_AUDITABLES: dict[tuple[str, str], str] = {
    ("POST",   "/api/inventory/ingredients"):          "crear_ingrediente",
    ("PATCH",  "/api/inventory/ingredients/"):         "modificar_ingrediente",
    ("PUT",    "/api/inventory/ingredients/"):         "ajuste_stock_manual",
    ("POST",   "/api/inventory/ingredients/waste"):    "registrar_merma",
    ("POST",   "/api/inventory/ingredients/"):         "entrada_mercancia",
    ("POST",   "/api/suppliers"):                      "crear_proveedor",
    ("PATCH",  "/api/suppliers/"):                     "modificar_proveedor",
    ("POST",   "/api/inventory/purchase-orders"):      "crear_orden_compra",
    ("PATCH",  "/api/inventory/purchase-orders/"):     "cambiar_estado_orden",
    ("POST",   "/api/admin/employees"):                "crear_empleado",
    ("PATCH",  "/api/admin/employees/"):               "modificar_empleado",
    ("PATCH",  "/api/admin/employees/role"):           "cambiar_rol",
    ("PATCH",  "/api/admin/menu/drinks/"):             "modificar_menu",
    ("PUT",    "/api/admin/thresholds"):               "configurar_umbrales",
    ("GET",    "/api/reports/"):                       "generar_reporte",
}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware que intercepta respuestas exitosas (2xx) en rutas
    auditables y persiste un registro en `audit_logs`.

    Solo registra cuando la respuesta es exitosa para evitar
    ruido de intentos fallidos (esos se manejan con logs de error).
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Solo auditar respuestas exitosas en métodos mutantes
        if response.status_code in range(200, 300) and request.method in (
            "POST", "PUT", "PATCH", "DELETE"
        ):
            tipo_evento = self._detectar_tipo_evento(request)
            if tipo_evento:
                await self._registrar(request, response, tipo_evento)

        return response

    def _detectar_tipo_evento(self, request: Request) -> str | None:
        """Mapea método + ruta a un tipo_evento de auditoría."""
        path = request.url.path
        method = request.method

        for (m, prefijo), evento in RUTAS_AUDITABLES.items():
            if method == m and path.startswith(prefijo):
                return evento
        return None

    async def _registrar(
        self, request: Request, response: Response, tipo_evento: str
    ) -> None:
        """Persiste el registro de auditoría de forma no bloqueante."""
        try:
            db = await database.get_db()
            # Extraer usuario del header Authorization si existe
            usuario_id = None
            nombre_usuario = "sistema"
            auth = request.headers.get("X-Employee-ID")
            auth_nombre = request.headers.get("X-Employee-Name")
            if auth:
                try:
                    usuario_id = int(auth)
                except ValueError:
                    pass
            if auth_nombre:
                nombre_usuario = auth_nombre

            ip_origen = request.client.host if request.client else None

            await db.execute("""
                INSERT INTO audit_logs
                    (tipo_evento, descripcion, usuario_id, nombre_usuario,
                     entidad_afectada, ip_origen, fecha)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """,
                tipo_evento,
                f"{request.method} {request.url.path} → {response.status_code}",
                usuario_id,
                nombre_usuario,
                request.url.path,
                ip_origen,
            )
        except Exception:
            # El fallo de auditoría no debe interrumpir la respuesta al cliente
            pass