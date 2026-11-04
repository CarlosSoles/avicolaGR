-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V4: COORDENADAS SATELITALES DE CLIENTES
-- Archivo: backend/database/migration_v4_client_coordinates.sql
-- Ejecutar en Supabase SQL Editor sobre bases existentes.
-- Permite autocompletar el punto de entrega de los pedidos comerciales con las
-- coordenadas registradas previamente en la ficha del cliente.
-- ==============================================================================

-- 1. Coordenadas del punto de entrega habitual del cliente
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7) NULL;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7) NULL;

-- 2. Documentación de columnas
COMMENT ON COLUMN public.clients.latitude IS 'Latitud WGS84 del punto de entrega habitual del cliente (Google Maps)';
COMMENT ON COLUMN public.clients.longitude IS 'Longitud WGS84 del punto de entrega habitual del cliente (Google Maps)';
