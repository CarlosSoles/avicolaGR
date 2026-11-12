"""Actualiza aleatoriamente el 30% de los lotes activos en BD a 35-39 días."""

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.core.database import engine


SQL_UPDATE = """
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
WHERE b.id = tb.id
RETURNING b.batch_code, b.hatch_date, (CURRENT_DATE - b.hatch_date) AS age_days;
"""


async def main() -> None:
    async with engine.begin() as conn:
        res = await conn.execute(text(SQL_UPDATE))
        rows = res.fetchall()
        print(f"Lotes actualizados (30%): {len(rows)}")
        for row in rows[:10]:
            print(f"  - {row[0]}: hatch_date={row[1]} ({row[2]} días)")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

