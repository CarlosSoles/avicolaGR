# ==============================================================================
# MODELOS SQLALCHEMY DEL MÓDULO COMERCIAL
# Archivo: backend/app/modules/comercial/infrastructure/models.py
# ==============================================================================

from datetime import datetime, date
import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Date,
    Integer,
    Numeric,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class ClientModel(Base):
    """Modelo de Clientes Autorizados del Sistema Comercial."""
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_name = Column(String(150), nullable=False)
    tax_id = Column(String(50), nullable=False, unique=True)
    zone_code = Column(String(50), nullable=False)
    address = Column(Text, nullable=True)
    contact_phone = Column(String(50), nullable=True)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    preferred_min_weight = Column(Numeric(4, 2), nullable=True)
    preferred_max_weight = Column(Numeric(4, 2), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class OrderModel(Base):
    """Modelo de Pedidos de Venta y Programación de Saca."""
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(30), nullable=False, unique=True)
    client_id = Column(UUID(as_uuid=True), nullable=True)
    client_name = Column(String(150), nullable=True)
    client_tax_id = Column(String(50), nullable=True)

    seller_user_id = Column(UUID(as_uuid=True), nullable=True)
    seller_username = Column(String(100), nullable=True)
    seller_full_name = Column(String(150), nullable=True)

    zone_code = Column(String(50), nullable=False)
    target_delivery_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="REGISTRADO")

    requested_quantity = Column(Integer, nullable=False, default=3000)
    allocated_quantity = Column(Integer, nullable=False, default=0)
    # Densidad de carga: aves por jaula (7-12). Las jaulas se derivan de este valor.
    density_birds_per_cage = Column(Integer, nullable=False, default=8)
    min_weight_kg = Column(Numeric(4, 2), nullable=False, default=2.20)
    max_weight_kg = Column(Numeric(4, 2), nullable=False, default=2.50)
    sex_preference = Column(String(15), default="INDISTINTO")

    estimated_total_kg = Column(Numeric(10, 2), nullable=True)
    estimated_cages = Column(Integer, nullable=True)

    suggested_farm_code = Column(String(20), nullable=True)
    suggested_barn_code = Column(String(20), nullable=True)
    assigned_farm_code = Column(String(20), nullable=True)
    assigned_barn_code = Column(String(20), nullable=True)

    is_split_parent = Column(Boolean, default=False)
    is_split_child = Column(Boolean, default=False)
    parent_order_id = Column(UUID(as_uuid=True), nullable=True)
    original_requested_quantity = Column(Integer, nullable=True)

    transport_assigned = Column(Boolean, default=False)
    transport_truck_id = Column(String(50), nullable=True)
    transport_plate = Column(String(20), nullable=True)
    transport_model = Column(String(100), nullable=True)
    transport_driver_name = Column(String(150), nullable=True)
    transport_driver_phone = Column(String(50), nullable=True)
    transport_crew = Column(String(100), nullable=True)
    transport_shift = Column(String(50), nullable=True)
    transport_capacity_cages = Column(Integer, nullable=True)
    transport_notes = Column(Text, nullable=True)
    transport_assigned_at = Column(DateTime(timezone=True), nullable=True)
    transport_assigned_by = Column(String(100), nullable=True)
    loading_slot_time = Column(String(100), nullable=True)

    dispatch_phase = Column(String(50), nullable=True)
    dispatch_phase_updated_at = Column(DateTime(timezone=True), nullable=True)

    audit_log = Column(JSONB, default=list, nullable=True)
    external_reference = Column(String(100), nullable=True)
    gestor_username = Column(String(100), nullable=True)
    gestor_observation = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    delivery_address = Column(Text, nullable=True)
    delivery_latitude = Column(Numeric(10, 7), nullable=True)
    delivery_longitude = Column(Numeric(10, 7), nullable=True)
    farm_contact_phone = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TransportVehicleModel(Base):
    """Modelo de Vehículos de Transporte y Distribución."""
    __tablename__ = "transport_vehicles"

    id = Column(String(50), primary_key=True)
    plate = Column(String(20), nullable=False, unique=True)
    model = Column(String(100), nullable=True)
    capacity_cages = Column(Integer, default=450, nullable=False)
    capacity_birds = Column(Integer, default=3600, nullable=False)
    driver_name = Column(String(150), nullable=False)
    driver_phone = Column(String(50), nullable=False)
    default_crew = Column(String(100), nullable=True)
    shift = Column(String(50), default="Madrugada (02:00 - 08:00)", nullable=True)
    zone_coverage = Column(JSONB, default=list, nullable=True)
    status = Column(String(30), default="DISPONIBLE", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

