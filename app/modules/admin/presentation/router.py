# ==============================================================================
# ROUTER DE ADMINISTRACIÓN Y AUTENTICACIÓN
# Archivo: backend/app/modules/admin/presentation/router.py
# ==============================================================================

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
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

# Router de notificaciones leídas por usuario
notifications_router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


class NotificationReadRequest(BaseModel):
    keys: List[str]
    read: bool = True


class NotificationResponse(BaseModel):
    id: str
    category: str
    type: str
    title: str
    description: str
    badge: Optional[str] = None
    farm_code: Optional[str] = None
    order_id: Optional[str] = None
    created_at: datetime
    read: bool = False


@notifications_router.get(
    "",
    response_model=List[NotificationResponse],
    summary="Listar notificaciones del usuario",
)
async def list_notifications(
    limit: int = 50,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Notificaciones generadas por eventos, visibles por rol o por usuario específico."""
    res = await db.execute(
        text("""
            SELECT n.id::text, n.category, n.type, n.title, n.description, n.badge,
                   n.farm_code, n.order_id::text, n.created_at,
                   (r.notification_key IS NOT NULL) AS is_read
            FROM public.notifications n
            LEFT JOIN public.notification_reads r
                   ON r.notification_key = n.id::text
                  AND r.user_id = CAST(:uid AS uuid)
            WHERE (n.target_user_id = CAST(:uid AS uuid))
               OR (n.target_user_id IS NULL AND CAST(:role AS text) = ANY(n.target_roles))
            ORDER BY n.created_at DESC
            LIMIT :lim
        """),
        {"uid": str(current_user.id), "role": current_user.role, "lim": max(1, min(limit, 200))},
    )
    return [
        {
            "id": row[0],
            "category": row[1],
            "type": row[2],
            "title": row[3],
            "description": row[4],
            "badge": row[5],
            "farm_code": row[6],
            "order_id": row[7],
            "created_at": row[8],
            "read": bool(row[9]),
        }
        for row in res.fetchall()
    ]


@notifications_router.get(
    "/reads",
    response_model=List[str],
    summary="Listar notificaciones leídas por el usuario",
)
async def list_notification_reads(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve las claves de notificación que el usuario ya marcó como leídas."""
    res = await db.execute(
        text("SELECT notification_key FROM public.notification_reads WHERE user_id = CAST(:uid AS uuid)"),
        {"uid": str(current_user.id)},
    )
    return [row[0] for row in res.fetchall()]


@notifications_router.put(
    "/reads",
    summary="Marcar notificaciones como leídas o no leídas",
)
async def set_notification_reads(
    req: NotificationReadRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persiste el estado de lectura en la base de datos, por usuario."""
    if not req.keys:
        return {"updated": 0, "read": req.read}

    if req.read:
        await db.execute(
            text("""
                INSERT INTO public.notification_reads (user_id, notification_key)
                SELECT CAST(:uid AS uuid), k
                FROM unnest(CAST(:keys AS text[])) AS k
                ON CONFLICT (user_id, notification_key) DO NOTHING
            """),
            {"uid": str(current_user.id), "keys": req.keys},
        )
    else:
        await db.execute(
            text("""
                DELETE FROM public.notification_reads
                WHERE user_id = CAST(:uid AS uuid)
                  AND notification_key = ANY(CAST(:keys AS text[]))
            """),
            {"uid": str(current_user.id), "keys": req.keys},
        )

    await db.commit()
    return {"updated": len(req.keys), "read": req.read}


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

