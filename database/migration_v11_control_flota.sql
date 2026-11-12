-- ==============================================================================
-- MIGRACIÓN v11: MÓDULO CONTROL DE FLOTA Y ROL CONTROLADOR DE FLOTA
-- Archivo: backend/database/migration_v11_control_flota.sql
-- ==============================================================================

-- 1. Ampliar constraint de roles en users_profile para permitir 'controlador_flota'
ALTER TABLE public.users_profile
DROP CONSTRAINT IF EXISTS users_profile_role_check;

ALTER TABLE public.users_profile
ADD CONSTRAINT users_profile_role_check
CHECK (role IN (
    'admin_sistema',
    'registrador_pecuario',
    'supervisor_pecuario',
    'vendedor',
    'gestor_comercial',
    'gerente_comercial',
    'controlador_flota'
));

-- 2. Asegurar columnas completas en transport_vehicles para gestión CRUD de flota
ALTER TABLE public.transport_vehicles
ADD COLUMN IF NOT EXISTS model VARCHAR(100) NULL,
ADD COLUMN IF NOT EXISTS capacity_cages INT NOT NULL DEFAULT 450,
ADD COLUMN IF NOT EXISTS default_crew VARCHAR(100) NULL,
ADD COLUMN IF NOT EXISTS zone_coverage JSONB DEFAULT '[]'::jsonb;

