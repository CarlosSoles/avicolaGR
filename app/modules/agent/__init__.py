# ==============================================================================
# MÓDULO OFICIAL DEL AGENTE INTELIGENTE ROXI - AVÍCOLA GR
# Archivo: backend/app/modules/agent/__init__.py
# ==============================================================================

from app.modules.agent.application.roxi_service import RoxiAgentService
from app.modules.agent.presentation.router import router as agent_router

__all__ = [
    "RoxiAgentService",
    "agent_router",
]
