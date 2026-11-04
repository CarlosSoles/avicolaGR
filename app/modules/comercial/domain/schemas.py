# ==============================================================================
# ESQUEMAS Y DTOs DEL MÓDULO COMERCIAL
# Archivo: backend/app/modules/comercial/domain/schemas.py
# ==============================================================================

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AuditLogEntry(BaseModel):
    id: str
    action: str = Field(..., description="Tipo de acción: CREADO | OBSERVADO | CORREGIDO | APROBADO_RESERVADO | TRANSPORTE_ASIGNADO | FASE_ACTUALIZADA | FRACCIONADO")
    actor_username: str
    actor_role: str
    timestamp: str
    description: str
    details: Optional[Dict[str, Any]] = None


class ClientBase(BaseModel):
    business_name: str = Field(..., description="Razón Social o Nombre del Cliente")
    tax_id: str = Field(..., description="RUC o DNI")
    zone_code: str = Field(..., description="Zona habitual de entrega (ej: NORTE, CENTRO, SUR, METROPOLITANA)")
    address: Optional[str] = Field(None, description="Dirección o punto de entrega")
    contact_phone: Optional[str] = Field(None, description="Teléfono de contacto")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitud WGS84 del punto de entrega habitual")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitud WGS84 del punto de entrega habitual")
    preferred_min_weight: Optional[float] = Field(None, description="Peso mínimo preferente en kg")
    preferred_max_weight: Optional[float] = Field(None, description="Peso máximo preferente en kg")
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    """Actualización parcial de la ficha del cliente (solo se aplican los campos enviados)."""

    business_name: Optional[str] = None
    tax_id: Optional[str] = None
    zone_code: Optional[str] = None
    address: Optional[str] = None
    contact_phone: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    preferred_min_weight: Optional[float] = None
    preferred_max_weight: Optional[float] = None
    is_active: Optional[bool] = None


class ClientResponse(ClientBase):
    id: str
    created_at: str


class OrderCreate(BaseModel):
    client_id: Optional[str] = Field(None, description="ID del cliente si existe en catálogo")
    client_name: str = Field(..., description="Nombre o razón social del cliente")
    client_tax_id: Optional[str] = Field(None, description="RUC o documento del cliente")
    seller_full_name: Optional[str] = Field(None, description="Nombre completo del vendedor")
    zone_code: str = Field("METROPOLITANA", description="Zona comercial de entrega")
    target_delivery_date: str = Field(..., description="Fecha requerida de entrega (YYYY-MM-DD)")
    requested_quantity: int = Field(..., gt=0, description="Cantidad total de aves solicitadas")
    density_birds_per_cage: int = Field(
        8,
        ge=7,
        le=12,
        description="Densidad de carga en aves por jaula (7-12). Define cuántas jaulas requiere el pedido.",
    )
    min_weight_kg: float = Field(..., gt=0, description="Peso mínimo requerido en kg")
    max_weight_kg: float = Field(..., gt=0, description="Peso máximo requerido en kg")
    sex_preference: str = Field("INDISTINTO", description="Preferencia de sexo: MACHO, HEMBRA o INDISTINTO")
    suggested_farm_code: Optional[str] = Field(None, description="Código de granja orientativa de Pecuaria")
    suggested_barn_code: Optional[str] = Field(None, description="Código de galpón orientativo de Pecuaria")
    external_reference: Optional[str] = Field(None, description="Orden de Compra u OC del cliente")
    notes: Optional[str] = Field(None, description="Observaciones comerciales")
    delivery_address: Optional[str] = Field(None, description="Dirección o punto de entrega físico")
    delivery_latitude: Optional[float] = Field(None, description="Latitud Google Maps del punto de entrega")
    delivery_longitude: Optional[float] = Field(None, description="Longitud Google Maps del punto de entrega")
    is_draft: bool = False


class OrderActionRequest(BaseModel):
    observation: Optional[str] = Field(None, description="Motivo u observación del Gestor Comercial")
    farm_code: Optional[str] = Field(None, description="Código de granja asignada formalmente")
    barn_code: Optional[str] = Field(None, description="Código de galpón asignado formalmente")
    allocated_quantity: Optional[int] = Field(None, description="Cantidad de aves reservadas de este galpón")
    density_birds_per_cage: Optional[int] = Field(
        None,
        ge=7,
        le=12,
        description="Ajuste de la densidad de carga (aves por jaula) al momento de aprobar",
    )
    force_reservation: bool = Field(
        False,
        description="Permite reservar aunque el saldo del galpón sea insuficiente (solo admin/gerente)",
    )
    force_reason: Optional[str] = Field(None, description="Motivo de la reserva forzada")
    split_remaining: bool = Field(False, description="Genera automáticamente una orden fraccionada con el saldo restante")
    split_delivery_date: Optional[str] = Field(None, description="Fecha de entrega para el saldo restante fraccionado")


class UpdateDensityRequest(BaseModel):
    density_birds_per_cage: int = Field(..., ge=7, le=12, description="Nueva densidad de carga en aves por jaula")


