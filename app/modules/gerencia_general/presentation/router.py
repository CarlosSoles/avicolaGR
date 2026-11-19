# ==============================================================================
# ROUTER FASTAPI DEL MÓDULO GERENCIA GENERAL (DASHBOARD & ROXI COPILOT)
# Archivo: backend/app/modules/gerencia_general/presentation/router.py
# ==============================================================================

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role, AuthenticatedUser
from app.modules.gerencia_general.domain.schemas import (
    ExecutiveFullReport,
    ExecutiveBriefResponse,
)
from app.modules.gerencia_general.application.service import GerenciaGeneralService

router = APIRouter(prefix="/gerencia-general", tags=["Módulo Gerencia General"])

# Permite acceso al Gerente General, Administrador de Sistema y Gerente Comercial
ALLOWED_ROLES = ["gerente_general", "admin_sistema", "gerente_comercial"]


@router.get(
    "/analytics",
    response_model=ExecutiveFullReport,
    status_code=status.HTTP_200_OK,
    summary="Obtener reporte ejecutivo 360 consolidado",
    description="Retorna KPIs directivos, ventas, desempeño de personal, producción y logística con filtros de período y zona/granja.",
)
async def get_executive_analytics(
    start_date: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    zone_code: Optional[str] = Query(None, description="Código de zona para filtrar (ej. 'SUR', 'NORTE')"),
    farm_code: Optional[str] = Query(None, description="Código de granja para filtrar (ej. 'SANTA_MARIA')"),
    session: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(ALLOWED_ROLES)),
):
    service = GerenciaGeneralService(session)
    return await service.get_consolidated_report(
        start_date=start_date,
        end_date=end_date,
        zone_code=zone_code,
        farm_code=farm_code,
    )


@router.get(
    "/brief",
    response_model=ExecutiveBriefResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener briefing ejecutivo estratégico generado por ROXI Copilot",
    description="Sintetiza la operación avícola en puntos clave, alertas críticas y recomendaciones estratégicas. Opcionalmente genera audio TTS en base64.",
)
async def get_executive_brief(
    start_date: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    with_audio: bool = Query(False, description="Indica si debe sintetizarse audio TTS narrado por ROXI"),
    session: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_role(ALLOWED_ROLES)),
):
    service = GerenciaGeneralService(session)
    report = await service.get_consolidated_report(start_date=start_date, end_date=end_date)
    return await service.generate_executive_brief(report=report, with_audio=with_audio)
