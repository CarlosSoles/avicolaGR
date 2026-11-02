# ==============================================================================
# CAPA DE INFRAESTRUCTURA - AGENTE ROXI
# Archivo: backend/app/modules/agent/infrastructure/__init__.py
# ==============================================================================

from app.modules.agent.infrastructure.distances import (
    FARM_TO_ZONE_DISTANCES_KM,
    COST_PER_KM_SOLES,
    get_farm_distance_km,
    calculate_freight_cost_soles,
)
from app.modules.agent.infrastructure.gemini_client import (
    RoxiGeminiClient,
    ROXI_SYSTEM_PROMPT,
)

__all__ = [
    "FARM_TO_ZONE_DISTANCES_KM",
    "COST_PER_KM_SOLES",
    "get_farm_distance_km",
    "calculate_freight_cost_soles",
    "RoxiGeminiClient",
    "ROXI_SYSTEM_PROMPT",
]
