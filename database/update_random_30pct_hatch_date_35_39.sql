-- Actualiza aleatoriamente el 30% de los lotes activos actuales para que tengan
-- entre 35 y 39 días de edad hoy, manteniendo el cálculo automático diario
-- basado en (CURRENT_DATE - hatch_date).

WITH target_batches AS (
    SELECT b.id
    FROM public.batches b
    INNER JOIN public.barn_inventories bi ON bi.current_batch_id = b.id
    WHERE b.is_active = TRUE
    ORDER BY random()
    LIMIT (
        SELECT GREATEST(1, ROUND(COUNT(*) * 0.30)::INT)
        FROM public.batches b2
        INNER JOIN public.barn_inventories bi2 ON bi2.current_batch_id = b2.id
        WHERE b2.is_active = TRUE
    )
)
UPDATE public.batches b
SET hatch_date = CURRENT_DATE - (35 + FLOOR(random() * 5)::INT)
FROM target_batches tb
WHERE b.id = tb.id;

