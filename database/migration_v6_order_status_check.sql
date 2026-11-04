-- ==============================================================================
-- MIGRACIÓN INCREMENTAL V6: ESTADOS VÁLIDOS DEL PEDIDO
-- Archivo: backend/database/migration_v6_order_status_check.sql
-- Motivo: la restricción original no incluía 'APROBADO_RESERVADO' ni
-- 'PENDIENTE_PROGRAMACION', por lo que la aprobación del Gestor Comercial
-- fallaba al persistir y el sistema caía al respaldo en memoria.
-- ==============================================================================

ALTER TABLE public.orders DROP CONSTRAINT IF EXISTS orders_status_check;

ALTER TABLE public.orders
    ADD CONSTRAINT orders_status_check CHECK (status IN (
        'BORRADOR',
        'REGISTRADO',
        'PENDIENTE_PROGRAMACION',
        'EN_EVALUACION',
        'RESERVADO',
        'APROBADO_RESERVADO',
        'CON_OBSERVACION',
        'CONFIRMADO',
        'DESPACHADO',
        'CANCELADO'
    ));
