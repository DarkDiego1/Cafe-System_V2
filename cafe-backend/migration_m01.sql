-- ============================================================
-- migration_m01.sql
-- Módulo 01 — Experiencia del Cliente (CEM)
--
-- Tablas nuevas:
--   sessions, password_reset_tokens, coupons,
--   favorite_drinks, promotions
--
-- Columnas nuevas en tablas existentes:
--   users    → contrasena_hash, puntos_lealtad, fecha_cumpleanos,
--               preferencias_alimenticias, metodo_pago_defecto
--   orders   → transaccion_id, metodo_pago, cupon_codigo
--   drinks   → es_vegetariana, sin_lactosa, sin_cafeina
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. EXTENDER TABLA users
-- ────────────────────────────────────────────────────────────

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS contrasena_hash          VARCHAR(255),
    ADD COLUMN IF NOT EXISTS puntos_lealtad           INTEGER       NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS fecha_cumpleanos         DATE,
    ADD COLUMN IF NOT EXISTS preferencias_alimenticias JSONB        DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS metodo_pago_defecto      VARCHAR(50);

-- ────────────────────────────────────────────────────────────
-- 2. EXTENDER TABLA orders
-- ────────────────────────────────────────────────────────────

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS transaccion_id  VARCHAR(100),
    ADD COLUMN IF NOT EXISTS metodo_pago     VARCHAR(50),
    ADD COLUMN IF NOT EXISTS cupon_codigo    VARCHAR(50);

-- ────────────────────────────────────────────────────────────
-- 3. EXTENDER TABLA drinks con filtros alimenticios (CU66)
-- ────────────────────────────────────────────────────────────

ALTER TABLE drinks
    ADD COLUMN IF NOT EXISTS es_vegetariana BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sin_lactosa    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sin_cafeina    BOOLEAN NOT NULL DEFAULT FALSE;

-- ────────────────────────────────────────────────────────────
-- 4. SESSIONS — CU17
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    id              SERIAL PRIMARY KEY,
    user_id         UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(100) NOT NULL,
    expires_at      TIMESTAMPTZ  NOT NULL,
    fecha_creacion  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (token);
COMMENT ON TABLE sessions IS 'Sesiones activas de usuarios — CU17';

-- ────────────────────────────────────────────────────────────
-- 5. PASSWORD_RESET_TOKENS — CU18
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         SERIAL PRIMARY KEY,
    email      VARCHAR(150) NOT NULL,
    token      VARCHAR(100) NOT NULL,
    expires_at TIMESTAMPTZ  NOT NULL,
    usado      BOOLEAN      NOT NULL DEFAULT FALSE,
    UNIQUE (email)
);

COMMENT ON TABLE password_reset_tokens IS 'Tokens de recuperación de contraseña — CU18';

-- ────────────────────────────────────────────────────────────
-- 6. COUPONS — CU31, CU68, CU70, CU73
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS coupons (
    id                  SERIAL PRIMARY KEY,
    codigo              VARCHAR(50)    NOT NULL UNIQUE,
    descuento           NUMERIC(10,2)  NOT NULL,
    tipo_descuento      VARCHAR(20)    NOT NULL DEFAULT 'porcentaje'
                        CHECK (tipo_descuento IN ('porcentaje', 'monto_fijo')),
    valido              BOOLEAN        NOT NULL DEFAULT TRUE,
    fecha_inicio        TIMESTAMPTZ,
    fecha_fin           TIMESTAMPTZ,
    uso_maximo          INTEGER,
    usos_actuales       INTEGER        NOT NULL DEFAULT 0,
    solo_primera_compra BOOLEAN        NOT NULL DEFAULT FALSE,
    user_id             UUID           REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_coupons_codigo ON coupons (codigo);
CREATE INDEX IF NOT EXISTS idx_coupons_user   ON coupons (user_id);
COMMENT ON TABLE coupons IS 'Cupones de descuento — CU31, CU68, CU70, CU73';

-- ────────────────────────────────────────────────────────────
-- 7. FAVORITE_DRINKS — CU21
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS favorite_drinks (
    id              SERIAL PRIMARY KEY,
    cliente_id      UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bebida_id       INTEGER NOT NULL REFERENCES drinks(id),
    nombre          VARCHAR(100),
    fecha_guardado  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cliente_id, bebida_id)
);

COMMENT ON TABLE favorite_drinks IS 'Recetas favoritas del cliente — CU21';

-- ────────────────────────────────────────────────────────────
-- 8. PROMOTIONS — CU15, CU73
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS promotions (
    id          SERIAL PRIMARY KEY,
    titulo      VARCHAR(150)  NOT NULL,
    descripcion TEXT,
    imagen_url  VARCHAR(500),
    descuento   NUMERIC(5,2)  NOT NULL DEFAULT 0,
    fecha_inicio TIMESTAMPTZ  NOT NULL,
    fecha_fin    TIMESTAMPTZ  NOT NULL,
    activa       BOOLEAN      NOT NULL DEFAULT TRUE,
    codigo_qr    VARCHAR(100) UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_promotions_fechas
    ON promotions (fecha_inicio, fecha_fin)
    WHERE activa = TRUE;

COMMENT ON TABLE promotions IS 'Promociones vigentes — CU15, CU73';

SELECT 'migration_m01.sql aplicado correctamente ✅' AS resultado;