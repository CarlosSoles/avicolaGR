-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V5: DENSIDAD DE CARGA (AVES POR JAULA)
-- Archivo: backend/database/migration_v5_order_density.sql
-- Ejecutar en Supabase SQL Editor sobre bases existentes.
-- Permite que cada pedido defina su densidad de carga (7 a 12 aves por jaula)
-- y que el cálculo de jaulas y camiones se derive de ella.
-- ==============================================================================

-- 1. Densidad de carga del pedido (aves por jaula)
ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS density_birds_per_cage INT NOT NULL DEFAULT 8;

-- 2. Rango operativo permitido: 7 a 12 aves por jaula
DO $$
BEGIN
    ALTER TABLE public.orders
        ADD CONSTRAINT chk_orders_density_birds_per_cage
        CHECK (density_birds_per_cage BETWEEN 7 AND 12);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 3. Documentación de la columna
COMMENT ON COLUMN public.orders.density_birds_per_cage IS
    'Densidad de carga del pedido en aves por jaula (7-12). Las jaulas se calculan como ceil(aves / densidad).';
