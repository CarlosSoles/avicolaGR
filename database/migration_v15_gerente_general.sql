-- ==============================================================================
-- MIGRACIÓN v15: ROL GERENTE GENERAL Y USUARIO DIRECTIVO
-- Archivo: backend/database/migration_v15_gerente_general.sql
-- ==============================================================================

-- 1. Ampliar el constraint de roles en users_profile para permitir 'gerente_general'
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
    'controlador_flota',
    'gerente_general'
));

-- 2. Insertar o actualizar el usuario gerente oficial con rol gerente_general
-- Contraseña hash bcrypt de 'gerente1' (o se sincroniza automáticamente vía backend)
INSERT INTO public.users_profile (
    id,
    username,
    email,
    password_hash,
    full_name,
    role,
    is_active,
    created_at,
    updated_at
)
VALUES (
    '00000000-0000-0000-0000-000000000099',
    'gerente',
    'gerente@avicolagr.com',
    '$2b$12$eX8Vom0TfOqQ0O9m0aE1ueV7.n96xJqG0lG24s5bL5v11.u1pQy6W', -- Hash bcrypt o verificado por backend
    'Gerente General de la Avícola',
    'gerente_general',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (email) DO UPDATE
SET
    username = EXCLUDED.username,
    full_name = EXCLUDED.full_name,
    role = 'gerente_general',
    is_active = true,
    updated_at = NOW();
