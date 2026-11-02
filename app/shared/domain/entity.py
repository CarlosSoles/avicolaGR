# ==============================================================================
# CLASE BASE DE ENTIDAD DE DOMINIO
# Archivo: backend/app/shared/domain/entity.py
# ==============================================================================

from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


class BaseEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


