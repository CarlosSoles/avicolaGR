# ==============================================================================
# ROUTER FASTAPI DEL AGENTE ROXI
# Archivo: backend/app/modules/agent/presentation/router.py
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, AuthenticatedUser
from app.core.config import settings
from app.modules.agent.domain.schemas import (
    RoxiRecommendRequest,
    RoxiAllocationResponse,
    RoxiChatRequest,
    RoxiChatResponse,
)
from app.modules.agent.application.roxi_service import RoxiAgentService

router = APIRouter(prefix="/agent", tags=["Agente IA • ROXI"])


@router.post(
    "/recommend-barn",
    response_model=RoxiAllocationResponse,
    summary="Recomendación inteligente de galpón con ROXI",
)
async def recommend_barn(
    req: RoxiRecommendRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evalúa las variables de la solicitud comercial (aves, peso, sexo, zona, fecha)
    y consulta a ROXI (Gemini Flash con Structured Outputs) para obtener la asignación
    óptima ponderada por edad biológica (> 45 días), distancia vial y calibre de peso.
    """
    req.user_role = current_user.role
    service = RoxiAgentService(db=db)
    try:
        return await service.recommend_barn(req)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la inferencia de ROXI: {str(e)}",
        )


@router.post(
    "/reassign-order/{order_id}",
    response_model=RoxiAllocationResponse,
    summary="Reasignar pedido por contingencia operativa con ROXI",
)
async def reassign_order(
    order_id: str,
    reason: str = "Ajuste operativo o contingencia en galpón",
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permite al Gestor Comercial o Administrador reasignar un pedido que ha tenido
    reducción de saldo por aves especiales o bloqueo de galpón.
    """
    if current_user.role not in ("gestor_comercial", "gerente_comercial", "admin_sistema"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el Gestor Comercial o Administrador pueden solicitar reasignaciones con ROXI.",
        )

    service = RoxiAgentService(db=db)
    try:
        return await service.reassign_order(order_id, reason=reason)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/chat",
    response_model=RoxiChatResponse,
    summary="Conversar con ROXI (Asistente de Saca)",
)
async def chat_with_roxi(
    req: RoxiChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Canal conversacional con ROXI con guardrails de seguridad para delimitar
    consultas a la operación de saca y programación comercial de Avícola GR.
    """
    req.user_role = current_user.role
    service = RoxiAgentService(db=db)
    return await service.chat(req)


@router.get(
    "/status",
    summary="Estado operacional y diagnóstico de ROXI",
)
async def roxi_status(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Diagnóstico de conectividad con Google Gemini y configuración del agente ROXI."""
    has_api_key = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 10)
    return {
        "agent_name": "ROXI",
        "role": "Copiloto IA de Asignación y Planificación de Saca",
        "version": "2.0.0-Production",
        "model": settings.GEMINI_MODEL,
        "api_key_configured": has_api_key,
        "mode": "Live Inventory + Gemini 2.0 Flash (Free Tier)",
        "status": "OPERATIONAL" if has_api_key else "DEGRADED_FALLBACK",
        "company": "Avícola GR / Grupo El Rocío",
    }

