# ==============================================================================
# MODELOS SQLALCHEMY DEL MÓDULO PECUARIA
# Archivo: backend/app/modules/pecuaria/infrastructure/models.py
# ==============================================================================

from datetime import datetime, date
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    CheckConstraint,
    Computed,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class FarmModel(Base):
    """Modelo de Granjas Avícolas."""
    __tablename__ = "farms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)
    zone_code = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    barns = relationship("BarnModel", back_populates="farm", cascade="all, delete-orphan")


class BarnModel(Base):
    """Modelo de Galpones dentro de una Granja."""
    __tablename__ = "barns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id", ondelete="RESTRICT"), nullable=False)
    barn_number = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(String(30), default="OPERATIVO", nullable=False)
    block_reason_catalog_id = Column(UUID(as_uuid=True), ForeignKey("catalogs.id"), nullable=True)
    block_notes = Column(Text, nullable=True)
    blocked_at = Column(DateTime(timezone=True), nullable=True)
    blocked_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users_profile.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    farm = relationship("FarmModel", back_populates="barns")
    batches = relationship("BatchModel", back_populates="barn")
    inventory = relationship("BarnInventoryModel", back_populates="barn", uselist=False)

    __table_args__ = (
        UniqueConstraint("farm_id", "barn_number", name="uq_barns_farm_number"),
        CheckConstraint(
            "status IN ('OPERATIVO', 'BLOQUEADO_SANITARIO', 'PENDIENTE_REVISION', 'CERRADO')",
            name="chk_barn_status"
        ),
    )


class BatchModel(Base):
    """Modelo de Lotes de Aves alojados en un Galpón."""
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    barn_id = Column(UUID(as_uuid=True), ForeignKey("barns.id", ondelete="RESTRICT"), nullable=False)
    batch_code = Column(String(50), nullable=False, unique=True)
    hatch_date = Column(Date, nullable=False)  # Fecha de encaste/nacimiento para calcular edad
    initial_count = Column(Integer, nullable=False)
    sex = Column(String(10), nullable=False)  # 'MACHO', 'HEMBRA', 'MIXTO'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    barn = relationship("BarnModel", back_populates="batches")
    weighing_samples = relationship("WeighingSampleModel", back_populates="batch")
    special_findings = relationship("SpecialFindingModel", back_populates="batch")
    movements = relationship("PhysicalMovementModel", back_populates="batch")

    __table_args__ = (
        CheckConstraint("sex IN ('MACHO', 'HEMBRA', 'MIXTO')", name="chk_batch_sex"),
        CheckConstraint("initial_count > 0", name="chk_batch_initial_count_positive"),
    )

    @property
    def age_days(self) -> int:
        """Calcula dinámicamente la edad del ave en días a partir de la fecha de encaste."""
        if self.hatch_date:
            return (date.today() - self.hatch_date).days
        return 0


class BarnInventoryModel(Base):
    """
    Modelo de Inventario y Cantidades Comerciales por Galpón.
    Tabla central de alta concurrencia que respalda la Tabla General de Saldo.
    """
    __tablename__ = "barn_inventories"

    barn_id = Column(UUID(as_uuid=True), ForeignKey("barns.id", ondelete="RESTRICT"), primary_key=True)
    current_batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    physical_count = Column(Integer, nullable=False, default=0)
    specials_count = Column(Integer, nullable=False, default=0)  # Cantidad general de especiales
    reserved_count = Column(Integer, nullable=False, default=0)
    sold_pending_count = Column(Integer, nullable=False, default=0)
    
    # available_count es columna generada en BD (solo lectura)
    available_count = Column(
        Integer,
        Computed(
            "physical_count - specials_count - reserved_count - sold_pending_count",
            persisted=True,
        ),
        nullable=False,
    )
    
    last_average_weight = Column(Numeric(5, 3), nullable=True)  # Peso promedio (x̄) en kg
    version = Column(Integer, nullable=False, default=1)        # Control de concurrencia optimista
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relaciones
    barn = relationship("BarnModel", back_populates="inventory")
    batch = relationship("BatchModel")


