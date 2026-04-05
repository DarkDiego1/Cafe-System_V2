"""
services/auth_service.py
Módulo 01 — Experiencia del Cliente (CEM)
CU16, CU17, CU18, CU19
"""

import hashlib
import secrets
from datetime import datetime, timedelta, date
from typing import Optional

import database
from entities.user import User


class AuthService:

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _verificar_password(self, password: str, *hashes: str) -> bool:
        h = self._hash_password(password)
        return any(h == x for x in hashes if x)

    # ── CU16 ─────────────────────────────────────────────────────────

    async def verificar_correo_disponible(self, correo: str) -> bool:
        db = await database.get_db()
        return await db.fetchval(
            "SELECT id FROM users WHERE LOWER(email) = LOWER($1)", correo
        ) is None

    async def crear_cuenta(
        self, nombre: str, correo: str, contrasena: str,
        telefono: Optional[str] = None,
        fecha_cumpleanos: Optional[str] = None,
    ) -> User:
        db = await database.get_db()
        if not await self.verificar_correo_disponible(correo):
            raise ValueError(f"El correo '{correo}' ya está en uso.")

        hash_pw  = self._hash_password(contrasena)
        fecha_nac = None
        if fecha_cumpleanos:
            try:
                fecha_nac = datetime.strptime(fecha_cumpleanos, "%Y-%m-%d").date()
            except ValueError:
                pass

        row = await db.fetchrow("""
            INSERT INTO users
                (nombre_completo, email, password_hash, contrasena_hash,
                 rol, fecha_nacimiento, fecha_cumpleanos,
                 puntos_lealtad, activo, fecha_creacion)
            VALUES ($1, $2, $3, $3, 'Cliente', $4, $4, 0, TRUE, NOW())
            RETURNING *
        """, nombre, correo.lower(), hash_pw, fecha_nac)

        return User.from_db_row(dict(row))

    # ── CU17 ─────────────────────────────────────────────────────────

    async def validar_credenciales(self, correo: str, contrasena: str) -> Optional[User]:
        db  = await database.get_db()
        row = await db.fetchrow(
            "SELECT * FROM users WHERE LOWER(email) = LOWER($1) AND activo = TRUE",
            correo,
        )
        if not row:
            return None
        if not self._verificar_password(
            contrasena,
            row.get("password_hash", ""),
            row.get("contrasena_hash", ""),
        ):
            return None
        return User.from_db_row(dict(row))

    async def crear_sesion(self, user_id: str) -> dict:
        db         = await database.get_db()
        token      = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=30)
        await db.execute("""
            INSERT INTO sessions (user_id, token, expires_at, fecha_creacion)
            VALUES ($1::uuid, $2, $3, NOW())
            ON CONFLICT (user_id) DO UPDATE
               SET token = EXCLUDED.token, expires_at = EXCLUDED.expires_at
        """, user_id, token, expires_at)
        return {"access_token": token, "user_id": user_id,
                "expires_at": expires_at.isoformat()}

    async def iniciar_sesion(self, correo: str, contrasena: str) -> dict:
        user = await self.validar_credenciales(correo, contrasena)
        if not user:
            raise ValueError("Correo o contraseña incorrectos.")
        sesion = await self.crear_sesion(user.id)
        return {"usuario": user.to_dict(), "sesion": sesion}

    # ── CU18 ─────────────────────────────────────────────────────────

    async def verificar_correo_existente(self, correo: str) -> bool:
        db = await database.get_db()
        return await db.fetchval(
            "SELECT id FROM users WHERE LOWER(email) = LOWER($1) AND activo = TRUE",
            correo,
        ) is not None

    async def generar_enlace_recuperacion(self, correo: str) -> str:
        db    = await database.get_db()
        token = secrets.token_urlsafe(32)
        exp   = datetime.now() + timedelta(hours=2)
        await db.execute("""
            INSERT INTO password_reset_tokens (email, token, expires_at, usado)
            VALUES ($1, $2, $3, FALSE)
            ON CONFLICT (email) DO UPDATE
               SET token = EXCLUDED.token,
                   expires_at = EXCLUDED.expires_at,
                   usado = FALSE
        """, correo.lower(), token, exp)
        return token

    async def restablecer_contrasena(self, token: str, nueva: str) -> bool:
        db  = await database.get_db()
        row = await db.fetchrow("""
            SELECT email FROM password_reset_tokens
            WHERE token = $1 AND expires_at > NOW() AND usado = FALSE
        """, token)
        if not row:
            return False
        h = self._hash_password(nueva)
        async with db.transaction():
            await db.execute(
                "UPDATE users SET password_hash=$2, contrasena_hash=$2 "
                "WHERE LOWER(email)=LOWER($1)",
                row["email"], h,
            )
            await db.execute(
                "UPDATE password_reset_tokens SET usado=TRUE WHERE token=$1", token
            )
        return True

    # ── CU19 ─────────────────────────────────────────────────────────

    async def actualizar_perfil(self, user_id: str, campos: dict) -> User:
        db = await database.get_db()
        if "fecha_cumpleanos" in campos:
            campos["fecha_nacimiento"] = campos["fecha_cumpleanos"]
        set_clauses = ", ".join(f"{k}=${i+2}" for i, k in enumerate(campos))
        row = await db.fetchrow(
            f"UPDATE users SET {set_clauses} WHERE id=$1::uuid RETURNING *",
            user_id, *list(campos.values()),
        )
        if not row:
            raise KeyError(f"Usuario {user_id} no encontrado.")
        return User.from_db_row(dict(row))

    async def obtener_usuario(self, user_id: str) -> User:
        db  = await database.get_db()
        row = await db.fetchrow("SELECT * FROM users WHERE id=$1::uuid", user_id)
        if not row:
            raise KeyError(f"Usuario {user_id} no encontrado.")
        return User.from_db_row(dict(row))

    async def cerrar_sesion(self, user_id: str) -> None:
        db = await database.get_db()
        await db.execute("DELETE FROM sessions WHERE user_id=$1::uuid", user_id)