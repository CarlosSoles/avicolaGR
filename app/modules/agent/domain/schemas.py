# ==============================================================================
# ESQUEMAS PYDANTIC DEL AGENTE ROXI (MODELO DE DOMINIO)
# Archivo: backend/app/modules/agent/domain/schemas.py
# ==============================================================================

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RoxiRecommendRequest(BaseModel):
    """Solicitud de recomendación de galpón óptimo para el Área Comercial o Gestor."""
    order_id: Optional[str] = Field(None, description="ID del pedido si ya existe registrado")
    client_name: Optional[str] = Field("Cliente Mayorista", description="Nombre o razón social del cliente")
    quantity_birds: int = Field(..., gt=0, description="Cantidad total de aves vivas solicitadas")
    sex: str = Field("Indistinto", description="Sexo requerido: Macho, Hembra o Indistinto")
    min_weight: float = Field(2.20, gt=0.5, description="Peso mínimo aceptable en kg")
    max_weight: float = Field(2.60, gt=0.5, description="Peso máximo aceptable en kg")
    zone_code: str = Field("CENTRO", description="Zona comercial de entrega: NORTE, CENTRO, SUR, METROPOLITANA")
    delivery_address: Optional[str] = Field(None, description="Dirección física de descarga del cliente")
    delivery_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitud del punto de entrega")
    delivery_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitud del punto de entrega")
    scheduled_date: Optional[str] = Field(None, description="Fecha programada de saca (YYYY-MM-DD)")
    user_role: Optional[str] = Field("vendedor", description="Rol que consulta: vendedor, gestor_comercial, gerente_comercial")


class ScoreBreakdown(BaseModel):
    """Desglose detallado del puntaje multicriterio (0-100)."""
    edad_biologica: int = Field(..., description="Puntos por edad del lote (>45 días otorga máximo puntaje)")
    distancia_flete: int = Field(..., description="Puntos por cercanía al punto de descarga")
    calibre_peso: int = Field(..., description="Puntos por calce exacto al peso solicitado")
    eficiencia_saldo: int = Field(..., description="Puntos por vaciado completo de galpón")


class CandidateBarnEvaluation(BaseModel):
    """Evaluación técnica y comercial de un galpón candidato."""
    farm_code: str = Field(..., description="Código oficial de la granja (ej: TRAD1, PACI6)")
    farm_name: str = Field(..., description="Nombre comercial de la granja (ej: Tradisa 1)")
    barn_code: str = Field(..., description="Código del galpón (ej: G-01)")
    current_age_days: float = Field(..., description="Edad biológica del lote en días")
    current_weight_kg: float = Field(..., description="Peso promedio registrado en último muestreo ave por ave")
    available_balance: int = Field(..., description="Saldo disponible de aves vendibles")
    sex: str = Field(..., description="Sexo de las aves en el lote")
    distance_km: float = Field(..., description="Distancia estimada en kilómetros hasta el destino")
    score_total: int = Field(..., ge=0, le=100, description="Score global de 0 a 100")
    score_breakdown: ScoreBreakdown = Field(..., description="Desglose por factor de optimización")
    key_advantage: str = Field(..., description="Ventaja competitiva principal destacada")


class SplitSuggestion(BaseModel):
    """Detalle de división de pedido cuando un galpón no cubre el cupo total."""
    enabled: bool = False
    first_allocation_barn: Optional[str] = None
    first_allocation_birds: Optional[int] = None
    second_allocation_barn: Optional[str] = None
    second_allocation_birds: Optional[int] = None
    reason: Optional[str] = None


class RoxiAllocationResponse(BaseModel):
    """Respuesta oficial estructurada emitida por ROXI."""
    recommended_barn: CandidateBarnEvaluation = Field(..., description="Mejor galpón asignable")
    alternative_barn: Optional[CandidateBarnEvaluation] = Field(None, description="Opción de respaldo")
    commercial_pitch: str = Field(..., description="Argumento comercial persuasivo para el vendedor")
    gestor_technical_notes: str = Field(..., description="Justificación técnica de saca y flete para el gestor")
    split_recommendation: SplitSuggestion = Field(default_factory=SplitSuggestion, description="Sugerencia de fraccionamiento")
    estimated_freight_cost_saving_soles: float = Field(0.0, description="Ahorro estimado en soles respecto a la granja más lejana")
    warnings: List[str] = Field(default_factory=list, description="Alertas sanitarias, viales o de sobreedad")
    agent_name: str = Field("ROXI", description="Identidad del agente de IA")
    model_used: str = Field("gemini-2.0-flash", description="Modelo LLM de inferencia utilizado")
    execution_time_ms: int = Field(0, description="Tiempo total de inferencia en milisegundos")


class RoxiChatRequest(BaseModel):
    """Consulta en lenguaje natural a ROXI con contexto operativo."""
    message: str = Field(..., min_length=2, description="Mensaje o pregunta dirigida a ROXI")
    order_context: Optional[Dict[str, Any]] = Field(None, description="Datos del pedido actual si aplica")
    user_role: Optional[str] = Field("vendedor", description="Rol del usuario que interactúa")


class RoxiChatResponse(BaseModel):
    """Respuesta conversacional de ROXI delimitada por guardrails."""
    reply: str = Field(..., description="Respuesta contextual de ROXI")
    in_scope: bool = Field(True, description="Indica si la consulta correspondió al ámbito avícola comercial")
    suggested_action: Optional[str] = Field(None, description="Acción sugerida: ASIGNAR_GALPON, REASIGNAR, FRACCIONAR")
    action_payload: Optional[Dict[str, Any]] = Field(None, description="Parámetros para ejecutar la acción sugerida")