class OrderResponse(BaseModel):
    id: str
    order_number: str
    client_id: Optional[str]
    client_name: str
    client_tax_id: Optional[str]
    seller_user_id: str
    seller_username: str
    seller_full_name: Optional[str] = None
    zone_code: str
    target_delivery_date: str
    requested_quantity: int
    allocated_quantity: int
    density_birds_per_cage: int = 8
    min_weight_kg: float
    max_weight_kg: float
    sex_preference: str = "INDISTINTO"
    estimated_total_kg: Optional[float] = None
    estimated_cages: Optional[int] = None
    suggested_farm_code: Optional[str]
    suggested_barn_code: Optional[str]
    assigned_farm_code: Optional[str]
    assigned_barn_code: Optional[str]
    status: str
    external_reference: Optional[str]
    gestor_observation: Optional[str]
    gestor_username: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str
    # Datos de Transporte y Distribución
    transport_assigned: bool = False
    transport_truck_id: Optional[str] = None
    transport_plate: Optional[str] = None
    transport_model: Optional[str] = None
    transport_driver_name: Optional[str] = None
    transport_driver_phone: Optional[str] = None
    transport_crew: Optional[str] = None
    transport_shift: Optional[str] = None
    transport_capacity_cages: Optional[int] = None
    transport_notes: Optional[str] = None
    transport_assigned_at: Optional[str] = None
    transport_assigned_by: Optional[str] = None
    loading_slot_time: Optional[str] = None
    # Ciclo de Vida del Despacho (Tracking de 4 Fases)
    dispatch_phase: Optional[str] = None
    dispatch_phase_updated_at: Optional[str] = None
    # Historial de Auditoría y Trazabilidad
    audit_log: List[AuditLogEntry] = Field(default_factory=list)
    # Fraccionamiento y Split de Pedidos
    is_split_parent: bool = False
    is_split_child: bool = False
    parent_order_id: Optional[str] = None
    original_requested_quantity: Optional[int] = None
    split_children_ids: List[str] = Field(default_factory=list)
    # Direcciones y contactos operativos
    delivery_address: Optional[str] = None
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    farm_contact_phone: Optional[str] = None


class UpdateDispatchPhaseRequest(BaseModel):
    dispatch_phase: str = Field(
        ...,
        description="Fase del ciclo de vida: TRANSPORTE_ASIGNADO | EN_GRANJA_CARGANDO | EN_TRANSITO | ENTREGADO_CONFORME",
    )
    notes: Optional[str] = None


class TransportVehicle(BaseModel):
    id: str
    plate: str = Field(..., description="Placa de rodaje de la unidad")
    model: str = Field(..., description="Tipo o modelo de vehículo de distribución")
    capacity_cages: int = Field(..., description="Capacidad máxima de jaulas")
    capacity_birds: int = Field(..., description="Capacidad orientativa en aves")
    driver_name: str = Field(..., description="Nombre del conductor / chofer titular")
    driver_phone: Optional[str] = Field(None, description="Teléfono de contacto del chofer")
    default_crew: Optional[str] = Field(None, description="Cuadrilla de atrape asignada habitualmente")
    zone_coverage: List[str] = Field(default_factory=list, description="Zonas que cubre el camión")
    status: str = Field("DISPONIBLE", description="Estado: DISPONIBLE, ASIGNADO, EN_MANTENIMIENTO")


class AssignTransportRequest(BaseModel):
    vehicle_id: str = Field(..., description="ID del vehículo de transporte del área de distribución")
    plate: Optional[str] = Field(None, description="Placa del vehículo")
    driver_name: Optional[str] = Field(None, description="Nombre del conductor asignado")
    driver_phone: Optional[str] = Field(None, description="Teléfono de contacto del conductor")
    crew_name: Optional[str] = Field(None, description="Cuadrilla de atrape asignada")
    shift: Optional[str] = Field("MADRUGADA", description="Turno de saca: MADRUGADA, MANANA, TARDE, NOCHE")
    loading_slot_time: Optional[str] = Field(None, description="Ventana horaria de carga en granja (Slotting nocturno)")
    transport_notes: Optional[str] = Field(None, description="Instrucciones especiales para el viaje y rampa")


class ProgramacionTransporteItem(BaseModel):
    order_id: str
    order_number: str
    target_delivery_date: str
    client_name: str
    client_tax_id: Optional[str] = None
    zone_code: str
    assigned_farm_code: str
    assigned_barn_code: str
    allocated_quantity: int
    density_birds_per_cage: int = 8
    estimated_cages: int
    estimated_total_kg: float
    estimated_tons: float
    sex_preference: str = "INDISTINTO"
    min_weight_kg: float
    max_weight_kg: float
    gestor_username: Optional[str] = None
    notes: Optional[str] = None
    external_reference: Optional[str] = None
    transport_assigned: bool = False
    transport_plate: Optional[str] = None
    transport_driver_name: Optional[str] = None
    transport_crew: Optional[str] = None
    transport_shift: Optional[str] = None


class ProgramacionTransporteResponse(BaseModel):
    delivery_date: Optional[str] = None
    total_orders: int
    total_birds: int
    total_cages: int
    total_tons: float
    estimated_trucks: int
    items: List[ProgramacionTransporteItem]

