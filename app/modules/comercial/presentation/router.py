# ==============================================================================
# ROUTER FASTAPI DEL MÓDULO COMERCIAL
# Archivo: backend/app/modules/comercial/presentation/router.py
# ==============================================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role, AuthenticatedUser
from app.modules.comercial.domain.schemas import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    OrderCreate,
    OrderActionRequest,
    OrderResponse,
    ProgramacionTransporteResponse,
    TransportVehicle,
    AssignTransportRequest,
    UpdateDispatchPhaseRequest,
    UpdateDensityRequest,
)
from app.modules.comercial.application.service import ComercialService

router = APIRouter(prefix="/comercial", tags=["Módulo Comercial"])

# Roles con visibilidad total de la cartera comercial
FULL_VISIBILITY_ROLES = ("admin_sistema", "gestor_comercial", "gerente_comercial")


def _scoped_seller(current_user: AuthenticatedUser, requested: Optional[str]) -> Optional[str]:
    """
    Aísla la cartera: un vendedor solo puede consultar sus propios pedidos,
    sin importar el parámetro 'seller' que envíe el cliente.
    """
    if current_user.role in FULL_VISIBILITY_ROLES:
        return requested
    if current_user.role == "vendedor":
        return current_user.username or current_user.email
    return requested


async def _load_order_scoped(
    order_id: str,
    current_user: AuthenticatedUser,
    db: AsyncSession,
) -> OrderResponse:
    """
    Carga un pedido y valida la propiedad cuando el usuario es vendedor.
    Devuelve 404 (no 403) para no revelar la existencia de pedidos ajenos.
    """
    order = await ComercialService.get_order_by_id(order_id, db=db)
    if current_user.role == "vendedor":
        me = current_user.username or current_user.email or ""
        owner = order.seller_username or ""
        if owner and owner != me:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido '{order_id}' no encontrado.",
            )
    return order


