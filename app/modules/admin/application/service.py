# ==============================================================================
# SERVICIO DE APLICACIÓN DEL MÓDULO ADMINISTRACIÓN
# Archivo: backend/app/modules/admin/application/service.py
# ==============================================================================

from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, delete
from fastapi import HTTPException, status

from app.modules.admin.infrastructure.models import UserProfileModel
from app.modules.admin.domain.schemas import (
    UserCreate,
    UserUpdate,
    UserProfileResponse,
    LoginRequest,
    LoginResponse,
    FarmCatalogItem,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.shared.infrastructure.notifier import notify

OFFICIAL_FARMS = [
    {"name": "Tradisa 1", "code": "TRAD1"},
    {"name": "Tradisa II", "code": "TRAD2"},
    {"name": "Pacifico 6", "code": "PACI6"},
    {"name": "San Jose 3", "code": "PAC67"},
    {"name": "San Jose 2", "code": "PACI7"},
    {"name": "Pacifico 1", "code": "PACI1"},
    {"name": "Pacifico 2", "code": "PACI2"},
    {"name": "San Jose 1", "code": "PACI5"},
    {"name": "Santa Isabel 2", "code": "SISA2"},
    {"name": "Semillero A", "code": "SEMIA"},
    {"name": "Santa Isabel 3", "code": "SISA3"},
    {"name": "Santa Isabel 1", "code": "SISA1"},
    {"name": "Semillero B", "code": "SEMIB"},
    {"name": "Nucleo 9", "code": "NUC-9"},
    {"name": "R4GB", "code": "R4G-B"},
    {"name": "Nucleo B", "code": "NUC-B"},
    {"name": "Esmeralda", "code": "ESMER"},
    {"name": "R4GC", "code": "R4G-C"},
    {"name": "R4GA", "code": "R4G-A"},
    {"name": "Quebaga", "code": "QBAGA"},
    {"name": "Puerto Mori 2", "code": "MORI2"},
    {"name": "507", "code": "507"},
    {"name": "Harco 2", "code": "HARC2"},
]


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_default_system_users(self) -> None:
        """Garantiza la existencia del administrador y de los vendedores oficiales del área comercial."""
        default_seed_users = [
            {
                "username": "admin",
                "email": "admin@avicolagr.com",
                "password": "admin 123",
                "full_name": "Administrador General",
                "role": "admin_sistema",
            },
            {
                "username": "areacomercial1",
                "email": "areacomercial@avicola.gr",
                "password": "123",
                "full_name": "Felipe",
                "role": "vendedor",
            },
            {
                "username": "vendedor1",
                "email": "jperez@avicola.gr",
                "password": "123",
                "full_name": "Juan Carlos Pérez Gálvez",
                "role": "vendedor",
            },
            {
                "username": "vendedor2",
                "email": "mrodriguez@avicola.gr",
                "password": "123",
                "full_name": "María Elena Rodríguez Soto",
                "role": "vendedor",
            },
            {
                "username": "gestor_comercial",
                "email": "gestorcomercial2@avicola.gr",
                "password": "123",
                "full_name": "Ramiro Vega Zabaleta",
                "role": "gestor_comercial",
            },
            {
                "username": "pecuaria1",
                "email": "pecuaria1@avicola.gr",
                "password": "123",
                "full_name": "Jorge Alfaro Chavez",
                "role": "registrador_pecuario",
            },
        ]

        for u in default_seed_users:
            stmt = select(UserProfileModel).where(
                or_(
                    func.lower(UserProfileModel.username) == u["username"],
                    func.lower(UserProfileModel.email) == u["email"],
                )
            )
            res = await self.db.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                new_u = UserProfileModel(
                    id=uuid4(),
                    username=u["username"],
                    email=u["email"],
                    password_hash=hash_password(u["password"]),
                    full_name=u["full_name"],
                    role=u["role"],
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(new_u)
            else:
                existing.full_name = u["full_name"]
                existing.role = u["role"]
                existing.is_active = True

        await self.db.commit()

    async def ensure_master_admin(self) -> UserProfileModel:
        """Garantiza la existencia del usuario administrador maestro (admin / admin 123) y usuarios oficiales."""
        await self.ensure_default_system_users()
        stmt = select(UserProfileModel).where(func.lower(UserProfileModel.username) == "admin")
        res = await self.db.execute(stmt)
        return res.scalar_one()

    async def authenticate(self, req: LoginRequest) -> LoginResponse:
        """Autenticación para el sistema en general."""
        clean_user = req.username.strip()
        if clean_user.startswith("@"):
            clean_user = clean_user[1:].strip()
        clean_pass = req.password

        # 1. Caso especial: Master Admin solicitado explícitamente
        if clean_user.lower() in ("admin", "admin@avicolagr.com") and clean_pass == "admin 123":
            admin = await self.ensure_master_admin()
            token = create_access_token(
                user_id=admin.id,
                email=admin.email,
                role=admin.role,
                username=admin.username,
                full_name=admin.full_name,
            )
            return LoginResponse(
                access_token=token,
                token_type="bearer",
                user=UserProfileResponse.model_validate(admin),
            )

        # 2. Búsqueda en base de datos por username o email
        stmt = select(UserProfileModel).where(
            or_(
                func.lower(UserProfileModel.username) == clean_user.lower(),
                func.lower(UserProfileModel.email) == clean_user.lower(),
            )
        )
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Su cuenta se encuentra inactiva. Contacte al Administrador.",
            )

        if not verify_password(clean_pass, user.password_hash or ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos.",
            )

        token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            username=user.username or user.email.split("@")[0],
            full_name=user.full_name,
        )

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user=UserProfileResponse.model_validate(user),
        )

    async def list_users(self) -> List[UserProfileResponse]:
        """Obtiene la lista de todos los usuarios registrados."""
        # Asegurar que el master admin exista primero
        await self.ensure_master_admin()

        stmt = select(UserProfileModel).order_by(UserProfileModel.created_at.desc())
        res = await self.db.execute(stmt)
        users = res.scalars().all()
        return [UserProfileResponse.model_validate(u) for u in users]

    async def create_user(self, dto: UserCreate) -> UserProfileResponse:
        """Crea un nuevo usuario en el sistema."""
        clean_username = dto.username.strip().lower()
        clean_email = dto.email.strip().lower()

        # Verificar unicidad de username y email
        stmt = select(UserProfileModel).where(
            or_(
                func.lower(UserProfileModel.username) == clean_username,
                func.lower(UserProfileModel.email) == clean_email,
            )
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            if existing.username and existing.username.lower() == clean_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El nombre de usuario '{dto.username}' ya está en uso.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El correo electrónico '{dto.email}' ya está registrado.",
            )

        new_user = UserProfileModel(
            id=uuid4(),
            username=clean_username,
            email=clean_email,
            password_hash=hash_password(dto.password),
            full_name=dto.full_name.strip(),
            role=dto.role,
            is_active=dto.is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        await notify(
            self.db,
            category="admin",
            type="seguridad",
            title=f"Nuevo usuario: @{clean_username}",
            description=f"Se creó la cuenta de {dto.full_name.strip()} con el rol {dto.role}.",
            target_roles=["admin_sistema"],
            badge="Seguridad",
        )

        return UserProfileResponse.model_validate(new_user)

    async def update_user(self, user_id: UUID, dto: UserUpdate) -> UserProfileResponse:
        """Actualiza la información de un usuario."""
        stmt = select(UserProfileModel).where(UserProfileModel.id == user_id)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado.",
            )

        if dto.full_name is not None:
            user.full_name = dto.full_name.strip()
        if dto.email is not None:
            user.email = dto.email.strip().lower()
        if dto.role is not None:
            user.role = dto.role
        if dto.is_active is not None:
            # No permitir desactivar al master admin
            if user.username == "admin" and not dto.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede desactivar la cuenta principal del Administrador.",
                )
            user.is_active = dto.is_active
        if dto.password:
            user.password_hash = hash_password(dto.password)

        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)

        return UserProfileResponse.model_validate(user)

    async def toggle_user_status(self, user_id: UUID, is_active: bool) -> UserProfileResponse:
        """Cambia el estado activo/inactivo de un usuario."""
        stmt = select(UserProfileModel).where(UserProfileModel.id == user_id)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado.",
            )

        if user.username == "admin" and not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede desactivar al usuario maestro admin.",
            )

        user.is_active = is_active
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)

        return UserProfileResponse.model_validate(user)

    async def delete_user(self, user_id: UUID) -> dict:
        """Elimina un usuario del sistema."""
        stmt = select(UserProfileModel).where(UserProfileModel.id == user_id)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado.",
            )

        if user.username == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cuenta principal de Administrador no puede ser eliminada.",
            )

        await self.db.execute(delete(UserProfileModel).where(UserProfileModel.id == user_id))
        await self.db.commit()

        return {"detail": f"Usuario {user.full_name} eliminado exitosamente."}

    async def list_farms(self) -> List[FarmCatalogItem]:
        """Retorna el catálogo oficial de 23 granjas sincronizado con la base de datos."""
        try:
            from sqlalchemy import text
            res = await self.db.execute(text("SELECT name, code, latitude, longitude FROM public.farms WHERE is_active = true ORDER BY name ASC"))
            rows = res.fetchall()
            if rows:
                db_coords = {r[1].upper(): (float(r[2]) if r[2] is not None else None, float(r[3]) if r[3] is not None else None) for r in rows}
                for f in OFFICIAL_FARMS:
                    code_up = f["code"].upper()
                    if code_up in db_coords:
                        f["latitude"] = db_coords[code_up][0]
                        f["longitude"] = db_coords[code_up][1]
        except Exception as e:
            print(f"Error consultando granjas en BD: {e}")

        return [
            FarmCatalogItem(
                name=f["name"],
                code=f["code"],
                barns_count=10,
                status="OPERATIVO",
                latitude=f.get("latitude"),
                longitude=f.get("longitude"),
            )
            for f in OFFICIAL_FARMS
        ]

    async def update_farm_coordinates(
        self, farm_code: str, lat: Optional[float], lng: Optional[float]
    ) -> FarmCatalogItem:
        """Actualiza las coordenadas GPS (Google Maps) de una granja."""
        matched = None
        for f in OFFICIAL_FARMS:
            if f["code"].upper() == farm_code.upper():
                f["latitude"] = lat
                f["longitude"] = lng
                matched = f
                break

        if not matched:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Granja con código '{farm_code}' no encontrada.",
            )

        try:
            from sqlalchemy import text
            result = await self.db.execute(
                text("UPDATE public.farms SET latitude = :lat, longitude = :lng WHERE UPPER(code) = :code"),
                {"lat": lat, "lng": lng, "code": farm_code.upper()},
            )
            if result.rowcount == 0:
                await self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"La granja '{farm_code}' no existe en la base de datos.",
                )
            await self.db.commit()
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            print(f"[AdminService] Error guardando coordenadas de {farm_code}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudieron guardar las coordenadas en la base de datos. Intente nuevamente.",
            )

        return FarmCatalogItem(
            name=matched["name"],
            code=matched["code"],
            barns_count=10,
            status="OPERATIVO",
            latitude=matched.get("latitude"),
            longitude=matched.get("longitude"),
        )

