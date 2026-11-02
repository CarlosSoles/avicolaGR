-- ==============================================================================
-- SISTEMA DE PLANIFICACIÓN DE SACA DE AVES - AVÍCOLA GR
-- Esquema Maestro de Base de Datos para Supabase (PostgreSQL 16)
-- Archivo: backend/database/schema.sql
-- Incluye: Módulo Comercial, Pecuaria, Gestión de Flota y Agente ROXI
-- ==============================================================================

-- 1. Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 2. FUNCIÓN DE ACTUALIZACIÓN DE TIMESTAMPS
-- ==============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- 3. MÓDULO ADMINISTRACIÓN Y CONTROL DE ACCESOS
-- ==============================================================================

-- 3.1. Perfiles de usuario (Vinculados con auth.users de Supabase o auth directo)
CREATE TABLE IF NOT EXISTS public.users_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN (
        'admin_sistema',
        'registrador_pecuario',
        'supervisor_pecuario',
        'vendedor',
        'gestor_comercial',
        'gerente_comercial'
    )),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_users_profile_updated_at
BEFORE UPDATE ON public.users_profile
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 3.2. Catálogos generales del sistema
CREATE TABLE IF NOT EXISTS public.catalogs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalog_type VARCHAR(50) NOT NULL, -- 'MOTIVO_ESPECIAL', 'BLOQUEO_GALPON', 'TIPO_MOVIMIENTO'
    code VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(catalog_type, code)
);

-- 3.3. Parámetros técnicos configurables
CREATE TABLE IF NOT EXISTS public.technical_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    param_key VARCHAR(100) NOT NULL UNIQUE,
    param_value TEXT NOT NULL,
    data_type VARCHAR(20) NOT NULL CHECK (data_type IN ('INT', 'FLOAT', 'STRING', 'BOOLEAN', 'JSON')),
    description TEXT NULL,
    updated_by_user_id UUID REFERENCES public.users_profile(id),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3.4. Ámbitos de trabajo (Asignación de Granjas/Galpones o Zonas a usuarios)
CREATE TABLE IF NOT EXISTS public.user_scopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users_profile(id) ON DELETE CASCADE,
    scope_type VARCHAR(50) NOT NULL CHECK (scope_type IN ('GRANJA', 'GALPON', 'ZONA_COMERCIAL')),
    target_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, scope_type, target_id)
);

-- ==============================================================================
-- 4. MÓDULO PECUARIA (FUENTE DE VERDAD FÍSICA Y BIOLÓGICA)
-- ==============================================================================

-- 4.1. Granjas (23 Granjas Oficiales)
CREATE TABLE IF NOT EXISTS public.farms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(20) NOT NULL UNIQUE,
    zone_code VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.2. Galpones
CREATE TABLE IF NOT EXISTS public.barns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES public.farms(id) ON DELETE RESTRICT,
    barn_number INT NOT NULL,
    capacity INT NOT NULL CHECK (capacity > 0),
    status VARCHAR(30) NOT NULL DEFAULT 'OPERATIVO' 
        CHECK (status IN ('OPERATIVO', 'BLOQUEADO_SANITARIO', 'PENDIENTE_REVISION', 'CERRADO')),
    block_reason_catalog_id UUID REFERENCES public.catalogs(id),
    block_notes TEXT NULL,
    blocked_at TIMESTAMPTZ NULL,
    blocked_by_user_id UUID REFERENCES public.users_profile(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(farm_id, barn_number)
);

-- 4.3. Lotes de Aves alojados en Galpones
CREATE TABLE IF NOT EXISTS public.batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    barn_id UUID NOT NULL REFERENCES public.barns(id) ON DELETE RESTRICT,
    batch_code VARCHAR(50) NOT NULL UNIQUE,
    hatch_date DATE NOT NULL,
    initial_count INT NOT NULL CHECK (initial_count > 0),
    sex VARCHAR(10) NOT NULL CHECK (sex IN ('MACHO', 'HEMBRA')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.4. Inventario de Galpón (Tabla central de saldos y cantidades comerciales)
CREATE TABLE IF NOT EXISTS public.barn_inventories (
    barn_id UUID PRIMARY KEY REFERENCES public.barns(id) ON DELETE RESTRICT,
    current_batch_id UUID NOT NULL REFERENCES public.batches(id) ON DELETE RESTRICT,
    physical_count INT NOT NULL CHECK (physical_count >= 0),
    specials_count INT NOT NULL DEFAULT 0 CHECK (specials_count >= 0),
    reserved_count INT NOT NULL DEFAULT 0 CHECK (reserved_count >= 0),
    sold_pending_count INT NOT NULL DEFAULT 0 CHECK (sold_pending_count >= 0),
    available_count INT GENERATED ALWAYS AS (
        physical_count - specials_count - reserved_count - sold_pending_count
    ) STORED,
    last_average_weight NUMERIC(5,3) NULL,
    version INT NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_positive_available CHECK (available_count >= 0)
);

CREATE TRIGGER trg_barn_inventories_updated_at
BEFORE UPDATE ON public.barn_inventories
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4.5. Muestras de Pesaje Ave por Ave
CREATE TABLE IF NOT EXISTS public.weighing_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES public.batches(id) ON DELETE RESTRICT,
    barn_id UUID NOT NULL REFERENCES public.barns(id) ON DELETE RESTRICT,
    declared_sample_size INT NOT NULL CHECK (declared_sample_size > 0),
    actual_sample_size INT NOT NULL DEFAULT 0,
    average_weight NUMERIC(5,3) NOT NULL CHECK (average_weight > 0),
    std_deviation NUMERIC(5,3) NULL,
    min_weight NUMERIC(5,3) NOT NULL,
    max_weight NUMERIC(5,3) NOT NULL,
    origin_type VARCHAR(20) NOT NULL CHECK (origin_type IN ('REAL', 'SIMULADO')),
    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETO' CHECK (status IN ('BORRADOR', 'COMPLETO', 'ANULADO')),
    weighed_by_user_id UUID NOT NULL REFERENCES public.users_profile(id),
    weighed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.6. Pesos Individuales Ave por Ave
CREATE TABLE IF NOT EXISTS public.individual_weights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sample_id UUID NOT NULL REFERENCES public.weighing_samples(id) ON DELETE CASCADE,
    bird_sequence INT NOT NULL,
    weight_kg NUMERIC(5,3) NOT NULL CHECK (weight_kg > 0 AND weight_kg <= 6.000),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sample_id, bird_sequence)
);

