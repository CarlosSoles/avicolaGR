# ==============================================================================
# ROUTER FASTAPI DEL MÓDULO PECUARIA
# Archivo: backend/app/modules/pecuaria/presentation/router.py
# ==============================================================================

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role, AuthenticatedUser
from app.modules.pecuaria.application.dtos import (
    TablaGeneralSaldoResponse,
    FarmCreateDTO,
    FarmDTO,
    BarnCreateDTO,
    BarnDTO,
    BatchCreateDTO,
    BatchDTO,
    WeighingSampleCreateDTO,
    WeighingSampleSummaryDTO,
    SampleWeightsBatchDTO,
    SimulateSampleDTO,
    SpecialFindingCreateDTO,
    SpecialFindingDTO,
    PhysicalMovementCreateDTO,
    PhysicalMovementDTO,
)
from app.modules.pecuaria.application.service import PecuariaService

router = APIRouter(prefix="/pecuaria", tags=["Módulo Pecuaria"])


# ==============================================================================
# 1. TABLA GENERAL DE SALDO (VISTA CENTRAL)
# ==============================================================================
@router.get(
    "/tabla-general-saldo",
    response_model=TablaGeneralSaldoResponse,
    summary="Consultar Tabla General de Saldo de Galpones",
    description="""
    Retorna la vista consolidada de Pecuaria con las 7 columnas obligatorias:
    1. Granja (farm_name)
    2. Galpón (barn_number)
    3. Edad del ave en días (bird_age_days)
    4. Especiales cantidad general (specials_general_count)
    5. Saldo por galpón disponible (barn_balance_available)
    6. Peso promedio en kg (average_weight_kg)
    7. Sexo del lote (sex: MACHO, HEMBRA o MIXTO)
    """,
)
async def get_tabla_general_saldo(
    farm_id: Optional[UUID] = Query(None, description="Filtrar por ID de Granja"),
    sex: Optional[str] = Query(None, description="Filtrar por Sexo: MACHO, HEMBRA o MIXTO"),
    min_age: Optional[int] = Query(None, description="Edad mínima en días"),
    max_age: Optional[int] = Query(None, description="Edad máxima en días"),
    status: Optional[str] = Query(None, description="Estado del galpón: OPERATIVO, BLOQUEADO_SANITARIO"),
    db: AsyncSession = Depends(get_db),
    # Todos los roles autenticados pueden consultar la tabla de saldos
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return await PecuariaService.get_tabla_general_saldo(
        db=db,
        farm_id=farm_id,
        sex=sex,
        min_age=min_age,
        max_age=max_age,
        status=status,
    )


# ==============================================================================
# 2. GRANJAS, GALPONES Y LOTES
# ==============================================================================
@router.get("/farms", response_model=List[FarmDTO], summary="Listar Granjas Activas")
async def list_farms(
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return await PecuariaService.get_farms(db)


@router.post(
    "/farms",
    response_model=FarmDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva Granja",
    dependencies=[Depends(require_role(["admin_sistema", "supervisor_pecuario"]))],
)
async def create_farm(
    dto: FarmCreateDTO,
    db: AsyncSession = Depends(get_db),
):
    return await PecuariaService.create_farm(db, dto)


@router.post(
    "/barns",
    response_model=BarnDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo Galpón en una Granja",
    dependencies=[Depends(require_role(["admin_sistema", "supervisor_pecuario"]))],
)
async def create_barn(
    dto: BarnCreateDTO,
    db: AsyncSession = Depends(get_db),
):
    return await PecuariaService.create_barn(db, dto)


@router.post(
    "/batches",
    response_model=BatchDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Dar de alta un nuevo Lote en un Galpón",
    dependencies=[Depends(require_role(["admin_sistema", "supervisor_pecuario"]))],
)
async def create_batch(
    dto: BatchCreateDTO,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return await PecuariaService.create_batch(db, dto, current_user.id)


@router.patch(
    "/barns/{barn_id}/close",
    response_model=bool,
    summary="Cerrar un Galpón (ya no tiene venta y no aparecerá en la tabla)",
    dependencies=[Depends(require_role(["supervisor_pecuario", "admin_sistema"]))],
)
async def close_barn(
    barn_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return await PecuariaService.close_barn(db, barn_id, current_user.id)


# ==============================================================================
# 3. REGISTRO DE PESAJES Y PESOS INDIVIDUALES AVE POR AVE
# ==============================================================================
@router.post(
    "/samples",
    response_model=UUID,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar una nueva muestra de pesaje",
    dependencies=[Depends(require_role(["registrador_pecuario", "supervisor_pecuario"]))],
)
async def create_sample(
    dto: WeighingSampleCreateDTO,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return await PecuariaService.create_weighing_sample(db, dto, current_user.id)


@router.post(
    "/samples/{sample_id}/weights",
    response_model=WeighingSampleSummaryDTO,
    summary="Registrar pesos individuales ave por ave y calcular peso promedio",
    dependencies=[Depends(require_role(["registrador_pecuario", "supervisor_pecuario"]))],
)
async def record_individual_weights(
    sample_id: UUID,
    dto: SampleWeightsBatchDTO,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Recibe la lista de pesos individuales de la muestra, calcula automáticamente:
    - Peso Promedio (x̄)
    - Desviación estándar, Mínimo y Máximo
    Y actualiza la Tabla General de Saldo con el nuevo peso promedio del galpón.
    """
    return await PecuariaService.record_individual_weights(db, sample_id, dto, current_user.id)


@router.post(
    "/samples/simulate",
    response_model=WeighingSampleSummaryDTO,
    summary="Simular muestra de pesaje (Botón de pruebas para MVP)",
    dependencies=[Depends(require_role(["supervisor_pecuario", "admin_sistema"]))],
)
async def simulate_sample(
    dto: SimulateSampleDTO,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Genera pesos sintéticos identificados de forma indeleble como 'SIMULADO'.
    Permite calcular estadísticas en demostraciones sin respaldar ventas reales.
    """
    return await PecuariaService.simulate_sample(db, dto, current_user.id)


# ==============================================================================
# 4. REGISTRO DE ESPECIALES ENCONTRADOS (CANTIDAD GENERAL)
# ==============================================================================
@router.post(
    "/specials",
    response_model=SpecialFindingDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cantidad general de especiales encontrados en el galpón",
    dependencies=[Depends(require_role(["registrador_pecuario", "supervisor_pecuario"]))],
)
async def record_special_findings(
    dto: SpecialFindingCreateDTO,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Registra aves especiales (descartes / tara / no aptas).
    Se descuentan INMEDIATAMENTE del Saldo Disponible en la Tabla General de Saldo,
    manteniéndose en el conteo físico del galpón.
    """
    return await PecuariaService.record_special_findings(db, dto, current_user.id)


# ==============================================================================
# 5. REGISTRO DE MOVIMIENTOS FÍSICOS
# ==============================================================================
@router.post(
    "/movements",
    response_model=PhysicalMovementDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar movimiento físico (Mortalidad, Traslado o Salida por Saca)",
    dependencies=[Depends(require_role(["registrador_pecuario", "supervisor_pecuario"]))],
)
async def record_physical_movement(
    dto: PhysicalMovementCreateDTO,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return await PecuariaService.record_physical_movement(db, dto, current_user.id)