class WeighingSampleModel(Base):
    """Modelo de Muestra de Pesaje Ave por Ave."""
    __tablename__ = "weighing_samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    barn_id = Column(UUID(as_uuid=True), ForeignKey("barns.id", ondelete="RESTRICT"), nullable=False)
    declared_sample_size = Column(Integer, nullable=False)
    actual_sample_size = Column(Integer, nullable=False, default=0)
    average_weight = Column(Numeric(5, 3), nullable=False)  # Peso Promedio (x̄)
    std_deviation = Column(Numeric(5, 3), nullable=True)
    min_weight = Column(Numeric(5, 3), nullable=False)
    max_weight = Column(Numeric(5, 3), nullable=False)
    origin_type = Column(String(20), nullable=False)  # 'REAL', 'SIMULADO'
    status = Column(String(20), nullable=False, default="COMPLETO")  # 'BORRADOR', 'COMPLETO', 'ANULADO'
    weighed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users_profile.id"), nullable=False)
    weighed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    batch = relationship("BatchModel", back_populates="weighing_samples")
    individual_weights = relationship(
        "IndividualWeightModel", 
        back_populates="sample", 
        cascade="all, delete-orphan", 
        order_by="IndividualWeightModel.bird_sequence"
    )

    __table_args__ = (
        CheckConstraint("origin_type IN ('REAL', 'SIMULADO')", name="chk_sample_origin_type"),
        CheckConstraint("status IN ('BORRADOR', 'COMPLETO', 'ANULADO')", name="chk_sample_status"),
    )


class IndividualWeightModel(Base):
    """Modelo de Pesaje Individual de cada Ave de la Muestra."""
    __tablename__ = "individual_weights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sample_id = Column(UUID(as_uuid=True), ForeignKey("weighing_samples.id", ondelete="CASCADE"), nullable=False)
    bird_sequence = Column(Integer, nullable=False)
    weight_kg = Column(Numeric(5, 3), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    sample = relationship("WeighingSampleModel", back_populates="individual_weights")

    __table_args__ = (
        UniqueConstraint("sample_id", "bird_sequence", name="uq_individual_weights_sample_sequence"),
        CheckConstraint("weight_kg > 0 AND weight_kg <= 6.000", name="chk_individual_weight_positive"),
    )


class SpecialFindingModel(Base):
    """Modelo de Registro de Especiales Encontrados (Cantidad General)."""
    __tablename__ = "special_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    barn_id = Column(UUID(as_uuid=True), ForeignKey("barns.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False)  # Cantidad general de especiales encontrados
    reason_catalog_id = Column(UUID(as_uuid=True), ForeignKey("catalogs.id"), nullable=True)
    evidence_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    reported_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users_profile.id"), nullable=False)
    finding_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    batch = relationship("BatchModel", back_populates="special_findings")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_special_findings_quantity_positive"),
    )


class PhysicalMovementModel(Base):
    """Modelo de Movimientos Físicos (Bajas, Traslados, Salidas por Saca, Ajustes)."""
    __tablename__ = "physical_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False)
    barn_id = Column(UUID(as_uuid=True), ForeignKey("barns.id", ondelete="RESTRICT"), nullable=False)
    movement_type = Column(String(30), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason_catalog_id = Column(UUID(as_uuid=True), ForeignKey("catalogs.id"), nullable=True)
    notes = Column(Text, nullable=True)
    performed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users_profile.id"), nullable=False)
    movement_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    batch = relationship("BatchModel", back_populates="movements")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_movement_quantity_positive"),
        CheckConstraint(
            "movement_type IN ('INGRESO_LOTE', 'MORTALIDAD_BAJA', 'TRASLADO_SALIDA', 'TRASLADO_INGRESO', 'SACA_DESPACHO', 'AJUSTE_JUSTIFICADO')",
            name="chk_movement_type"
        ),
    )

