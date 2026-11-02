# ==============================================================================
# SERVICIO DE AUDITORÍA INMUTABLE
# Archivo: backend/app/shared/infrastructure/audit_logger.py
# ==============================================================================

from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def log_audit_event(
    db: AsyncSession,
    entity_name: str,
    entity_id: UUID,
    action: str,
    user_id: UUID,
    new_state: Dict[str, Any],
    previous_state: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> None:
    """
    Inserta de forma inmutable un registro en la tabla audit_logs de Supabase PostgreSQL.
    """
    query = text("""
        INSERT INTO public.audit_logs (
            entity_name, entity_id, action, user_id, 
            previous_state, new_state, reason, client_ip
        ) VALUES (
            :entity_name, :entity_id, :action, :user_id, 
            CAST(:previous_state AS jsonb), CAST(:new_state AS jsonb), :reason, :client_ip
        )
    """)

    import json
    await db.execute(
        query,
        {
            "entity_name": entity_name,
            "entity_id": str(entity_id),
            "action": action,
            "user_id": str(user_id),
            "previous_state": json.dumps(previous_state) if previous_state else None,
            "new_state": json.dumps(new_state),
            "reason": reason,
            "client_ip": client_ip,
        }
    )

