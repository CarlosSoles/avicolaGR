-- ==============================================================================
-- MIGRACIÓN v13: LÍNEAS MÚLTIPLES POR PEDIDO (order_lines)
-- Archivo: backend/database/migration_v13_order_lines.sql
-- ==============================================================================

ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS order_lines JSONB NOT NULL DEFAULT '[]'::jsonb;

