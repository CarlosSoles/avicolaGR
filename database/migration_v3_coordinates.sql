-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V3: COORDENADAS GEOGRÁFICAS (GOOGLE MAPS)
-- Archivo: backend/database/migration_v3_coordinates.sql
-- Ejecutar en Supabase SQL Editor para añadir soporte de geolocalización
-- ==============================================================================

-- 1. Agregar coordenadas a la tabla de Granjas Oficiales (Punto de Origen)
ALTER TABLE public.farms ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7) NULL;
ALTER TABLE public.farms ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7) NULL;

-- 2. Agregar coordenadas a la tabla de Pedidos (Punto de Entrega)
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_latitude NUMERIC(10, 7) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_longitude NUMERIC(10, 7) NULL;

-- 3. Documentación de Columnas
COMMENT ON COLUMN public.farms.latitude IS 'Latitud WGS84 de la entrada o galpones de la granja (Google Maps)';
COMMENT ON COLUMN public.farms.longitude IS 'Longitud WGS84 de la entrada o galpones de la granja (Google Maps)';
COMMENT ON COLUMN public.orders.delivery_latitude IS 'Latitud WGS84 del punto de entrega acordado con el cliente (Google Maps)';
COMMENT ON COLUMN public.orders.delivery_longitude IS 'Longitud WGS84 del punto de entrega acordado con el cliente (Google Maps)';
