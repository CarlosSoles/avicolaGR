# ==============================================================================
# ESQUEMAS PYDANTIC DEL MÓDULO DE GERENCIA GENERAL
# Archivo: backend/app/modules/gerencia_general/domain/schemas.py
# ==============================================================================

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. DASHBOARD 360 - KPIs DIRECTIVOS
# ------------------------------------------------------------------------------
class ExecutiveKPIs(BaseModel):
    total_birds_sold: int = Field(..., description="Total de aves vendidas en el período")
    total_tons_sold: float = Field(..., description="Toneladas métricas totales estimadas")
    total_orders: int = Field(..., description="Total de pedidos procesados")
    fulfillment_rate: float = Field(..., description="% de cumplimiento de pedidos a tiempo")
    birds_in_stock: int = Field(..., description="Aves vivas disponibles en granja")
    active_barns: int = Field(..., description="Número de galpones abiertos en producción")
    avg_weight_kg: float = Field(..., description="Peso promedio general de aves en pie (kg)")
    total_cages_dispatched: int = Field(..., description="Total de jaulas despachadas")


# ------------------------------------------------------------------------------
# 2. VENTAS & CLIENTES
# ------------------------------------------------------------------------------
class ZoneSalesItem(BaseModel):
    zone_code: str
    zone_name: str
    birds: int
    cages: int
    percentage: float


class SexSalesItem(BaseModel):
    sex: str
    birds: int
    cages: int
    percentage: float


class TopClientItem(BaseModel):
    client_name: str
    tax_id: Optional[str] = None
    zone_code: str
    orders_count: int
    total_birds: int
    total_cages: int


class SalesTrendItem(BaseModel):
    date: str
    birds_sold: int
    cages_sold: int
    orders_count: int


class SalesAnalytics(BaseModel):
    by_zone: List[ZoneSalesItem]
    by_sex: List[SexSalesItem]
    top_clients: List[TopClientItem]
    trend: List[SalesTrendItem]


# ------------------------------------------------------------------------------
# 3. DESEMPEÑO DEL PERSONAL & PRODUCTIVIDAD
# ------------------------------------------------------------------------------
class SellerPerformanceItem(BaseModel):
    seller_name: str
    orders_count: int
    total_birds: int
    total_cages: int
    approved_pct: float
    rating: str


class DriverPerformanceItem(BaseModel):
    driver_name: str
    plate: str
    trips_count: int
    on_time_pct: float
    status: str


class OperationTimesItem(BaseModel):
    avg_farm_load_min: int
    avg_transit_min: int
    avg_total_cycle_min: int


class StaffPerformanceAnalytics(BaseModel):
    sellers_ranking: List[SellerPerformanceItem]
    drivers_performance: List[DriverPerformanceItem]
    avg_times: OperationTimesItem


# ------------------------------------------------------------------------------
# 4. PRODUCCIÓN, GRANJAS & STOCK EN PIE
# ------------------------------------------------------------------------------
class FarmStockItem(BaseModel):
    farm_code: str
    farm_name: str
    total_birds: int
    available_birds: int
    reserved_birds: int
    active_barns: int
    avg_age_days: float


class WeightDistributionItem(BaseModel):
    range_label: str
    birds_count: int
    percentage: float


class ProductionStockAnalytics(BaseModel):
    by_farm: List[FarmStockItem]
    weight_distribution: List[WeightDistributionItem]
    barns_ready_for_saca: int
    total_live_weight_tons: float


# ------------------------------------------------------------------------------
# 5. LOGÍSTICA & FLOTA
# ------------------------------------------------------------------------------
class IncidentItem(BaseModel):
    reason: str
    count: int
    percentage: float


class LogisticsFleetAnalytics(BaseModel):
    fleet_utilization_pct: float
    total_trips: int
    delivered_rate_pct: float
    incident_reasons: List[IncidentItem]
    avg_cages_per_truck: int


# ------------------------------------------------------------------------------
# 6. INFORME EJECUTIVO CONSOLIDADO
# ------------------------------------------------------------------------------
class ExecutiveFullReport(BaseModel):
    generated_at: str
    period_start: str
    period_end: str
    kpis: ExecutiveKPIs
    sales: SalesAnalytics
    staff: StaffPerformanceAnalytics
    production: ProductionStockAnalytics
    logistics: LogisticsFleetAnalytics


# ------------------------------------------------------------------------------
# 7. BRIEFING Y ASESORÍA DE ROXI
# ------------------------------------------------------------------------------
class ExecutiveBriefResponse(BaseModel):
    headline: str
    summary_points: List[str]
    critical_alerts: List[str]
    strategic_recommendations: List[str]
    speech_text: str
    audio_base64: Optional[str] = None