# ==============================================================================
# 1. CLIENTES AUTORIZADOS
# ==============================================================================
@router.get(
    "/clients",
    response_model=List[ClientResponse],
    summary="Listar clientes autorizados",
)
async def list_clients(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna el catálogo de clientes autorizados para la captura de pedidos."""
    return await ComercialService.get_clients(db=db)


@router.post(
    "/clients",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo cliente",
)
async def create_client(
    client_in: ClientCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra un nuevo cliente en el catálogo comercial."""
    return await ComercialService.create_client(client_in, db=db)


@router.put(
    "/clients/{client_id}",
    response_model=ClientResponse,
    summary="Actualizar ficha de un cliente",
)
async def update_client(
    client_id: str,
    client_in: ClientUpdate,
    current_user: AuthenticatedUser = Depends(
        require_role(["vendedor", "gestor_comercial", "gerente_comercial", "admin_sistema"])
    ),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza los datos del cliente, incluidas su dirección y coordenadas de entrega."""
    return await ComercialService.update_client(client_id, client_in, db=db)


# ==============================================================================
# 2. PEDIDOS Y PROGRAMACIÓN
# ==============================================================================
@router.get(
    "/orders",
    response_model=List[OrderResponse],
    summary="Listar pedidos y programación de saca",
)
async def list_orders(
    status: Optional[str] = Query(None, description="Filtrar por estado: REGISTRADO, APROBADO_RESERVADO, CON_OBSERVACION, etc."),
    zone: Optional[str] = Query(None, description="Filtrar por zona comercial: NORTE, CENTRO, SUR, METROPOLITANA"),
    seller: Optional[str] = Query(None, description="Filtrar por usuario vendedor"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna la lista de pedidos para el Área Comercial y la Programación.
    El vendedor solo ve su propia cartera; el Gestor Comercial revisa toda la cola.
    """
    return await ComercialService.get_orders(
        status_filter=status,
        zone_filter=zone,
        seller_username=_scoped_seller(current_user, seller),
        db=db,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Consultar detalle de un pedido",
)
async def get_order(
    order_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene el detalle completo de un pedido comercial (el vendedor solo los suyos)."""
    return await _load_order_scoped(order_id, current_user, db)


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar nuevo pedido de venta",
)
async def create_order(
    order_in: OrderCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Registra un nuevo pedido de venta en el sistema comercial con persistencia en Supabase.
    """
    seller_id = str(current_user.id)
    seller_name = current_user.username or current_user.email or "vendedor"
    return await ComercialService.create_order(
        order_in=order_in,
        seller_user_id=seller_id,
        seller_username=seller_name,
        db=db,
    )


# ==============================================================================
# 3. ACCIONES EXCLUSIVAS DEL GESTOR COMERCIAL (APROBAR, OBSERVAR, CANCELAR)
# ==============================================================================
@router.post(
    "/orders/{order_id}/aprobar",
    response_model=OrderResponse,
    summary="Aprobar y reservar pedido (Acción exclusiva del Gestor Comercial)",
)
@router.post(
    "/orders/{order_id}/dar-ok",
    response_model=OrderResponse,
    include_in_schema=False,
)
async def aprobar_order(
    order_id: str,
    action_req: OrderActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    El Gestor Comercial evalúa la disponibilidad pecuaria y aprueba formalmente el pedido,
    asignando el galpón de origen y reservando las aves para saca.
    """
    gestor_name = current_user.username or "gestor_comercial"
    return await ComercialService.aprobar_pedido(
        order_id=order_id,
        user_role=current_user.role,
        gestor_username=gestor_name,
        action_req=action_req,
        db=db,
    )


@router.post(
    "/orders/{order_id}/observar",
    response_model=OrderResponse,
    summary="Devolver pedido con observación al vendedor",
)
async def observar_order(
    order_id: str,
    action_req: OrderActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    El Gestor Comercial devuelve el pedido con una observación o propuesta de ajuste de fecha/rango.
    """
    gestor_name = current_user.username or "gestor_comercial"
    return await ComercialService.observar_pedido(
        order_id=order_id,
        user_role=current_user.role,
        gestor_username=gestor_name,
        action_req=action_req,
        db=db,
    )


@router.post(
    "/orders/{order_id}/cancelar",
    response_model=OrderResponse,
    summary="Cancelar pedido comercial",
)
async def cancel_order(
    order_id: str,
    action_req: OrderActionRequest,
    current_user: AuthenticatedUser = Depends(
        require_role(["vendedor", "gestor_comercial", "gerente_comercial", "admin_sistema"])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancela un pedido comercial.
    El vendedor solo puede cancelar pedidos propios y que aún no tengan reserva en firme.
    """
    order = await _load_order_scoped(order_id, current_user, db)

    if current_user.role == "vendedor" and order.status not in (
        "BORRADOR",
        "REGISTRADO",
        "CON_OBSERVACION",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "El pedido ya tiene una reserva aprobada por el Gestor Comercial. "
                "Solicite la cancelación al Gestor Comercial."
            ),
        )

    return await ComercialService.cancelar_pedido(
        order_id=order_id,
        reason=action_req.observation,
        db=db,
    )


# ==============================================================================
# 4. HOJA DE PROGRAMACIÓN DIARIA Y TRANSPORTE
# ==============================================================================
@router.get(
    "/programacion-transporte",
    response_model=ProgramacionTransporteResponse,
    summary="Obtener Hoja de Programación Diaria para Transporte (pedidos aprobados)",
)
async def get_programacion_transporte(
    delivery_date: Optional[str] = Query(None, description="Fecha de saca (YYYY-MM-DD)"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna el consolidado de pedidos aprobados con galpón asignado y aves reservadas,
    calculando tonelaje, jaulas y camiones para la cuadrilla de saca y choferes de transporte.
    """
    return await ComercialService.get_programacion_transporte(
        delivery_date=delivery_date,
        db=db,
        seller_username=_scoped_seller(current_user, None),
    )


# ==============================================================================
# 5. ASIGNACIÓN Y FLOTA DE TRANSPORTE DE DISTRIBUCIÓN
# ==============================================================================
@router.get(
    "/transport/vehicles",
    response_model=List[TransportVehicle],
    summary="Listar flota de camiones de transporte del área de distribución",
)
async def list_transport_vehicles(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna la flota de camiones y choferes disponibles para la programación de saca."""
    return await ComercialService.get_transport_vehicles(db=db)


@router.post(
    "/orders/{order_id}/assign-transport",
    response_model=OrderResponse,
    summary="Designar vehículo y chofer de transporte al pedido (Gestor Comercial)",
)
async def assign_transport(
    order_id: str,
    transport_req: AssignTransportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Designa formalmente la unidad de transporte, conductor, turno y cuadrilla a un pedido aprobado.
    Acción exclusiva del Gestor Comercial.
    """
    gestor_name = current_user.username or "gestor_comercial"
    return await ComercialService.assign_transport_to_order(
        order_id=order_id,
        user_role=current_user.role,
        gestor_username=gestor_name,
        transport_req=transport_req,
        db=db,
    )


@router.post(
    "/orders/{order_id}/unassign-transport",
    response_model=OrderResponse,
    summary="Liberar transporte asignado a un pedido (Gestor Comercial)",
)
async def unassign_transport(
    order_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Libera el transporte asignado a un pedido para permitir reasignar una nueva unidad.
    """
    gestor_name = current_user.username or "gestor_comercial"
    return await ComercialService.unassign_transport_from_order(
        order_id=order_id,
        user_role=current_user.role,
        gestor_username=gestor_name,
        db=db,
    )


@router.patch(
    "/orders/{order_id}/dispatch-phase",
    response_model=OrderResponse,
    summary="Avanzar o actualizar la fase del ciclo de vida del despacho (4 Fases)",
)
async def update_dispatch_phase(
    order_id: str,
    phase_req: UpdateDispatchPhaseRequest,
    current_user: AuthenticatedUser = Depends(
        require_role(["gestor_comercial", "gerente_comercial", "admin_sistema"])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualiza la fase del ciclo de vida del despacho:
    - TRANSPORTE_ASIGNADO
    - EN_GRANJA_CARGANDO
    - EN_TRANSITO
    - ENTREGADO_CONFORME
    """
    username = current_user.username or "gestor_comercial"
    return await ComercialService.update_dispatch_phase(
        order_id=order_id,
        user_role=current_user.role,
        username=username,
        dispatch_phase=phase_req.dispatch_phase,
        notes=phase_req.notes,
        db=db,
        user_id=current_user.id,
    )


@router.patch(
    "/orders/{order_id}/density",
    response_model=OrderResponse,
    summary="Ajustar la densidad de carga del pedido (aves por jaula)",
)
async def update_order_density(
    order_id: str,
    density_req: UpdateDensityRequest,
    current_user: AuthenticatedUser = Depends(
        require_role(["vendedor", "gestor_comercial", "gerente_comercial", "admin_sistema"])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Ajusta la densidad de carga (7 a 12 aves por jaula) y recalcula las jaulas del pedido.
    Solo permitido antes de que el despacho entre en tránsito.
    """
    username = current_user.username or "gestor_comercial"
    # El vendedor solo puede ajustar la densidad de sus propios pedidos
    await _load_order_scoped(order_id, current_user, db)
    return await ComercialService.update_order_density(
        order_id=order_id,
        density_birds_per_cage=density_req.density_birds_per_cage,
        user_role=current_user.role,
        username=username,
        db=db,
    )