-- 4.7. Registro de Especiales Encontrados
CREATE TABLE IF NOT EXISTS public.special_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES public.batches(id) ON DELETE RESTRICT,
    barn_id UUID NOT NULL REFERENCES public.barns(id) ON DELETE RESTRICT,
    quantity INT NOT NULL CHECK (quantity > 0),
    reason_catalog_id UUID REFERENCES public.catalogs(id),
    evidence_url TEXT NULL,
    notes TEXT NULL,
    reported_by_user_id UUID NOT NULL REFERENCES public.users_profile(id),
    finding_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4.8. Movimientos Físicos
CREATE TABLE IF NOT EXISTS public.physical_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES public.batches(id) ON DELETE RESTRICT,
    barn_id UUID NOT NULL REFERENCES public.barns(id) ON DELETE RESTRICT,
    movement_type VARCHAR(30) NOT NULL CHECK (movement_type IN (
        'INGRESO_LOTE', 'MORTALIDAD_BAJA', 'TRASLADO_SALIDA', 'TRASLADO_INGRESO', 
        'SACA_DESPACHO', 'AJUSTE_JUSTIFICADO'
    )),
    quantity INT NOT NULL CHECK (quantity > 0),
    reason_catalog_id UUID REFERENCES public.catalogs(id),
    notes TEXT NULL,
    performed_by_user_id UUID NOT NULL REFERENCES public.users_profile(id),
    movement_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- 5. MÓDULO TRANSPORTE Y FLOTA DE DISTRIBUCIÓN
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.transport_vehicles (
    id VARCHAR(50) PRIMARY KEY, -- Ej: 'VH-001'
    plate VARCHAR(20) NOT NULL UNIQUE,
    driver_name VARCHAR(150) NOT NULL,
    driver_phone VARCHAR(50) NOT NULL,
    shift VARCHAR(50) DEFAULT 'Madrugada (02:00 - 08:00)',
    capacity_birds INT NOT NULL DEFAULT 4000,
    capacity_kg NUMERIC(10,2) NOT NULL DEFAULT 10000.00,
    status VARCHAR(30) DEFAULT 'DISPONIBLE' CHECK (status IN ('DISPONIBLE', 'EN_TRANSITO', 'EN_MANTENIMIENTO')),
    current_zone VARCHAR(50) DEFAULT 'CENTRO',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- 6. MÓDULO COMERCIAL (CLIENTES Y PEDIDOS DE VENTA)
-- ==============================================================================

-- 6.1. Clientes
CREATE TABLE IF NOT EXISTS public.clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name VARCHAR(150) NOT NULL,
    tax_id VARCHAR(20) NOT NULL UNIQUE,
    zone_code VARCHAR(50) NOT NULL,
    address TEXT NULL,
    contact_phone VARCHAR(50) NULL,
    preferred_min_weight NUMERIC(4,2) NULL,
    preferred_max_weight NUMERIC(4,2) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6.2. Pedidos de Venta
CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(30) NOT NULL UNIQUE,
    client_id UUID NOT NULL REFERENCES public.clients(id) ON DELETE RESTRICT,
    seller_user_id UUID NULL REFERENCES public.users_profile(id),
    seller_full_name VARCHAR(150) NULL,
    zone_code VARCHAR(50) NOT NULL,
    target_delivery_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'REGISTRADO' CHECK (status IN (
        'BORRADOR', 'REGISTRADO', 'PENDIENTE_PROGRAMACION', 'APROBADO_RESERVADO', 
        'CON_OBSERVACION', 'CONFIRMADO', 'DESPACHADO', 'CANCELADO'
    )),
    
    -- Volúmenes y Pesos
    requested_quantity INT NOT NULL CHECK (requested_quantity > 0),
    allocated_quantity INT NOT NULL DEFAULT 0,
    min_weight_kg NUMERIC(4,2) NOT NULL DEFAULT 2.20,
    max_weight_kg NUMERIC(4,2) NOT NULL DEFAULT 2.50,
    sex_preference VARCHAR(15) DEFAULT 'INDISTINTO' CHECK (sex_preference IN ('MACHO', 'HEMBRA', 'INDISTINTO', 'MIXTO')),

    -- Asignación Pecuaria
    suggested_farm_code VARCHAR(20) NULL,
    suggested_barn_code VARCHAR(20) NULL,
    assigned_farm_code VARCHAR(20) NULL,
    assigned_barn_code VARCHAR(20) NULL,

    -- Control de Fraccionamiento (Order Split)
    is_split_parent BOOLEAN DEFAULT FALSE,
    is_split_child BOOLEAN DEFAULT FALSE,
    parent_order_id UUID NULL REFERENCES public.orders(id),
    original_requested_quantity INT NULL,

    -- Logística y Transporte
    transport_assigned BOOLEAN DEFAULT FALSE,
    transport_truck_id VARCHAR(50) NULL REFERENCES public.transport_vehicles(id),
    transport_plate VARCHAR(20) NULL,
    transport_driver_name VARCHAR(150) NULL,
    transport_driver_phone VARCHAR(50) NULL,
    transport_shift VARCHAR(50) NULL,
    dispatch_phase VARCHAR(50) NULL CHECK (dispatch_phase IN (
        'TRANSPORTE_ASIGNADO', 'EN_GRANJA_CARGANDO', 'EN_TRANSITO', 'ENTREGADO_CONFORME'
    )),
    estimated_cages INT NULL,
    estimated_total_kg NUMERIC(10,2) NULL,

    -- Observaciones y Metadatos
    external_reference VARCHAR(100) NULL,
    gestor_username VARCHAR(100) NULL,
    gestor_observation TEXT NULL,
    delivery_address TEXT NULL,
    notes TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_orders_updated_at
BEFORE UPDATE ON public.orders
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==============================================================================
-- 7. AUDITORÍA DE INFERENCIAS DE LA IA (ROXI)
-- ==============================================================================
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

-- ==============================================================================
-- 8. AUDITORÍA INMUTABLE TRANSVERSAL
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL,
    user_id UUID NULL REFERENCES public.users_profile(id),
    username VARCHAR(100) NULL,
    previous_state JSONB NULL,
    new_state JSONB NOT NULL,
    reason TEXT NULL,
    client_ip VARCHAR(45) NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- 9. VISTA CENTRAL MAESTRA: TABLA GENERAL DE SALDO (PECUARIA)
-- ==============================================================================
CREATE OR REPLACE VIEW public.v_tabla_general_saldo AS
SELECT 
    f.id AS farm_id,
    f.name AS farm_name,
    f.code AS farm_code,
    f.zone_code AS farm_zone,
    b.id AS barn_id,
    b.barn_number,
    CONCAT('G-', LPAD(b.barn_number::TEXT, 2, '0')) AS barn_code,
    b.status AS barn_status,
    bt.id AS batch_id,
    bt.batch_code,
    (CURRENT_DATE - bt.hatch_date) AS bird_age_days,
    COALESCE(bi.specials_count, 0) AS specials_general_count,
    COALESCE(bi.available_count, 0) AS barn_balance_available,
    COALESCE(bi.physical_count, 0) AS physical_count,
    COALESCE(bi.reserved_count, 0) AS reserved_count,
    COALESCE(bi.sold_pending_count, 0) AS sold_pending_count,
    bi.last_average_weight AS average_weight_kg,
    bt.sex AS sex,
    bi.updated_at AS last_inventory_update
FROM public.barns b
JOIN public.farms f ON b.farm_id = f.id
LEFT JOIN public.barn_inventories bi ON bi.barn_id = b.id
LEFT JOIN public.batches bt ON bi.current_batch_id = bt.id
WHERE b.is_active = TRUE;

-- ==============================================================================
-- 10. ÍNDICES DE ALTO RENDIMIENTO
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_delivery_date ON public.orders(target_delivery_date);
CREATE INDEX IF NOT EXISTS idx_orders_client_id ON public.orders(client_id);
CREATE INDEX IF NOT EXISTS idx_farms_code ON public.farms(code);
CREATE INDEX IF NOT EXISTS idx_batches_hatch_date ON public.batches(hatch_date);
CREATE INDEX IF NOT EXISTS idx_weighing_samples_barn ON public.weighing_samples(barn_id);

-- ==============================================================================
-- 11. SUPABASE REALTIME (REACTIVIDAD)
-- ==============================================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.barn_inventories;
ALTER PUBLICATION supabase_realtime ADD TABLE public.orders;
ALTER PUBLICATION supabase_realtime ADD TABLE public.transport_vehicles;
