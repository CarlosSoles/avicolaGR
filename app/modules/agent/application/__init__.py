# ==============================================================================
# CAPA DE APLICACIÓN - AGENTE ROXI
# Archivo: backend/app/modules/agent/application/__init__.py
# ==============================================================================

from app.modules.agent.application.roxi_service import (
    RoxiAgentService,
    MOCK_FARMS_INVENTORY,
)

__all__ = [
    "RoxiAgentService",
    "MOCK_FARMS_INVENTORY",
]
