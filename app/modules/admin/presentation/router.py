# ==============================================================================
# ROUTER DE ADMINISTRACIÓN Y AUTENTICACIÓN
# Archivo: backend/app/modules/admin/presentation/router.py
# ==============================================================================

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role, AuthenticatedUser
from app.modules.admin.application.service import AdminService
from app.modules.admin.domain.schemas import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserUpdate,
    UserStatusUpdate,
    UserProfileResponse,
    FarmCatalogItem,
    FarmCoordinatesUpdate,
)

# Router para autenticación
auth_router = APIRouter(prefix="/auth", tags=["Autenticación del Sistema"])

# Router para administración (usuarios y configuración)
admin_router = APIRouter(prefix="/admin", tags=["Módulo de Administración & Usuarios"])


# ------------------------------------------------------------------------------
# ENDPOINTS DE AUTENTICACIÓN
# ------------------------------------------------------------------------------

@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="Inicio de Sesión General",
    description="Permite iniciar sesión con usuario (ej. 'admin') o correo electrónico y contraseña.",
)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.authenticate(req)


@auth_router.get(
    "/me",
    summary="Perfil del Usuario Autenticado",
    description="Devuelve el perfil del usuario actual a partir del token JWT.",
)
async def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role,
        "scopes": current_user.scopes,
    }


# ------------------------------------------------------------------------------
# ENDPOINTS DE GESTIÓN DE USUARIOS (MÓDULO ADMIN)
# ------------------------------------------------------------------------------

@admin_router.get(
    "/users",
    response_model=List[UserProfileResponse],
    summary="Listar Usuarios del Sistema",
    description="Exclusivo para el Administrador del Sistema. Lista todas las cuentas operativas y comerciales.",
)
async def list_users(
    current_user: AuthenticatedUser = Depends(require_role(["admin_sistema"])),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_users()


@admin_router.post(
    "/users",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar Nuevo Usuario",
    description="Crea una nueva cuenta de usuario con credenciales y rol específico.",
)
async def create_user(
    dto: UserCreate,
    current_user: AuthenticatedUser = Depends(require_role(["admin_sistema"])),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.create_user(dto)


@admin_router.put(
    "/users/{user_id}",
    response_model=UserProfileResponse,
    summary="Modificar Usuario",
    description="Actualiza el rol, correo, nombre o contraseña de un usuario.",
)
async def update_user(
    user_id: UUID,
    dto: UserUpdate,
    current_user: AuthenticatedUser = Depends(require_role(["admin_sistema"])),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.update_user(user_id, dto)


@admin_router.patch(
    "/users/{user_id}/status",
    response_model=UserProfileResponse,
    summary="Activar o Desactivar Usuario",
    description="Cambia el estado de acceso de un colaborador.",
)
async def toggle_status(
    user_id: UUID,
    dto: UserStatusUpdate,
    current_user: AuthenticatedUser = Depends(require_role(["admin_sistema"])),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.toggle_user_status(user_id, dto.is_active)


@admin_router.delete(
    "/users/{user_id}",
    summary="Eliminar Usuario",
    description="Remueve una cuenta de usuario (no se permite sobre el usuario admin).",
)
async def delete_user(
    user_id: UUID,
    current_user: AuthenticatedUser = Depends(require_role(["admin_sistema"])),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.delete_user(user_id)


@admin_router.get(
    "/farms",
    response_model=List[FarmCatalogItem],
    summary="Catálogo Oficial de Granjas",
    description="Lista las 23 granjas autorizadas con sus códigos de negocio.",
)
async def list_farms(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_farms()


@admin_router.put(
    "/farms/{farm_code}/coordinates",
    response_model=FarmCatalogItem,
    summary="Actualizar Coordenadas de Granja",
    description="Actualiza las coordenadas GPS (Latitud y Longitud de Google Maps) de una granja.",
)
async def update_farm_coordinates(
    farm_code: str,
    coords: FarmCoordinatesUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.update_farm_coordinates(farm_code, coords.latitude, coords.longitude)

