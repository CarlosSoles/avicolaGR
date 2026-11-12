-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V10: DENSIDAD DE CARGA POR ZONA Y SEXO (AVES / JAULA)
-- Archivo: backend/database/migration_v10_zone_cage_densities.sql
-- Permite al Administrador configurar la densidad por defecto según zona y sexo:
--   - Zona Norte: Machos 8, Hembras 11
--   - Metropolitana: Machos 9, Hembras 11
--   - Zona Centro: Machos 9, Hembras 11
--   - Zona Sur: Machos 8, Hembras 11
-- Área Comercial consulta estos valores en solo lectura al crear pedidos.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.zone_cage_densities (
    zone_code VARCHAR(50) PRIMARY KEY,
    zone_name VARCHAR(100) NOT NULL,
    male_density INT NOT NULL CHECK (male_density BETWEEN 7 AND 12),
    female_density INT NOT NULL CHECK (female_density BETWEEN 7 AND 12),
    updated_by_user_id UUID REFERENCES public.users_profile(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO public.zone_cage_densities (zone_code, zone_name, male_density, female_density) VALUES
    ('NORTE', 'Zona Norte', 8, 11),
    ('METROPOLITANA', 'Metropolitana (Lima)', 9, 11),
    ('CENTRO', 'Zona Centro', 9, 11),
    ('SUR', 'Zona Sur', 8, 11)
ON CONFLICT (zone_code) DO NOTHING;

COMMENT ON TABLE public.zone_cage_densities IS
    'Densidades de carga por defecto (aves por jaula, 7-12) configuradas por Administración según zona y sexo.';

