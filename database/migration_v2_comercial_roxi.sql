-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V2: MÓDULO COMERCIAL, FLOTA Y AGENTE ROXI
-- Archivo: backend/database/migration_v2_comercial_roxi.sql
-- Ejecutar en Supabase SQL Editor si ya tenías la versión anterior de schema.sql
-- ==============================================================================

-- 1. Asegurar nuevas columnas en la tabla `orders`
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS requested_quantity INT DEFAULT 3000;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS allocated_quantity INT DEFAULT 0;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS min_weight_kg NUMERIC(4,2) DEFAULT 2.20;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS max_weight_kg NUMERIC(4,2) DEFAULT 2.50;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS sex_preference VARCHAR(15) DEFAULT 'INDISTINTO';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS suggested_farm_code VARCHAR(20) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS suggested_barn_code VARCHAR(20) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS assigned_farm_code VARCHAR(20) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS assigned_barn_code VARCHAR(20) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS gestor_username VARCHAR(100) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS delivery_address TEXT NULL;

-- Control de Fraccionamiento (Split)
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS is_split_parent BOOLEAN DEFAULT FALSE;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS is_split_child BOOLEAN DEFAULT FALSE;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS parent_order_id UUID NULL REFERENCES public.orders(id);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS original_requested_quantity INT NULL;

-- Logística y Transporte
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS transport_assigned BOOLEAN DEFAULT FALSE;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS transport_truck_id VARCHAR(50) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS transport_plate VARCHAR(20) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS transport_driver_name VARCHAR(150) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS transport_driver_phone VARCHAR(50) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS transport_shift VARCHAR(50) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS dispatch_phase VARCHAR(50) NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS estimated_cages INT NULL;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS estimated_total_kg NUMERIC(10,2) NULL;

-- 2. Crear tabla de vehículos de transporte si no existe
CREATE TABLE IF NOT EXISTS public.transport_vehicles (
    id VARCHAR(50) PRIMARY KEY,
    plate VARCHAR(20) NOT NULL UNIQUE,
    driver_name VARCHAR(150) NOT NULL,
    driver_phone VARCHAR(50) NOT NULL,
    shift VARCHAR(50) DEFAULT 'Madrugada (02:00 - 08:00)',
    capacity_birds INT NOT NULL DEFAULT 4000,
    capacity_kg NUMERIC(10,2) NOT NULL DEFAULT 10000.00,
    status VARCHAR(30) DEFAULT 'DISPONIBLE',
    current_zone VARCHAR(50) DEFAULT 'CENTRO',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Crear tabla de auditoría para el Agente ROXI
CREATE TABLE IF NOT EXISTS public.roxi_recommendation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NULL REFERENCES public.orders(id),
    client_name VARCHAR(150) NULL,
    quantity_birds INT NOT NULL,
    sex VARCHAR(15) NULL,
    min_weight NUMERIC(4,2) NULL,
    max_weight NUMERIC(4,2) NULL,
    zone_code VARCHAR(50) NULL,
    recommended_farm VARCHAR(20) NOT NULL,
    recommended_barn VARCHAR(20) NOT NULL,
    score_total NUMERIC(5,2) NOT NULL,
    alternative_farm VARCHAR(20) NULL,
    alternative_barn VARCHAR(20) NULL,
    freight_saving_soles NUMERIC(8,2) DEFAULT 0,
    model_used VARCHAR(50) DEFAULT 'gemini-2.0-flash',
    execution_time_ms NUMERIC(8,2) NULL,
    user_role VARCHAR(50) NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Actualizar publicación de Realtime en Supabase
DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.transport_vehicles;
EXCEPTION WHEN OTHERS THEN
    -- Ya estaba agregada o permiso concedido
END $$;

