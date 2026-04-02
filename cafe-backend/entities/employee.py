"""
entities/employee.py
Módulo 03 — Gestión y Administración (MAM)

Entidad de dominio: Employee
Casos de uso: CU58 — Gestionar empleados, CU59 — Asignar permisos
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

ROLES_VALIDOS = {"gerente", "barista", "empleado"}

# Mapa de permisos por rol
PERMISOS_POR_ROL: dict[str, list[str]] = {
    "gerente": [
        "ver_inventario", "editar_inventario", "ver_reportes",
        "editar_menu", "gestionar_empleados", "ver_auditoria",
        "configurar_umbrales", "gestionar_proveedores",
    ],
    "barista": [
        "ver_inventario", "registrar_merma", "ver_ordenes",
        "actualizar_estado_orden",
    ],
    "empleado": [
        "ver_inventario", "registrar_merma", "ver_ordenes",
        "registrar_entrada_mercancia",
    ],
}


@dataclass
class Employee:
    """
    Representa un empleado interno del sistema Dominia.
    Mapea contra la tabla `employees` de PostgreSQL.
    """

    id: int
    nombre_completo: str
    usuario: str
    rol: str                            # gerente | barista | empleado
    activo: bool = True
    email: Optional[str] = None
    telefono: Optional[str] = None
    fecha_contratacion: datetime = field(default_factory=datetime.now)
    # contrasena_hash no se incluye en representación por seguridad

    # ── CU58: validaciones de dominio ─────────────────────────────────

    def validar_rol(self, rol: str) -> bool:
        """Verifica que el rol sea uno de los roles válidos del sistema."""
        return rol in ROLES_VALIDOS

    def activar(self) -> None:
        """Reactiva la cuenta del empleado."""
        self.activo = True

    def desactivar(self) -> None:
        """Desactiva la cuenta sin eliminarla (baja lógica)."""
        self.activo = False

    # ── CU59: asignar permisos (cambio de rol) ────────────────────────

    def asignar_rol(self, nuevo_rol: str) -> None:
        """
        Cambia el rol del empleado, lo que modifica sus permisos de acceso.
        Corresponde a asignarPermisos() — diagrama CU59.

        Raises:
            ValueError: Si el rol no es válido.
        """
        if not self.validar_rol(nuevo_rol):
            raise ValueError(
                f"Rol '{nuevo_rol}' no válido. Opciones: {', '.join(ROLES_VALIDOS)}"
            )
        self.rol = nuevo_rol

    def obtener_permisos(self) -> list[str]:
        """
        Retorna la lista de permisos asociados al rol actual.
        Corresponde a obtenerPermisos() — diagrama CU59.
        """
        return PERMISOS_POR_ROL.get(self.rol, [])

    def tiene_permiso(self, permiso: str) -> bool:
        """
        Verifica si el empleado tiene un permiso específico.
        Usado por middleware de autorización.
        """
        return permiso in self.obtener_permisos()

    # ── Serialización ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre_completo": self.nombre_completo,
            "usuario": self.usuario,
            "rol": self.rol,
            "activo": self.activo,
            "email": self.email,
            "telefono": self.telefono,
            "fecha_contratacion": self.fecha_contratacion.isoformat(),
            "permisos": self.obtener_permisos(),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Employee":
        return cls(
            id=row["id"],
            nombre_completo=row["nombre_completo"],
            usuario=row["usuario"],
            rol=row.get("rol", "empleado"),
            activo=row.get("activo", True),
            email=row.get("email"),
            telefono=row.get("telefono"),
            fecha_contratacion=row.get("fecha_contratacion") or datetime.now(),
        )