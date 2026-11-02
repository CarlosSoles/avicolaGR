# ==============================================================================
# CAPA DE DOMINIO - AGENTE ROXI
# Archivo: backend/app/modules/agent/domain/__init__.py
# ==============================================================================

from app.modules.agent.domain.schemas import (
    RoxiRecommendRequest,
    ScoreBreakdown,
    CandidateBarnEvaluation,
    SplitSuggestion,
    RoxiAllocationResponse,
    RoxiChatRequest,
    RoxiChatResponse,
)

__all__ = [
    "RoxiRecommendRequest",
    "ScoreBreakdown",
    "CandidateBarnEvaluation",
    "SplitSuggestion",
    "RoxiAllocationResponse",
    "RoxiChatRequest",
    "RoxiChatResponse",
]
