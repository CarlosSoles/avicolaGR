-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V8: NOTIFICACIONES GENERADAS POR EVENTOS
-- Archivo: backend/database/migration_v8_notifications.sql
-- Las notificaciones dejan de ser textos fijos en el frontend y pasan a ser
-- eventos reales del sistema, con visibilidad por rol o por usuario.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(30) NOT NULL,
    type VARCHAR(30) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    badge VARCHAR(60) NULL,
    target_roles TEXT[] NOT NULL DEFAULT '{}',
    target_user_id UUID NULL,
    farm_code VARCHAR(20) NULL,
    order_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_created ON public.notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON public.notifications(target_user_id);

COMMENT ON TABLE public.notifications IS
    'Notificaciones generadas por eventos del sistema (pedidos, transporte, pesajes).';
