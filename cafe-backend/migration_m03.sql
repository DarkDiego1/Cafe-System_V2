-- ============================================================
-- migration_m03_fix.sql
-- Corrección de columnas para adaptar tablas existentes
-- a la estructura que espera el código Python del Módulo 03
-- ============================================================
-- Ejecutar desde: cafe-backend/
-- Comando:
--   $env:PGPASSWORD = "Darklink1!"
--   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -U postgres -d Cafe_Nuevos_Horizontes -f migration_m03_fix.sql
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- 1. SUPPLIERS
--    Real:   nombre_empresa, fecha_creacion
--    Código: nombre,         fecha_registro
-- ────────────────────────────────────────────────────────────

-- Añadir columna `nombre` como alias de `nombre_empresa`
ALTER TABLE suppliers
    ADD COLUMN IF NOT EXISTS nombre VARCHAR(150);

-- Poblarla con los datos existentes
UPDATE suppliers SET nombre = nombre_empresa WHERE nombre IS NULL;

-- Hacerla NOT NULL y mantener sincronía con nombre_empresa
ALTER TABLE suppliers ALTER COLUMN nombre SET NOT NULL;

-- Añadir columna `notas` que el código usa
ALTER TABLE suppliers
    ADD COLUMN IF NOT EXISTS notas TEXT;

-- Añadir columna `fecha_registro` que el código devuelve
ALTER TABLE suppliers
    ADD COLUMN IF NOT EXISTS fecha_registro TIMESTAMPTZ DEFAULT NOW();

UPDATE suppliers SET fecha_registro = fecha_creacion WHERE fecha_registro IS NULL;

-- Índice único sobre nombre (el código valida duplicados por nombre)
CREATE UNIQUE INDEX IF NOT EXISTS uq_suppliers_nombre
    ON suppliers (LOWER(nombre));

-- ────────────────────────────────────────────────────────────
-- 2. PURCHASE_ORDER_ITEMS
--    Real:   orden_compra_id, cantidad_solicitada
--    Código: orden_id,        cantidad
-- ────────────────────────────────────────────────────────────

ALTER TABLE purchase_order_items
    ADD COLUMN IF NOT EXISTS orden_id INTEGER
        REFERENCES purchase_orders(id) ON DELETE CASCADE;

-- Poblar con los datos existentes
UPDATE purchase_order_items
SET orden_id = orden_compra_id
WHERE orden_id IS NULL;

-- Añadir columna `cantidad` que el código inserta
ALTER TABLE purchase_order_items
    ADD COLUMN IF NOT EXISTS cantidad NUMERIC(12,3);

UPDATE purchase_order_items
SET cantidad = cantidad_solicitada
WHERE cantidad IS NULL;

-- Índice para búsquedas por orden
CREATE INDEX IF NOT EXISTS idx_poi_orden
    ON purchase_order_items (orden_id);

-- ────────────────────────────────────────────────────────────
-- 3. EMPLOYEES
--    Real:   usuario_id (uuid FK a users), cargo
--    Código: usuario (varchar), rol, nombre_completo, contrasena_hash
--
--    La tabla real vincula a users mediante usuario_id.
--    Añadimos las columnas que el código necesita leer/escribir.
-- ────────────────────────────────────────────────────────────

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS nombre_completo VARCHAR(150);

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS usuario VARCHAR(60);

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS contrasena_hash VARCHAR(255);

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS rol VARCHAR(20) DEFAULT 'empleado'
        CHECK (rol IN ('gerente', 'barista', 'empleado'));

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS email VARCHAR(150);

ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS telefono VARCHAR(20);

-- Poblar nombre_completo y rol desde datos existentes si es posible
-- (cargo se mapea a rol como aproximación)
UPDATE employees
SET rol = CASE
    WHEN LOWER(cargo) LIKE '%gerente%' OR LOWER(cargo) LIKE '%manager%' THEN 'gerente'
    WHEN LOWER(cargo) LIKE '%barista%' THEN 'barista'
    ELSE 'empleado'
END
WHERE rol IS NULL OR rol = 'empleado';

UPDATE employees
SET nombre_completo = cargo
WHERE nombre_completo IS NULL;

-- Índice sobre usuario (para validación de duplicados)
CREATE UNIQUE INDEX IF NOT EXISTS uq_employees_usuario_str
    ON employees (LOWER(usuario))
    WHERE usuario IS NOT NULL;

-- ────────────────────────────────────────────────────────────
-- 4. WASTE_LOGS
--    Real:   empleado_id (uuid), motivo (VARCHAR 30 con CHECK),
--            descripcion
--    Código: registrado_por (integer FK a employees)
-- ────────────────────────────────────────────────────────────

-- Añadir columna registrado_por que el código escribe/lee
ALTER TABLE waste_logs
    ADD COLUMN IF NOT EXISTS registrado_por INTEGER
        REFERENCES employees(id);

-- Ampliar motivo a 255 chars (el código permite texto libre)
-- Primero eliminamos el CHECK restrictivo y ampliamos
ALTER TABLE waste_logs DROP CONSTRAINT IF EXISTS chk_wl_motivo;

