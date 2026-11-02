# ==============================================================================
# PRUEBAS UNITARIAS Y DE INTEGRACIÓN DEL AGENTE ROXI
# Archivo: backend/tests/test_roxi_agent.py
# ==============================================================================

import pytest
from app.modules.agent.domain.schemas import (
    RoxiRecommendRequest,
    RoxiChatRequest,
)
from app.modules.agent.application.roxi_service import RoxiAgentService
from app.modules.agent.infrastructure.distances import (
    get_farm_distance_km,
    calculate_freight_cost_soles,
)


@pytest.mark.asyncio
async def test_roxi_recommend_macho_centro():
    """
    Verifica que ROXI recomiende un galpón compatible de machos para Zona Centro,
    priorizando edad biológica (> 45 días) y cercanía (ej. TRAD1 o SISA1).
    """
    service = RoxiAgentService(db=None)

    req = RoxiRecommendRequest(
        client_name="Distribuidora Santa Anita S.A.C.",
        quantity_birds=4000,
        sex="Macho",
        min_weight=2.30,
        max_weight=2.60,
        zone_code="CENTRO",
        delivery_address="Mercado Santa Anita",
        user_role="vendedor",
    )

    res = await service.recommend_barn(req)

    # Validaciones obligatorias de negocio
    assert res.recommended_barn is not None
    assert res.recommended_barn.sex in ("MACHO", "INDISTINTO")
    assert res.recommended_barn.available_balance > 0
    assert res.recommended_barn.score_total >= 70
    assert res.recommended_barn.score_breakdown.edad_biologica > 0
    assert res.commercial_pitch is not None and len(res.commercial_pitch) > 10
    assert res.agent_name == "ROXI"


@pytest.mark.asyncio
async def test_roxi_recommend_hembra_strict_filter():
    """
    Verifica que ROXI aplique la restricción dura de sexo:
    Si se solicita hembra, jamás debe recomendar un lote clasificado como macho.
    """
    service = RoxiAgentService(db=None)

    req = RoxiRecommendRequest(
        client_name="Pollerías Norky's Corp S.A.",
        quantity_birds=3000,
        sex="Hembra",
        min_weight=2.10,
        max_weight=2.30,
        zone_code="METROPOLITANA",
        user_role="vendedor",
    )

    res = await service.recommend_barn(req)

    assert res.recommended_barn is not None
    assert res.recommended_barn.sex in ("HEMBRA", "INDISTINTO")
    assert res.recommended_barn.sex != "MACHO"


@pytest.mark.asyncio
async def test_roxi_chat_guardrails():
    """
    Verifica que las consultas ajenas a la operación avícola sean rechazadas
    amablemente por los guardrails de ROXI.
    """
    service = RoxiAgentService(db=None)

    # Consulta fuera de ámbito
    out_of_scope_req = RoxiChatRequest(
        message="¿Me cuentas un chiste o una receta de cocina?",
        user_role="vendedor",
    )
    chat_res = await service.chat(out_of_scope_req)
    assert chat_res.in_scope is False
    assert "ROXI" in chat_res.reply
    assert "delimitada" in chat_res.reply.lower()

    # Consulta operativa válida
    in_scope_req = RoxiChatRequest(
        message="¿Cómo recomiendas los galpones según la edad de saca?",
        user_role="gestor_comercial",
    )
    valid_res = await service.chat(in_scope_req)
    assert valid_res.in_scope is True
    assert "45" in valid_res.reply


def test_distances_matrix():
    """Verifica que la matriz de distancias viales responda con valores numéricos correctos."""
    dist_trad1_centro = get_farm_distance_km("TRAD1", "CENTRO")
    assert dist_trad1_centro > 0
    assert dist_trad1_centro < 30.0  # Tradisa 1 está cerca de Santa Anita / Ate

    flete = calculate_freight_cost_soles(dist_trad1_centro)
    assert flete > 0

