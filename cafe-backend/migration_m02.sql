-- ============================================================
-- migration_m02_fix.sql
-- Adapta la tabla notifications existente al código del M02
-- ============================================================

-- notifications real:   usuario_id (uuid), fecha_creacion, payload
-- código espera:        orden_id,  user_id,  fecha_envio,   enviada

ALTER TABLE notifications
    ADD COLUMN IF NOT EXISTS orden_id   UUID REFERENCES orders(id),
    ADD COLUMN IF NOT EXISTS user_id    UUID REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS fecha_envio TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS enviada    BOOLEAN NOT NULL DEFAULT FALSE;

-- Poblar user_id desde usuario_id existente
UPDATE notifications SET user_id = usuario_id WHERE user_id IS NULL;

-- Poblar fecha_envio desde fecha_creacion existente
UPDATE notifications SET fecha_envio = fecha_creacion WHERE fecha_envio IS NULL;

-- Ampliar el CHECK de tipo para incluir 'push' e 'in_app'
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS chk_notif_tipo;
ALTER TABLE notifications
    ADD CONSTRAINT chk_notif_tipo CHECK (
        tipo IN (
            'push', 'email', 'sms', 'in_app',
            'OrdenLista', 'StockBajo', 'Cumpleanos',
            'Promocion', 'Recordatorio', 'Sistema'
        )
    );

-- Índices para las nuevas columnas
CREATE INDEX IF NOT EXISTS idx_notifications_orden
    ON notifications (orden_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_m02
    ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_fecha_envio
    ON notifications (fecha_envio DESC);

-- También actualizar el servicio de notification para usar
-- usuario_id en lugar de user_id al insertar (compatibilidad)
-- La vista v_notifications unifica ambas columnas
CREATE OR REPLACE VIEW v_notifications AS
SELECT
    id,
    COALESCE(user_id, usuario_id) AS user_id,
    usuario_id,
    orden_id,
    tipo,
    titulo,
    mensaje,
    enviada,
    leida,
    COALESCE(fecha_envio, fecha_creacion) AS fecha_envio,
    fecha_creacion,
    payload
FROM notifications;

COMMENT ON VIEW v_notifications IS
    'Vista unificada de notificaciones compatible con M01 y M02';

SELECT 'migration_m02_fix.sql aplicado correctamente ✅' AS resultado;