ALTER TABLE waste_logs
    ALTER COLUMN motivo TYPE VARCHAR(255);

-- ────────────────────────────────────────────────────────────
-- 5. AUDIT_LOGS
--    Real:   entidad, accion, valores_anteriores, valores_nuevos,
--            ip_address, usuario_id (uuid)
--    Código: tipo_evento, descripcion, datos_anteriores,
--            datos_nuevos, ip_origen, nombre_usuario,
--            entidad_afectada, entidad_id
-- ────────────────────────────────────────────────────────────

-- Añadir columnas que el código inserta
ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS tipo_evento VARCHAR(50);

ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS descripcion TEXT DEFAULT '';

ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS nombre_usuario VARCHAR(150) DEFAULT 'sistema';

ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS entidad_afectada VARCHAR(100);

ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS datos_anteriores JSONB;

ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS datos_nuevos JSONB;

ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS ip_origen VARCHAR(45);

-- Poblar tipo_evento desde accion existente para registros históricos
UPDATE audit_logs
SET tipo_evento = LOWER(accion),
    entidad_afectada = entidad
WHERE tipo_evento IS NULL;

-- Índices para las nuevas columnas
CREATE INDEX IF NOT EXISTS idx_audit_tipo_evento
    ON audit_logs (tipo_evento);

CREATE INDEX IF NOT EXISTS idx_audit_entidad_afectada
    ON audit_logs (entidad_afectada, entidad_id);

-- ────────────────────────────────────────────────────────────
-- 6. INGREDIENT_SUPPLIERS
--    Verificar que la tabla tenga columna `principal`
-- ────────────────────────────────────────────────────────────

ALTER TABLE ingredient_suppliers
    ADD COLUMN IF NOT EXISTS principal BOOLEAN NOT NULL DEFAULT FALSE;

-- ────────────────────────────────────────────────────────────
-- 7. VISTAS corregidas con los nombres reales de columnas
-- ────────────────────────────────────────────────────────────

-- Vista inventario con alertas (usa nombre real: nombre_empresa → nombre)
CREATE OR REPLACE VIEW v_inventory_alerts AS
SELECT
    i.id,
    i.nombre,
    i.categoria,
    i.unidad_medida,
    i.stock_actual,
    i.stock_minimo,
    i.stock_optimo,
    i.costo_unitario,
    (i.stock_actual * i.costo_unitario)                              AS valor_en_bodega,
    (i.stock_actual < i.stock_minimo)                                AS alerta_stock,
    ROUND(
        (i.stock_actual / NULLIF(i.stock_minimo, 0) * 100)::numeric, 1
    )                                                                AS nivel_pct,
    s.nombre                                                         AS proveedor_principal,
    s.email                                                          AS proveedor_email
FROM ingredients i
LEFT JOIN ingredient_suppliers isu
       ON isu.ingrediente_id = i.id AND isu.principal = TRUE
LEFT JOIN suppliers s ON s.id = isu.proveedor_id
WHERE i.activo = TRUE
ORDER BY (i.stock_actual < i.stock_minimo) DESC, nivel_pct ASC;

-- Vista mermas del mes (usa columna real: empleado_id → registrado_por)
CREATE OR REPLACE VIEW v_waste_current_month AS
SELECT
    wl.id,
    wl.fecha,
    i.nombre       AS ingrediente,
    i.unidad_medida,
    wl.cantidad,
    wl.motivo,
    wl.costo_estimado,
    wl.registrado_por
FROM waste_logs wl
JOIN ingredients i ON i.id = wl.ingrediente_id
WHERE DATE_TRUNC('month', wl.fecha) = DATE_TRUNC('month', NOW())
ORDER BY wl.fecha DESC;

-- ────────────────────────────────────────────────────────────
-- 8. TRIGGER de auditoría de stock (corregido)
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_audit_stock_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.stock_actual IS DISTINCT FROM NEW.stock_actual THEN
        INSERT INTO audit_logs
            (tipo_evento, descripcion, entidad_afectada,
             datos_anteriores, datos_nuevos, nombre_usuario,
             entidad, accion, entidad_id)
        VALUES (
            'ajuste_stock_manual',
            FORMAT('Stock de "%s" cambió de %s a %s %s',
                   NEW.nombre, OLD.stock_actual, NEW.stock_actual, NEW.unidad_medida),
            'ingredients',
            jsonb_build_object('stock_actual', OLD.stock_actual),
            jsonb_build_object('stock_actual', NEW.stock_actual),
            'trigger_sistema',
            'ingredients',
            'UPDATE',
            NEW.id::TEXT
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_stock ON ingredients;
CREATE TRIGGER trg_audit_stock
    AFTER UPDATE OF stock_actual ON ingredients
    FOR EACH ROW EXECUTE FUNCTION fn_audit_stock_change();

-- ────────────────────────────────────────────────────────────
-- FIN — verificar resultados
-- ────────────────────────────────────────────────────────────
SELECT 'migration_m03_fix.sql aplicado correctamente ✅' AS resultado;