-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V14: SOPORTE DE SEXO MIXTO, PESO AYER Y REESTRUCTURACIÓN DE SALDOS
-- Archivo: backend/database/migration_v14_mixto_and_weights.sql
-- ==============================================================================

-- 1. Permitir sexo 'MIXTO' en lotes (batches)
ALTER TABLE public.batches DROP CONSTRAINT IF EXISTS batches_sex_check;
ALTER TABLE public.batches ADD CONSTRAINT batches_sex_check CHECK (sex IN ('MACHO', 'HEMBRA', 'MIXTO'));

-- 2. Columna para peso promedio de ayer en barn_inventories
ALTER TABLE public.barn_inventories ADD COLUMN IF NOT EXISTS average_weight_yesterday_g NUMERIC(8,2) NULL;

-- 3. Documentación
COMMENT ON COLUMN public.barn_inventories.average_weight_yesterday_g IS 'Peso promedio registrado el día anterior en gramos (evaluación de ganancia diaria)';

