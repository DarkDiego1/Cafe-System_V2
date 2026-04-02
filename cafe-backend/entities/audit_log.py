"""
entities/audit_log.py
Módulo 03 — Gestión y Administración (MAM)

Entidad de dominio: AuditLog
Casos de uso: CU65 — Ver registro de auditoría del sistema

Representa un evento registrado automáticamente cada vez que
un usuario realiza una acción relevante en el sistema.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Tipos de evento auditables
TIPOS_EVENTO = {
    "crear_ingrediente",
    "modificar_ingrediente",
    "eliminar_ingrediente",
    "ajuste_stock_manual",
    "entrada_mercancia",
    "registrar_merma",
    "crear_proveedor",
    "modificar_proveedor",
    "crear_empleado",
    "modificar_empleado",
    "cambiar_rol",
    "modificar_menu",
    "configurar_umbrales",
    "generar_reporte",
    "crear_orden_compra",
    "cambiar_estado_orden",
    "login",
    "logout",
}


@dataclass
class AuditLog:
    """
    Registro inmutable de una acción realizada en el sistema.
    Mapea contra la tabla `audit_logs` de PostgreSQL.
    """

    id: int
    tipo_evento: str                    # uno de TIPOS_EVENTO
    descripcion: str                    # texto legible del evento
    usuario_id: Optional[int]           # employee_id o user_id
    nombre_usuario: str                 # desnormalizado para lectura rápida
    entidad_afectada: Optional[str]     # nombre de la tabla/entidad
    entidad_id: Optional[str]           # ID del registro afectado
    datos_anteriores: Optional[dict]    # snapshot antes del cambio
    datos_nuevos: Optional[dict]        # snapshot después del cambio
    ip_origen: Optional[str]
    fecha: datetime = field(default_factory=datetime.now)

    # ── CU65: métodos del diagrama de secuencia ───────────────────────

    @classmethod
    def registrar_evento(
        cls,
        id: int,
        tipo_evento: str,
        descripcion: str,
        usuario_id: Optional[int] = None,
        nombre_usuario: str = "sistema",
        entidad_afectada: Optional[str] = None,
        entidad_id: Optional[str] = None,
        datos_anteriores: Optional[dict] = None,
        datos_nuevos: Optional[dict] = None,
        ip_origen: Optional[str] = None,
    ) -> "AuditLog":
        """
        Factory para crear un registro de auditoría.
        Corresponde a la acción de registro automático en cada operación sensible.
        """
        return cls(
            id=id,
            tipo_evento=tipo_evento,
            descripcion=descripcion,
            usuario_id=usuario_id,
            nombre_usuario=nombre_usuario,
            entidad_afectada=entidad_afectada,
            entidad_id=str(entidad_id) if entidad_id else None,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_origen=ip_origen,
        )

    def resumen(self) -> str:
        """
        Texto legible del evento para mostrar en la pantalla de auditoría.
        Corresponde a Mostrar_registros_auditoria() — CU65.
        """
        return (
            f"[{self.fecha.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"{self.tipo_evento.upper()} por {self.nombre_usuario}"
            f"{f' en {self.entidad_afectada}#{self.entidad_id}' if self.entidad_afectada else ''}"
            f": {self.descripcion}"
        )

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo_evento": self.tipo_evento,
            "descripcion": self.descripcion,
            "usuario_id": self.usuario_id,
            "nombre_usuario": self.nombre_usuario,
            "entidad_afectada": self.entidad_afectada,
            "entidad_id": self.entidad_id,
            "datos_anteriores": self.datos_anteriores,
            "datos_nuevos": self.datos_nuevos,
            "ip_origen": self.ip_origen,
            "fecha": self.fecha.isoformat(),
            "resumen": self.resumen(),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "AuditLog":
        import json
        def parse_json(val):
            if val is None:
                return None
            if isinstance(val, dict):
                return val
            try:
                return json.loads(val)
            except Exception:
                return None

        return cls(
            id=row["id"],
            tipo_evento=row["tipo_evento"],
            descripcion=row.get("descripcion", ""),
            usuario_id=row.get("usuario_id"),
            nombre_usuario=row.get("nombre_usuario", "sistema"),
            entidad_afectada=row.get("entidad_afectada"),
            entidad_id=row.get("entidad_id"),
            datos_anteriores=parse_json(row.get("datos_anteriores")),
            datos_nuevos=parse_json(row.get("datos_nuevos")),
            ip_origen=row.get("ip_origen"),
            fecha=row.get("fecha") or datetime.now(),
        )