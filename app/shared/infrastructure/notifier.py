# ==============================================================================
# GENERADOR DE NOTIFICACIONES POR EVENTOS
# Archivo: backend/app/shared/infrastructure/notifier.py
# ==============================================================================

from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def notify(
    db: Optional[AsyncSession],
    *,
    category: str,
    type: str,
    title: str,
    description: str,
    target_roles: Iterable[str] = (),
    target_user_id: Optional[UUID] = None,
    farm_code: Optional[str] = None,
    order_id: Optional[UUID] = None,
    badge: Optional[str] = None,
) -> None:
    """
    Registra una notificación del sistema. Nunca interrumpe el flujo de negocio:
    si falla, solo se registra en consola.
    """
    if db is None:
        return

    try:
        await db.execute(
            text("""
                INSERT INTO public.notifications
                    (category, type, title, description, badge,
                     target_roles, target_user_id, farm_code, order_id)
                VALUES
                    (:category, :type, :title, :description, :badge,
                     CAST(:roles AS text[]), CAST(:user_id AS uuid),
                     :farm_code, CAST(:order_id AS uuid))
            """),
            {
                "category": category,
                "type": type,
                "title": title,
                "description": description,
                "badge": badge,
                "roles": list(target_roles),
                "user_id": str(target_user_id) if target_user_id else None,
                "farm_code": farm_code,
                "order_id": str(order_id) if order_id else None,
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"[notifier] No se pudo registrar la notificación: {e}")
