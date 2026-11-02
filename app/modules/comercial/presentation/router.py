# ==============================================================================
# ROUTER FASTAPI DEL MÓDULO COMERCIAL
# Archivo: backend/app/modules/comercial/presentation/router.py
# ==============================================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, AuthenticatedUser
from app.modules.comercial.domain.schemas import (
    ClientCreate,
    ClientResponse,
    OrderCreate,
    OrderActionRequest,
    OrderResponse,
    ProgramacionTransporteResponse,
    TransportVehicle,
    AssignTransportRequest,
    UpdateDispatchPhaseRequest,
)
from app.modules.comercial.application.service import ComercialService

router = APIRouter(prefix="/comercial", tags=["Módulo Comercial"])


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
):
    """Retorna el catálogo de clientes autorizados para la captura de pedidos."""
    return ComercialService.get_clients()


@router.post(
    "/clients",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo cliente",
)
async def create_client(
    client_in: ClientCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Registra un nuevo cliente en el catálogo comercial."""
    return ComercialService.create_client(client_in)


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
):
    """
    Retorna la lista de pedidos para el Área Comercial y la Programación.
    Los vendedores pueden filtrar sus propios pedidos; el Gestor Comercial revisa toda la cola.
    """
    return ComercialService.get_orders(
        status_filter=status,
        zone_filter=zone,
        seller_username=seller,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Consultar detalle de un pedido",
)
async def get_order(
    order_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Obtiene el detalle completo de un pedido comercial."""
    return ComercialService.get_order_by_id(order_id)


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar nuevo pedido de venta",
)
async def create_order(
    order_in: OrderCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Registra un nuevo pedido de venta en el sistema comercial.
    Pasa a estado 'REGISTRADO' para que el Gestor Comercial evalúe la disponibilidad de Pecuaria y autorice la saca.
    """
    seller_id = str(current_user.id)
    seller_name = current_user.username or current_user.email or "vendedor"
    return ComercialService.create_order(
        order_in=order_in,
        seller_user_id=seller_id,
        seller_username=seller_name,
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
):
    """
    El Gestor Comercial evalúa la disponibilidad pecuaria y aprueba formalmente el pedido,
    asignando el galpón de origen y reservando las aves para saca.
    """
    gestor_name = current_user.username or "gestor_comercial"
    return ComercialService.aprobar_pedido(
        order_id=order_id,
        user_role=current_user.role,
        gestor_username=gestor_name,
        action_req=action_req,
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
):
    """
    El Gestor Comercial devuelve el pedido con una observación o propuesta de ajuste de fecha/rango.
    """
    gestor_name = current_user.username or "gestor_comercial"
    return ComercialService.observar_pedido(
        order_id=order_id,
        user_role=current_user.role,
        gestor_username=gestor_name,
        action_req=action_req,
    )


@router.post(
    "/orders/{order_id}/cancelar",
    response_model=OrderResponse,
    summary="Cancelar pedido comercial",
)
async def cancel_order(
    order_id: str,
    action_req: OrderActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Cancela un pedido comercial."""
    return ComercialService.cancelar_pedido(
        order_id=order_id,
        reason=action_req.observation,
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
):
    """
    Retorna el consolidado de pedidos aprobados con galpón asignado y aves reservadas,
    calculando tonelaje, jaulas y camiones para la cuadrilla de saca y choferes de transporte.
    """
    return ComercialService.get_programacion_transporte(delivery_date=delivery_date)


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
):
    """Retorna la flota de camiones y choferes disponibles para la programación de saca."""
    return ComercialService.get_transport_vehicles()


@router.post(
    "/orders/{order_id}/assign-transport",
    response_model=OrderResponse,
    summary="Designar vehículo y chofer de transporte al pedido (Gestor Comercial)",
)
async def assign_transport(
    order_id: str,
    transport_req: AssignTransportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Designa formalmente la unidad de transporte, conductor, turno y cuadrilla a un pedido aprobado.
    Acción exclusiva del Gestor Comercial.
    """
    gestor_name = current_user.username or "gestor_comercial"
    return ComercialService.assign_transport_to_order(
        order_id=order_id,
        user_role=current_user.role,
        gestor_username=gestor_name,
        transport_req=transport_req,
    )


@router.post(
    "/orders/{order_id}/unassign-transport",
    response_model=OrderResponse,
    summary="Liberar transporte asignado a un pedido (Gestor Comercial)",
)
async def unassign_transport(
    order_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Libera el transporte asignado a un pedido para permitir reasignar una nueva unidad.
    """
    return ComercialService.unassign_transport_from_order(
        order_id=order_id,
        user_role=current_user.role,
    )


@router.patch(
    "/orders/{order_id}/dispatch-phase",
    response_model=OrderResponse,
    summary="Avanzar o actualizar la fase del ciclo de vida del despacho (4 Fases)",
)
async def update_dispatch_phase(
    order_id: str,
    phase_req: UpdateDispatchPhaseRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Actualiza la fase del ciclo de vida del despacho:
    - TRANSPORTE_ASIGNADO
    - EN_GRANJA_CARGANDO
    - EN_TRANSITO
    - ENTREGADO_CONFORME
    """
    username = current_user.username or "gestor_comercial"
    return ComercialService.update_dispatch_phase(
        order_id=order_id,
        user_role=current_user.role,
        username=username,
        dispatch_phase=phase_req.dispatch_phase,
        notes=phase_req.notes,
    )

