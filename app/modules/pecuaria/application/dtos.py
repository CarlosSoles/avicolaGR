# ==============================================================================
# DATA TRANSFER OBJECTS (DTOs / SCHEMAS) DEL MÓDULO PECUARIA
# Archivo: backend/app/modules/pecuaria/application/dtos.py
# ==============================================================================

from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ==============================================================================
# 1. TABLA GENERAL DE SALDO (DTO PRINCIPAL)
# ==============================================================================

class TablaGeneralSaldoItemDTO(BaseModel):
    """
    Representa una fila de la Tabla General de Saldo con las 7 columnas obligatorias:
    1. Granja (farm_name)
    2. Galpón (barn_number)
    3. Edad del ave en días (bird_age_days)
    4. Especiales cantidad general (specials_general_count)
    5. Saldo por galpón disponible (barn_balance_available)
    6. Peso promedio en kg (average_weight_kg)
    7. Sexo del lote (sex: 'MACHO', 'HEMBRA', 'MIXTO')
    """
    farm_id: UUID
    farm_name: str
    farm_code: Optional[str] = Field(default=None, description="Código único de la granja padre (ej. G-SP-01)")
    farm_zone: str
    barn_id: UUID
    barn_number: int
    barn_code: Optional[str] = Field(default=None, description="Código único del galpón hijo (ej. G-01)")
    barn_status: str
    batch_id: Optional[UUID] = None
    batch_code: Optional[str] = None
    
    # Las 7 columnas obligatorias
    bird_age_days: int = Field(description="Edad calculada del lote en días (Fecha actual - Fecha encaste)")
    specials_general_count: int = Field(description="Cantidad general de aves especiales observadas en el galpón")
    barn_balance_available: int = Field(description="Saldo por galpón disponible libre de compromisos")
    average_weight_kg: Optional[float] = Field(default=None, description="Peso promedio representativo en kg (x̄)")
    min_weight_kg: Optional[float] = Field(default=None, description="Peso mínimo registrado en la muestra")
    max_weight_kg: Optional[float] = Field(default=None, description="Peso máximo registrado en la muestra")
    weight_range_label: Optional[str] = Field(default=None, description="Rango de peso formateado (ej: 2.45 - 2.85 kg)")
    sex: str = Field(description="Sexo biológico del lote: MACHO, HEMBRA o MIXTO")
    
    # Desglose operativo adicional
    physical_count: int = Field(description="Conteo físico total de aves vivas en el galpón")
    reserved_count: int = Field(description="Cantidad de aves reservadas por el Gestor Comercial")
    sold_pending_count: int = Field(description="Cantidad de aves vendidas pendientes de saca")
    last_inventory_update: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TablaGeneralSaldoResponse(BaseModel):
    total_records: int
    data: List[TablaGeneralSaldoItemDTO]


# ==============================================================================
# 2. GRANJAS, GALPONES Y LOTES
# ==============================================================================

class FarmCreateDTO(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    code: str = Field(min_length=2, max_length=20)
    zone_code: str = Field(min_length=2, max_length=50)


class FarmDTO(FarmCreateDTO):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BarnCreateDTO(BaseModel):
    farm_id: UUID
    barn_number: int = Field(gt=0)
    capacity: int = Field(gt=0)


class BarnDTO(BarnCreateDTO):
    id: UUID
    status: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BatchCreateDTO(BaseModel):
    barn_id: UUID
    batch_code: str = Field(min_length=3, max_length=50)
    hatch_date: date
    initial_count: int = Field(gt=0)
    sex: str = Field(description="MACHO o HEMBRA")

    @field_validator("sex")
    def validate_sex(cls, v: str) -> str:
        upper_v = v.upper().strip()
        if upper_v not in ("MACHO", "HEMBRA"):
            raise ValueError("El sexo del lote debe ser 'MACHO' o 'HEMBRA'")
        return upper_v


class BatchDTO(BatchCreateDTO):
    id: UUID
    is_active: bool
    age_days: int

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# 3. REGISTRO DE PESAJES Y PESOS INDIVIDUALES
# ==============================================================================

class WeighingSampleCreateDTO(BaseModel):
    barn_id: UUID
    declared_sample_size: int = Field(gt=0, description="Total de aves declaradas para la muestra (ej. 100, 200, 300)")


class IndividualWeightEntryDTO(BaseModel):
    bird_sequence: int = Field(gt=0, description="Secuencia correlativa del ave (1, 2, ... N)")
    weight_kg: float = Field(gt=0, le=6.0, description="Peso individual en kilogramos")


class SampleWeightsBatchDTO(BaseModel):
    weights: List[IndividualWeightEntryDTO] = Field(min_length=1, description="Lista de pesos individuales registrados")


class WeighingSampleSummaryDTO(BaseModel):
    id: UUID
    barn_id: UUID
    batch_id: UUID
    declared_sample_size: int
    actual_sample_size: int
    average_weight: float = Field(description="Peso Promedio (x̄) en kg")
    std_deviation: Optional[float]
    min_weight: float
    max_weight: float
    origin_type: str  # 'REAL' o 'SIMULADO'
    status: str
    weighed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SimulateSampleDTO(BaseModel):
    barn_id: UUID
    sample_size: int = Field(default=200, gt=0, le=2000, description="Cantidad de aves a simular")
    expected_avg_weight: float = Field(default=2.350, gt=0.5, le=5.0, description="Peso promedio esperado en kg")
    std_deviation: float = Field(default=0.150, gt=0.01, le=1.0, description="Desviación estándar de pesos")


# ==============================================================================
# 4. ESPECIALES ENCONTRADOS Y MOVIMIENTOS FÍSICOS
# ==============================================================================

class SpecialFindingCreateDTO(BaseModel):
    barn_id: UUID
    quantity: int = Field(gt=0, description="Cantidad general de aves especiales encontradas")
    reason_catalog_id: Optional[UUID] = None
    evidence_url: Optional[str] = None
    notes: Optional[str] = None


class SpecialFindingDTO(SpecialFindingCreateDTO):
    id: UUID
    batch_id: UUID
    finding_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PhysicalMovementCreateDTO(BaseModel):
    barn_id: UUID
    movement_type: str = Field(description="MORTALIDAD_BAJA, TRASLADO_SALIDA, SACA_DESPACHO, AJUSTE_JUSTIFICADO")
    quantity: int = Field(gt=0)
    reason_catalog_id: Optional[UUID] = None
    notes: Optional[str] = None


class PhysicalMovementDTO(PhysicalMovementCreateDTO):
    id: UUID
    batch_id: UUID
    movement_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
