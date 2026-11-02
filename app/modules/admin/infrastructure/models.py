# ==============================================================================
# MODELOS SQLALCHEMY DEL MÓDULO ADMINISTRACIÓN
# Archivo: backend/app/modules/admin/infrastructure/models.py
# ==============================================================================

from datetime import datetime
import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class UserProfileModel(Base):
    """Modelo de Perfil de Usuario con soporte para autenticación directa y Supabase."""
    __tablename__ = "users_profile"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=True, unique=True)
    password_hash = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin_sistema', 'registrador_pecuario', 'supervisor_pecuario', 'vendedor', 'gestor_comercial', 'gerente_comercial')",
            name="chk_user_role"
        ),
    )


class CatalogModel(Base):
    """Modelo de Catálogos Oficiales del Sistema."""
    __tablename__ = "catalogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_type = Column(String(50), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("catalog_type", "code", name="uq_catalogs_type_code"),
    )


class TechnicalParameterModel(Base):
    """Modelo de Parámetros Técnicos Configurables."""
    __tablename__ = "technical_parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    param_key = Column(String(100), nullable=False, unique=True)
    param_value = Column(Text, nullable=False)
    data_type = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    updated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users_profile.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "data_type IN ('INT', 'FLOAT', 'STRING', 'BOOLEAN', 'JSON')",
            name="chk_param_data_type"
        ),
    )


class UserScopeModel(Base):
    """Modelo de Ámbitos Territoriales y Operativos de Usuarios."""
    __tablename__ = "user_scopes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users_profile.id", ondelete="CASCADE"), nullable=False)
    scope_type = Column(String(50), nullable=False)
    target_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "scope_type", "target_id", name="uq_user_scopes_target"),
        CheckConstraint(
            "scope_type IN ('GRANJA', 'GALPON', 'ZONA_COMERCIAL')",
            name="chk_user_scope_type"
        ),
    )
