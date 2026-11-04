# ==============================================================================
# ESQUEMAS PYDANTIC DEL MÓDULO ADMINISTRACIÓN
# Archivo: backend/app/modules/admin/domain/schemas.py
# ==============================================================================

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario o correo electrónico")
    password: str = Field(..., description="Contraseña de acceso")


class UserProfileResponse(BaseModel):
    id: UUID
    username: Optional[str] = None
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Identificador único de usuario")
    email: str = Field(..., description="Correo electrónico corporativo")
    password: str = Field(..., min_length=4, description="Contraseña inicial")
    full_name: str = Field(..., min_length=3, max_length=150, description="Nombre completo del colaborador")
    role: str = Field(..., description="Rol operativo o comercial en el sistema")
    is_active: bool = Field(default=True, description="Estado de acceso activo")


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserStatusUpdate(BaseModel):
    is_active: bool


class FarmCatalogItem(BaseModel):
    code: str
    name: str
    barns_count: int = 10
    status: str = "OPERATIVO"
    zone_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class FarmCoordinatesUpdate(BaseModel):
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitud WGS84")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitud WGS84")

