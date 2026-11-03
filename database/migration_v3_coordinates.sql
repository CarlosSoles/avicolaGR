-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V3: COORDENADAS GEOGRÁFICAS Y RESILIENCIA DE REGISTRO
-- Archivo: backend/database/migration_v3_coordinates.sql
-- Ejecutado en Supabase PostgreSQL para habilitar geolocalización y persistencia comercial
-- ==============================================================================

-- 1. Agregar coordenadas a la tabla de Granjas Oficiales (Punto de Origen)
ALTER TABLE public.farms ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7) NULL;
ALTER TABLE public.farms ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7) NULL;

-- 2. Agregar coordenadas a la tabla de Pedidos (Punto de Entrega)
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_latitude NUMERIC(10, 7) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_longitude NUMERIC(10, 7) NULL;

-- 3. Asegurar columnas de cliente y vendedor en pedidos
ALTER TABLE public.orders ALTER COLUMN client_id DROP NOT NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS client_name VARCHAR(150) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS client_tax_id VARCHAR(50) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS seller_username VARCHAR(100) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS seller_full_name VARCHAR(150) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS farm_contact_phone VARCHAR(100) NULL;

-- 4. Flexibilizar claves foráneas para soporte offline / tokens de desarrollo
ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_seller_user_id_fkey;
ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_client_id_fkey;

-- 5. Documentación de Columnas
COMMENT ON COLUMN public.farms.latitude IS 'Latitud WGS84 de la entrada o galpones de la granja (Google Maps)';
COMMENT ON COLUMN public.farms.longitude IS 'Longitud WGS84 de la entrada o galpones de la granja (Google Maps)';
COMMENT ON COLUMN public.orders.delivery_latitude IS 'Latitud WGS84 del punto de entrega acordado con el cliente (Google Maps)';
COMMENT ON COLUMN public.orders.delivery_longitude IS 'Longitud WGS84 del punto de entrega acordado con el cliente (Google Maps)';
