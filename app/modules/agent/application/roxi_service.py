# ==============================================================================
# SERVICIO DE APLICACIÓN DEL AGENTE ROXI
# Archivo: backend/app/modules/agent/application/roxi_service.py
# ==============================================================================

import time
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent.domain.schemas import (
    RoxiRecommendRequest,
    RoxiAllocationResponse,
    RoxiChatRequest,
    RoxiChatResponse,
)
from app.modules.agent.infrastructure.distances import get_farm_distance_km
from app.modules.agent.infrastructure.gemini_client import RoxiGeminiClient
from app.modules.pecuaria.application.service import PecuariaService
from app.modules.comercial.application.service import ComercialService

# Catálogo predeterminado en memoria de galpones oficiales en caso de inicialización temprana
MOCK_FARMS_INVENTORY = [
    {
        "farm_code": "TRAD1",
        "farm_name": "Tradisa 1",
        "barn_code": "G-01",
        "age_days": 45.4,
        "available_birds": 12500,
        "current_weight": 2.45,
        "sex": "MACHO",
        "status": "OPERATIVO",
    },
    {
        "farm_code": "PACI6",
        "farm_name": "Pacifico 6",
        "barn_code": "G-02",
        "age_days": 43.8,
        "available_birds": 14200,
        "current_weight": 2.52,
        "sex": "INDISTINTO",
        "status": "OPERATIVO",
    },
    {
        "farm_code": "TRAD2",
        "farm_name": "Tradisa II",
        "barn_code": "G-03",
        "age_days": 42.1,
        "available_birds": 9800,
        "current_weight": 2.22,
        "sex": "HEMBRA",
        "status": "OPERATIVO",
    },
    {
        "farm_code": "SISA1",
        "farm_name": "Santa Isabel 1",
        "barn_code": "G-05",
        "age_days": 46.2,
        "available_birds": 8300,
        "current_weight": 2.65,
        "sex": "MACHO",
        "status": "OPERATIVO",
    },
    {
        "farm_code": "MORI2",
        "farm_name": "Puerto Mori 2",
        "barn_code": "G-06",
        "age_days": 44.0,
        "available_birds": 11000,
        "current_weight": 2.35,
        "sex": "INDISTINTO",
        "status": "OPERATIVO",
    },
    {
        "farm_code": "SEMIA",
        "farm_name": "Semillero A",
        "barn_code": "G-04",
        "age_days": 41.5,
        "available_birds": 15000,
        "current_weight": 2.28,
        "sex": "HEMBRA",
        "status": "OPERATIVO",
    },
]


