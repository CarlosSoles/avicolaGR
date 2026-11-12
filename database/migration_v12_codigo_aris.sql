-- ==============================================================================
-- MIGRACIÓN v12: CÓDIGO ARIS Y CICLO DE VIDA COMPLETO DEL PEDIDO
-- Archivo: backend/database/migration_v12_codigo_aris.sql
-- ==============================================================================

-- 1. Agregar columna codigo_aris a la tabla orders
ALTER TABLE public.orders
ADD COLUMN IF NOT EXISTS codigo_aris VARCHAR(20) NULL,
ADD COLUMN IF NOT EXISTS codigo_aris_generated_at TIMESTAMPTZ NULL,
ADD COLUMN IF NOT EXISTS codigo_aris_generated_by VARCHAR(100) NULL;

-- 2. Índice único para código Aris (no puede repetirse)
CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_codigo_aris ON public.orders (codigo_aris) WHERE codigo_aris IS NOT NULL;