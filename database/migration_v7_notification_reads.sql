-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V7: NOTIFICACIONES LEÍDAS POR USUARIO
-- Archivo: backend/database/migration_v7_notification_reads.sql
-- Motivo: el estado "leído" vivía solo en localStorage del navegador, por lo que
-- se perdía al entrar desde otro navegador, equipo o modo incógnito.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.notification_reads (
    user_id UUID NOT NULL,
    notification_key VARCHAR(100) NOT NULL,
    read_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, notification_key)
);

CREATE INDEX IF NOT EXISTS idx_notification_reads_user
    ON public.notification_reads(user_id);

COMMENT ON TABLE public.notification_reads IS
    'Notificaciones marcadas como leídas por cada usuario (sobrevive a cambios de navegador).';