class RoxiAgentService:
    """Servicio coordinador del agente inteligente ROXI."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.gemini_client = RoxiGeminiClient()

    async def _get_live_barn_inventory(self) -> List[Dict[str, Any]]:
        """
        Recupera el inventario en vivo desde la base de datos PostgreSQL de Supabase
        a través de la Tabla General de Saldo de Pecuaria.
        """
        if self.db:
            try:
                saldo_res = await PecuariaService.get_tabla_general_saldo(self.db)
                if saldo_res and saldo_res.data:
                    live_list = []
                    for item in saldo_res.data:
                        live_list.append({
                            "farm_code": item.farm_code,
                            "farm_name": item.farm_name,
                            "barn_code": item.barn_code,
                            "age_days": float(item.bird_age_days),
                            "available_birds": int(item.barn_balance_available),
                            "current_weight": float(item.average_weight_kg) if item.average_weight_kg else 2.40,
                            "sex": item.sex.upper() if item.sex else "INDISTINTO",
                            "status": item.barn_status,
                        })
                    if live_list:
                        return live_list
            except Exception as e:
                # Si la base de datos se encuentra aún sin datos iniciales o con conexión temporal
                pass

        return MOCK_FARMS_INVENTORY

    async def recommend_barn(self, req: RoxiRecommendRequest) -> RoxiAllocationResponse:
        """
        Calcula y recomienda el galpón óptimo para una solicitud comercial dada.
        Aplica arquitectura híbrida: Filtro Rígido en Python + Razonamiento de Gemini Flash.
        """
        start_time = time.time()
        live_inventory = await self._get_live_barn_inventory()

        target_sex = (req.sex or "Indistinto").upper().strip()
        min_w = req.min_weight
        max_w = req.max_weight
        zone = (req.zone_code or "CENTRO").upper().strip()

        # ======================================================================
        # FASE 1: FILTRO RÍGIDO DETERMINISTA (HARD CONSTRAINTS)
        # ======================================================================
        candidates = []
        for barn in live_inventory:
            # 1. Filtro de estado
            if barn.get("status") in ("CERRADO", "CUARENTENA", "MANTENIMIENTO"):
                continue

            # 2. Filtro de saldo disponible
            if barn.get("available_birds", 0) <= 0:
                continue

            # 3. Filtro estricto de sexo
            barn_sex = barn.get("sex", "INDISTINTO").upper()
            if target_sex != "INDISTINTO" and barn_sex != "INDISTINTO" and barn_sex != target_sex:
                continue

            # 4. Filtro de tolerancia de peso (+- 0.18 kg)
            b_weight = barn.get("current_weight", 2.40)
            if b_weight < (min_w - 0.18) or b_weight > (max_w + 0.18):
                continue

            # 5. Cálculo de distancia vial real
            dist_km = get_farm_distance_km(barn["farm_code"], zone)

            candidates.append({
                "farm_code": barn["farm_code"],
                "farm_name": barn["farm_name"],
                "barn_code": barn["barn_code"],
                "current_age_days": barn["age_days"],
                "current_weight_kg": b_weight,
                "available_balance": barn["available_birds"],
                "sex": barn_sex,
                "distance_km": dist_km,
            })

        # Si ningún galpón pasa el filtro rígido con tolerancia estricta,
        # flexibilizar ventana de peso en 100g adicionales para no dejar la respuesta vacía
        if not candidates:
            for barn in live_inventory:
                if barn.get("available_birds", 0) > 0:
                    dist_km = get_farm_distance_km(barn["farm_code"], zone)
                    candidates.append({
                        "farm_code": barn["farm_code"],
                        "farm_name": barn["farm_name"],
                        "barn_code": barn["barn_code"],
                        "current_age_days": barn.get("age_days", 42.0),
                        "current_weight_kg": barn.get("current_weight", 2.40),
                        "available_balance": barn.get("available_birds", 5000),
                        "sex": barn.get("sex", "INDISTINTO"),
                        "distance_km": dist_km,
                    })

        # Pre-ordenar candidatos priorizando edad > 45 días (urgente) y menor distancia km
        candidates.sort(
            key=lambda c: (
                0 if c["current_age_days"] >= 45.0 else 1,
                -c["current_age_days"],
                c["distance_km"],
            )
        )
        top_candidates = candidates[:5]

        # ======================================================================
        # FASE 2: INFERENCIA DE ROXI (GEMINI FLASH CON STRUCTURED OUTPUTS)
        # ======================================================================
        order_dict = req.model_dump()
        response = await self.gemini_client.generate_allocation(
            order_request=order_dict,
            candidates=top_candidates,
            user_role=req.user_role or "vendedor",
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        response.execution_time_ms = elapsed_ms
        return response

    async def reassign_order(self, order_id: str, reason: str = "Ajuste operativo") -> RoxiAllocationResponse:
        """
        Reasigna un pedido existente cuando el galpón reservado sufre un imprevisto
        (descartes, mortandad o sobreventa).
        """
        order = ComercialService.get_order_by_id(order_id)
        if not order:
            raise ValueError(f"No se encontró el pedido con ID {order_id}")

        delivery_date_str = (
            order.target_delivery_date.isoformat()
            if hasattr(order.target_delivery_date, "isoformat")
            else str(order.target_delivery_date)
        )

        req = RoxiRecommendRequest(
            order_id=order.id,
            client_name=order.client_business_name,
            quantity_birds=order.quantity_birds,
            sex=order.requested_sex,
            min_weight=order.requested_weight_range_min,
            max_weight=order.requested_weight_range_max,
            zone_code=order.zone_code,
            delivery_address=order.delivery_address,
            scheduled_date=delivery_date_str,
            user_role="gestor_comercial",
        )

        res = await self.recommend_barn(req)
        res.gestor_technical_notes = f"[REASIGNACIÓN ACTIVADA]: {reason}. {res.gestor_technical_notes}"
        return res

    async def chat(self, req: RoxiChatRequest) -> RoxiChatResponse:
        """Responde consultas conversacionales del Vendedor o Gestor."""
        res_dict = await self.gemini_client.chat(
            request_msg=req.message,
            user_role=req.user_role or "vendedor",
            context=req.order_context,
        )
        return RoxiChatResponse.model_validate(res_dict)
