# ==============================================================================
# SERVICIO DE APLICACIÓN DEL MÓDULO COMERCIAL
# Archivo: backend/app/modules/comercial/application/service.py
# ==============================================================================

import math
from typing import List, Optional, Dict, Any
from uuid import uuid4, UUID
from datetime import datetime, date
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, text
from sqlalchemy.orm.attributes import flag_modified

from app.modules.comercial.domain.schemas import (
    ClientCreate,
    ClientResponse,
    OrderCreate,
    OrderActionRequest,
    OrderResponse,
    ProgramacionTransporteItem,
    ProgramacionTransporteResponse,
    TransportVehicle,
    AssignTransportRequest,
)
from app.modules.comercial.infrastructure.models import (
    ClientModel,
    OrderModel,
    TransportVehicleModel,
)

# Catálogo predeterminado de respaldo
DEFAULT_CLIENTS = [
    {
        "id": "c1000000-0000-0000-0000-000000000001",
        "business_name": "Distribuidora Santa Anita S.A.C.",
        "tax_id": "20548963211",
        "zone_code": "CENTRO",
        "address": "Av. Nicolás Ayllón 3800, Mercado Mayorista Santa Anita (Rampa 2)",
        "contact_phone": "+51 987 654 321",
        "preferred_min_weight": 2.20,
        "preferred_max_weight": 2.50,
        "is_active": True,
        "created_at": "2026-10-01T08:00:00Z",
    },
    {
        "id": "c1000000-0000-0000-0000-000000000002",
        "business_name": "Pollerías Norky's Corp S.A.",
        "tax_id": "20100456789",
        "zone_code": "METROPOLITANA",
        "address": "Av. Javier Prado Este 2890, San Borja, Lima",
        "contact_phone": "+51 991 223 344",
        "preferred_min_weight": 2.10,
        "preferred_max_weight": 2.30,
        "is_active": True,
        "created_at": "2026-10-05T09:30:00Z",
    },
    {
        "id": "c1000000-0000-0000-0000-000000000003",
        "business_name": "Supermercados Metro / Cencosud Perú",
        "tax_id": "20456123987",
        "zone_code": "NORTE",
        "address": "Panamericana Norte Km 24.5, Los Olivos",
        "contact_phone": "+51 976 543 210",
        "preferred_min_weight": 2.30,
        "preferred_max_weight": 2.60,
        "is_active": True,
        "created_at": "2026-10-10T10:15:00Z",
    },
    {
        "id": "c1000000-0000-0000-0000-000000000004",
        "business_name": "Mercados del Norte Mayoristas S.A.C.",
        "tax_id": "20601234567",
        "zone_code": "NORTE",
        "address": "Mercado Unicachi Puesto 84, Comas",
        "contact_phone": "+51 954 321 876",
        "preferred_min_weight": 2.40,
        "preferred_max_weight": 2.70,
        "is_active": True,
        "created_at": "2026-10-12T11:00:00Z",
    },
    {
        "id": "c1000000-0000-0000-0000-000000000005",
        "business_name": "Avícola San Fernando Mayorista Sur",
        "tax_id": "20100045612",
        "zone_code": "SUR",
        "address": "Av. Pachacútec 1200, Villa El Salvador",
        "contact_phone": "+51 945 678 123",
        "preferred_min_weight": 2.20,
        "preferred_max_weight": 2.45,
        "is_active": True,
        "created_at": "2026-10-15T14:20:00Z",
    },
]

# Flota predeterminada
DEFAULT_VEHICLES = [
    {
        "id": "VH-001",
        "plate": "T8C-940",
        "model": "Camión Baranda 3 Ejes",
        "capacity_cages": 450,
        "capacity_birds": 3600,
        "driver_name": "Carlos Méndez Rojas",
        "driver_phone": "+51 984 123 456",
        "default_crew": "Cuadrilla Norte 1",
        "zone_coverage": ["NORTE", "CENTRO", "METROPOLITANA"],
        "status": "DISPONIBLE",
    },
    {
        "id": "VH-002",
        "plate": "V6B-821",
        "model": "Camión Plataforma 2 Ejes",
        "capacity_cages": 350,
        "capacity_birds": 2800,
        "driver_name": "José Luis Quispe",
        "driver_phone": "+51 992 345 678",
        "default_crew": "Cuadrilla Centro 2",
        "zone_coverage": ["CENTRO", "METROPOLITANA"],
        "status": "DISPONIBLE",
    },
    {
        "id": "VH-003",
        "plate": "W5A-712",
        "model": "Semirremolque Jaulero Pesado",
        "capacity_cages": 650,
        "capacity_birds": 5200,
        "driver_name": "Manuel Rodríguez Ramos",
        "driver_phone": "+51 977 456 789",
        "default_crew": "Cuadrilla Pesada Alpha",
        "zone_coverage": ["NORTE", "SUR", "CENTRO", "METROPOLITANA"],
        "status": "DISPONIBLE",
    },
    {
        "id": "VH-004",
        "plate": "F4K-915",
        "model": "Camión Baranda 3 Ejes",
        "capacity_cages": 450,
        "capacity_birds": 3600,
        "driver_name": "Roberto Sánchez Díaz",
        "driver_phone": "+51 981 567 890",
        "default_crew": "Cuadrilla Sur 1",
        "zone_coverage": ["SUR", "METROPOLITANA"],
        "status": "DISPONIBLE",
    },
    {
        "id": "VH-005",
        "plate": "B7Z-330",
        "model": "Camión Mediano 2 Ejes",
        "capacity_cages": 300,
        "capacity_birds": 2400,
        "driver_name": "David Paredes Vega",
        "driver_phone": "+51 965 678 901",
        "default_crew": "Cuadrilla Express",
        "zone_coverage": ["NORTE", "CENTRO"],
        "status": "DISPONIBLE",
    },
    {
        "id": "VH-006",
        "plate": "D9X-504",
        "model": "Semirremolque Jaulero 4 Ejes",
        "capacity_cages": 600,
        "capacity_birds": 4800,
        "driver_name": "Hugo Alarcón Castro",
        "driver_phone": "+51 953 789 012",
        "default_crew": "Cuadrilla Pesada Beta",
        "zone_coverage": ["NORTE", "SUR", "CENTRO", "METROPOLITANA"],
        "status": "DISPONIBLE",
    },
]

INITIAL_ORDERS = [
    {
        "id": "ord-0001",
        "order_number": "PED-2026-001",
        "client_id": "c1000000-0000-0000-0000-000000000001",
        "client_name": "Distribuidora Santa Anita S.A.C.",
        "client_tax_id": "20548963211",
        "seller_user_id": "u-seller-felipe",
        "seller_username": "areacomercial1",
        "seller_full_name": "Felipe",
        "zone_code": "CENTRO",
        "target_delivery_date": "2026-11-03",
        "requested_quantity": 4000,
        "allocated_quantity": 4000,
        "min_weight_kg": 2.20,
        "max_weight_kg": 2.50,
        "sex_preference": "MACHO",
        "estimated_total_kg": 9400.0,
        "estimated_cages": 500,
        "suggested_farm_code": "TRAD1",
        "suggested_barn_code": "G-01",
        "assigned_farm_code": "TRAD1",
        "assigned_barn_code": "G-01",
        "status": "APROBADO_RESERVADO",
        "external_reference": "OC-4890",
        "gestor_observation": "Aprobación formal verificada. Galpón G-01 con 13.855 aves disponibles cumple rango 2.30 kg.",
        "gestor_username": "gestor1",
        "notes": "Entrega en rampa 2 en horas de la madrugada (4:00 AM).",
        "delivery_address": "Av. Nicolás Ayllón 3800, Mercado Santa Anita Puesto 45 - Lima",
        "farm_contact_phone": "+51 987 654 321 (Encargado Tradición 1)",
        "created_at": "2026-11-01T08:30:00Z",
        "updated_at": "2026-11-01T09:15:00Z",
        "transport_assigned": True,
        "transport_truck_id": "VH-001",
        "transport_plate": "T8C-940",
        "transport_model": "Camión Baranda 3 Ejes",
        "transport_driver_name": "Carlos Méndez Rojas",
        "transport_driver_phone": "+51 984 123 456",
        "transport_crew": "Cuadrilla Norte 1",
        "transport_shift": "MADRUGADA",
        "transport_capacity_cages": 450,
        "transport_notes": "Programado para carga 03:30 AM en Tradiciones 1 (G-01).",
        "transport_assigned_at": "2026-11-01T09:30:00Z",
        "transport_assigned_by": "gestor1",
        "loading_slot_time": "03:00 - 05:00 hrs",
        "dispatch_phase": "EN_GRANJA_CARGANDO",
        "dispatch_phase_updated_at": "2026-11-01T09:35:00Z",
        "audit_log": [
            {
                "id": "log-001",
                "action": "CREADO",
                "actor_username": "areacomercial1",
                "actor_role": "vendedor",
                "timestamp": "2026-11-01T08:30:00Z",
                "description": "Pedido registrado formalmente por Comercial para 4,000 aves.",
            }
        ],
    }
]


def _model_to_client_dict(model: ClientModel) -> Dict[str, Any]:
    return {
        "id": str(model.id),
        "business_name": model.business_name,
        "tax_id": model.tax_id,
        "zone_code": model.zone_code,
        "address": model.address,
        "contact_phone": model.contact_phone,
        "preferred_min_weight": float(model.preferred_min_weight) if model.preferred_min_weight is not None else None,
        "preferred_max_weight": float(model.preferred_max_weight) if model.preferred_max_weight is not None else None,
        "is_active": model.is_active,
        "created_at": model.created_at.isoformat() + "Z" if model.created_at else datetime.utcnow().isoformat() + "Z",
    }


def _model_to_order_dict(model: OrderModel) -> Dict[str, Any]:
    return {
        "id": str(model.id),
        "order_number": model.order_number,
        "client_id": str(model.client_id) if model.client_id else None,
        "client_name": model.client_name or "",
        "client_tax_id": model.client_tax_id,
        "seller_user_id": str(model.seller_user_id) if model.seller_user_id else "vendedor",
        "seller_username": model.seller_username or "vendedor",
        "seller_full_name": model.seller_full_name or "Juan Carlos Pérez Gálvez",
        "zone_code": model.zone_code,
        "target_delivery_date": str(model.target_delivery_date),
        "requested_quantity": model.requested_quantity,
        "allocated_quantity": model.allocated_quantity or 0,
        "min_weight_kg": float(model.min_weight_kg) if model.min_weight_kg is not None else 2.20,
        "max_weight_kg": float(model.max_weight_kg) if model.max_weight_kg is not None else 2.50,
        "sex_preference": model.sex_preference or "INDISTINTO",
        "estimated_total_kg": float(model.estimated_total_kg) if model.estimated_total_kg is not None else None,
        "estimated_cages": model.estimated_cages,
        "suggested_farm_code": model.suggested_farm_code,
        "suggested_barn_code": model.suggested_barn_code,
        "assigned_farm_code": model.assigned_farm_code,
        "assigned_barn_code": model.assigned_barn_code,
        "status": model.status or "REGISTRADO",
        "external_reference": model.external_reference,
        "gestor_observation": model.gestor_observation,
        "gestor_username": model.gestor_username,
        "notes": model.notes,
        "delivery_address": model.delivery_address,
        "delivery_latitude": float(model.delivery_latitude) if model.delivery_latitude is not None else None,
        "delivery_longitude": float(model.delivery_longitude) if model.delivery_longitude is not None else None,
        "farm_contact_phone": model.farm_contact_phone,
        "created_at": model.created_at.isoformat() + "Z" if model.created_at else datetime.utcnow().isoformat() + "Z",
        "updated_at": model.updated_at.isoformat() + "Z" if model.updated_at else datetime.utcnow().isoformat() + "Z",
        "transport_assigned": bool(model.transport_assigned),
        "transport_truck_id": model.transport_truck_id,
        "transport_plate": model.transport_plate,
        "transport_model": model.transport_model,
        "transport_driver_name": model.transport_driver_name,
        "transport_driver_phone": model.transport_driver_phone,
        "transport_crew": model.transport_crew,
        "transport_shift": model.transport_shift,
        "transport_capacity_cages": model.transport_capacity_cages,
        "transport_notes": model.transport_notes,
        "transport_assigned_at": model.transport_assigned_at.isoformat() + "Z" if model.transport_assigned_at else None,
        "transport_assigned_by": model.transport_assigned_by,
        "loading_slot_time": model.loading_slot_time,
        "dispatch_phase": model.dispatch_phase,
        "dispatch_phase_updated_at": model.dispatch_phase_updated_at.isoformat() + "Z" if model.dispatch_phase_updated_at else None,
        "audit_log": model.audit_log or [],
        "is_split_parent": bool(model.is_split_parent),
        "is_split_child": bool(model.is_split_child),
        "parent_order_id": str(model.parent_order_id) if model.parent_order_id else None,
        "original_requested_quantity": model.original_requested_quantity,
        "split_children_ids": [],
    }


def _model_to_vehicle_dict(model: TransportVehicleModel) -> Dict[str, Any]:
    return {
        "id": model.id,
        "plate": model.plate,
        "model": model.model or "Camión de Distribución",
        "capacity_cages": model.capacity_cages,
        "capacity_birds": model.capacity_birds,
        "driver_name": model.driver_name,
        "driver_phone": model.driver_phone,
        "default_crew": model.default_crew,
        "shift": model.shift,
        "zone_coverage": model.zone_coverage or ["NORTE", "CENTRO", "SUR", "METROPOLITANA"],
        "status": model.status,
    }


class ComercialService:
    _clients_store: List[Dict[str, Any]] = list(DEFAULT_CLIENTS)
    _orders_store: List[Dict[str, Any]] = list(INITIAL_ORDERS)
    _vehicles_store: List[Dict[str, Any]] = list(DEFAULT_VEHICLES)
    _order_counter: int = len(INITIAL_ORDERS)

    @classmethod
    def _add_audit_log(
        cls,
        order: Dict[str, Any],
        action: str,
        actor_username: str,
        actor_role: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Registra un evento inmutable en la auditoría."""
        if "audit_log" not in order or not isinstance(order["audit_log"], list):
            order["audit_log"] = []
        order["audit_log"].append({
            "id": f"log-{uuid4().hex[:6]}",
            "action": action,
            "actor_username": actor_username or "sistema",
            "actor_role": actor_role or "usuario",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "description": description,
            "details": details,
        })

    # =========================================================================
    # FLOTA DE TRANSPORTE
    # =========================================================================
    @classmethod
    async def get_transport_vehicles(cls, db: Optional[AsyncSession] = None) -> List[TransportVehicle]:
        """Obtiene la flota de transporte desde Supabase PostgreSQL o respaldo."""
        if db:
            try:
                res = await db.execute(select(TransportVehicleModel))
                models = res.scalars().all()
                if models:
                    return [TransportVehicle(**_model_to_vehicle_dict(m)) for m in models]
            except Exception as e:
                print(f"[ComercialService] Error consultando vehículos en BD: {e}")

        return [TransportVehicle(**v) for v in cls._vehicles_store]

    # =========================================================================
    # CLIENTES
    # =========================================================================
    @classmethod
    async def get_clients(cls, db: Optional[AsyncSession] = None) -> List[ClientResponse]:
        """Obtiene el catálogo de clientes autorizados desde Supabase PostgreSQL."""
        if db:
            try:
                stmt = select(ClientModel).where(ClientModel.is_active == True).order_by(ClientModel.created_at.desc())
                res = await db.execute(stmt)
                db_clients = res.scalars().all()
                if db_clients:
                    # Actualizar caché en memoria
                    cls._clients_store = [_model_to_client_dict(c) for c in db_clients]
                    return [ClientResponse(**c) for c in cls._clients_store]
            except Exception as e:
                print(f"[ComercialService] Error consultando clientes en BD: {e}")

        return [ClientResponse(**c) for c in cls._clients_store]

    @classmethod
    async def create_client(cls, client_in: ClientCreate, db: Optional[AsyncSession] = None) -> ClientResponse:
        """Registra un nuevo cliente con persistencia garantizada en PostgreSQL."""
        if db:
            try:
                # 1. Verificar unicidad de tax_id en BD
                dup = await db.execute(select(ClientModel).where(ClientModel.tax_id == client_in.tax_id))
                if dup.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya existe un cliente registrado con el RUC/DNI '{client_in.tax_id}'.",
                    )

                new_client_model = ClientModel(
                    id=uuid4(),
                    business_name=client_in.business_name,
                    tax_id=client_in.tax_id,
                    zone_code=client_in.zone_code,
                    address=client_in.address,
                    contact_phone=client_in.contact_phone,
                    preferred_min_weight=client_in.preferred_min_weight,
                    preferred_max_weight=client_in.preferred_max_weight,
                    is_active=client_in.is_active,
                    created_at=datetime.utcnow(),
                )
                db.add(new_client_model)
                await db.commit()
                await db.refresh(new_client_model)

                client_dict = _model_to_client_dict(new_client_model)
                cls._clients_store.insert(0, client_dict)
                return ClientResponse(**client_dict)
            except HTTPException:
                raise
            except Exception as e:
                print(f"[ComercialService] Error guardando cliente en BD: {e}")
                await db.rollback()

        # Fallback en memoria si la BD no responde
        if any(c["tax_id"] == client_in.tax_id for c in cls._clients_store):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un cliente registrado con el RUC/DNI '{client_in.tax_id}'.",
            )
        new_client = {
            "id": str(uuid4()),
            "business_name": client_in.business_name,
            "tax_id": client_in.tax_id,
            "zone_code": client_in.zone_code,
            "address": client_in.address,
            "contact_phone": client_in.contact_phone,
            "preferred_min_weight": client_in.preferred_min_weight,
            "preferred_max_weight": client_in.preferred_max_weight,
            "is_active": client_in.is_active,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        cls._clients_store.insert(0, new_client)
        return ClientResponse(**new_client)

    # =========================================================================
    # PEDIDOS Y PROGRAMACIÓN
    # =========================================================================
    @classmethod
    async def get_orders(
        cls,
        status_filter: Optional[str] = None,
        zone_filter: Optional[str] = None,
        seller_username: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[OrderResponse]:
        """Lista los pedidos registrados desde la base de datos PostgreSQL."""
        if db:
            try:
                stmt = select(OrderModel).order_by(OrderModel.target_delivery_date.desc(), OrderModel.created_at.desc())
                if status_filter:
                    stmt = stmt.where(OrderModel.status == status_filter)
                if zone_filter:
                    stmt = stmt.where(OrderModel.zone_code == zone_filter)
                if seller_username:
                    stmt = stmt.where(OrderModel.seller_username == seller_username)

                res = await db.execute(stmt)
                db_orders = res.scalars().all()
                if db_orders:
                    return [OrderResponse(**_model_to_order_dict(o)) for o in db_orders]
            except Exception as e:
                print(f"[ComercialService] Error listando pedidos en BD: {e}")

        # Fallback en memoria
        orders = cls._orders_store
        if status_filter:
            orders = [o for o in orders if o["status"] == status_filter]
        if zone_filter:
            orders = [o for o in orders if o["zone_code"] == zone_filter]
        if seller_username:
            orders = [o for o in orders if o["seller_username"] == seller_username]

        orders_sorted = sorted(
            orders,
            key=lambda x: (x.get("target_delivery_date", ""), x.get("created_at", "")),
            reverse=True,
        )
        return [OrderResponse(**o) for o in orders_sorted]

    @classmethod
    async def get_order_by_id(cls, order_id: str, db: Optional[AsyncSession] = None) -> OrderResponse:
        """Obtiene un pedido específico por ID o número de orden."""
        if db:
            try:
                try:
                    uuid_val = UUID(order_id)
                    stmt = select(OrderModel).where(or_(OrderModel.id == uuid_val, OrderModel.order_number == order_id))
                except (ValueError, TypeError):
                    stmt = select(OrderModel).where(OrderModel.order_number == order_id)

                res = await db.execute(stmt)
                order_model = res.scalar_one_or_none()
                if order_model:
                    return OrderResponse(**_model_to_order_dict(order_model))
            except Exception as e:
                print(f"[ComercialService] Error buscando pedido en BD: {e}")

        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                return OrderResponse(**o)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido '{order_id}' no encontrado.",
        )

    @classmethod
    async def create_order(
        cls,
        order_in: OrderCreate,
        seller_user_id: str,
        seller_username: str,
        db: Optional[AsyncSession] = None,
    ) -> OrderResponse:
        """Crea y persiste un nuevo pedido de venta en Supabase PostgreSQL."""
        if order_in.min_weight_kg > order_in.max_weight_kg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El peso mínimo ({order_in.min_weight_kg} kg) no puede ser mayor al peso máximo ({order_in.max_weight_kg} kg).",
            )

        if order_in.requested_quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cantidad de aves solicitadas debe ser mayor a cero.",
            )

        initial_status = "BORRADOR" if order_in.is_draft else "REGISTRADO"
        avg_weight = (order_in.min_weight_kg + order_in.max_weight_kg) / 2.0
        est_kg = round(order_in.requested_quantity * avg_weight, 2)
        est_cages = (order_in.requested_quantity + 7) // 8

        seller_full_name = getattr(order_in, "seller_full_name", None)
        if not seller_full_name:
            if seller_username in ("vendedor1", "vendedor"):
                seller_full_name = "Juan Carlos Pérez Gálvez"
            elif seller_username == "vendedor2":
                seller_full_name = "María Elena Rodríguez Soto"
            else:
                seller_full_name = seller_username.replace(".", " ").title()

        now_dt = datetime.utcnow()
        now_str = now_dt.isoformat() + "Z"
        audit_entry = {
            "id": f"log-{uuid4().hex[:6]}",
            "action": "CREADO",
            "actor_username": seller_username,
            "actor_role": "vendedor",
            "timestamp": now_str,
            "description": f"Pedido registrado formalmente por Comercial para {order_in.requested_quantity:,} aves.",
        }

        # Intentar persistencia en BD
        if db:
            try:
                # Contar pedidos para el secuencial
                cnt_res = await db.execute(select(func.count(OrderModel.id)))
                total_cnt = (cnt_res.scalar() or 0) + 1
                order_num = f"PED-2026-{str(total_cnt).zfill(3)}"

                # Convertir delivery_date a date object
                try:
                    target_date_obj = date.fromisoformat(order_in.target_delivery_date)
                except Exception:
                    target_date_obj = date.today()

                client_uuid = None
                if order_in.client_id:
                    try:
                        client_uuid = UUID(order_in.client_id)
                    except Exception:
                        pass

                seller_uuid = None
                try:
                    seller_uuid = UUID(seller_user_id)
                except Exception:
                    pass

                new_order_model = OrderModel(
                    id=uuid4(),
                    order_number=order_num,
                    client_id=client_uuid,
                    client_name=order_in.client_name,
                    client_tax_id=order_in.client_tax_id,
                    seller_user_id=seller_uuid,
                    seller_username=seller_username,
                    seller_full_name=seller_full_name,
                    zone_code=order_in.zone_code,
                    target_delivery_date=target_date_obj,
                    status=initial_status,
                    requested_quantity=order_in.requested_quantity,
                    allocated_quantity=0,
                    min_weight_kg=round(order_in.min_weight_kg, 2),
                    max_weight_kg=round(order_in.max_weight_kg, 2),
                    sex_preference=order_in.sex_preference or "INDISTINTO",
                    estimated_total_kg=est_kg,
                    estimated_cages=est_cages,
                    suggested_farm_code=order_in.suggested_farm_code,
                    suggested_barn_code=order_in.suggested_barn_code,
                    assigned_farm_code=None,
                    assigned_barn_code=None,
                    external_reference=order_in.external_reference,
                    notes=order_in.notes,
                    delivery_address=order_in.delivery_address or f"Punto de distribución - Zona {order_in.zone_code}",
                    delivery_latitude=order_in.delivery_latitude,
                    delivery_longitude=order_in.delivery_longitude,
                    audit_log=[audit_entry],
                    created_at=now_dt,
                    updated_at=now_dt,
                )

                db.add(new_order_model)
                await db.commit()
                await db.refresh(new_order_model)

                order_dict = _model_to_order_dict(new_order_model)
                cls._orders_store.insert(0, order_dict)
                return OrderResponse(**order_dict)
            except Exception as e:
                print(f"[ComercialService] Error guardando pedido en BD: {e}")
                await db.rollback()

        # Respaldo en memoria
        cls._order_counter += 1
        order_num = f"PED-2026-{str(cls._order_counter).zfill(3)}"
        new_order = {
            "id": f"ord-{uuid4().hex[:8]}",
            "order_number": order_num,
            "client_id": order_in.client_id,
            "client_name": order_in.client_name,
            "client_tax_id": order_in.client_tax_id,
            "seller_user_id": seller_user_id,
            "seller_username": seller_username,
            "seller_full_name": seller_full_name,
            "zone_code": order_in.zone_code,
            "target_delivery_date": order_in.target_delivery_date,
            "requested_quantity": order_in.requested_quantity,
            "allocated_quantity": 0,
            "min_weight_kg": round(order_in.min_weight_kg, 2),
            "max_weight_kg": round(order_in.max_weight_kg, 2),
            "sex_preference": getattr(order_in, "sex_preference", "INDISTINTO") or "INDISTINTO",
            "estimated_total_kg": est_kg,
            "estimated_cages": est_cages,
            "suggested_farm_code": order_in.suggested_farm_code,
            "suggested_barn_code": order_in.suggested_barn_code,
            "assigned_farm_code": None,
            "assigned_barn_code": None,
            "status": initial_status,
            "external_reference": order_in.external_reference,
            "gestor_observation": None,
            "gestor_username": None,
            "notes": order_in.notes,
            "delivery_address": order_in.delivery_address or f"Punto de distribución oficial - Zona {order_in.zone_code}",
            "delivery_latitude": order_in.delivery_latitude,
            "delivery_longitude": order_in.delivery_longitude,
            "created_at": now_str,
            "updated_at": now_str,
            "audit_log": [audit_entry],
        }
        cls._orders_store.insert(0, new_order)
        return OrderResponse(**new_order)

    # =========================================================================
    # APROBACIÓN, OBSERVACIÓN Y CANCELACIÓN (GESTOR COMERCIAL)
    # =========================================================================
    @classmethod
    async def aprobar_pedido(
        cls,
        order_id: str,
        user_role: str,
        gestor_username: str,
        action_req: OrderActionRequest,
        db: Optional[AsyncSession] = None,
    ) -> OrderResponse:
        """Aprueba formalmente el pedido y reserva aves del galpón en PostgreSQL."""
        allowed_roles = ["gestor_comercial", "gerente_comercial", "admin_sistema"]
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: Únicamente el Gestor Comercial puede autorizar pedidos.",
            )

        if db:
            try:
                try:
                    uuid_val = UUID(order_id)
                    stmt = select(OrderModel).where(or_(OrderModel.id == uuid_val, OrderModel.order_number == order_id))
                except Exception:
                    stmt = select(OrderModel).where(OrderModel.order_number == order_id)

                res = await db.execute(stmt)
                m = res.scalar_one_or_none()
                if m:
                    if m.status == "CANCELADO":
                        raise HTTPException(status_code=400, detail="No se puede aprobar un pedido cancelado.")

                    farm_to_assign = action_req.farm_code or m.suggested_farm_code or "TRAD1"
                    barn_to_assign = action_req.barn_code or m.suggested_barn_code or "G-01"
                    qty_to_assign = action_req.allocated_quantity or m.requested_quantity

                    m.status = "APROBADO_RESERVADO"
                    m.assigned_farm_code = farm_to_assign
                    m.assigned_barn_code = barn_to_assign
                    m.allocated_quantity = qty_to_assign
                    m.gestor_username = gestor_username
                    m.gestor_observation = action_req.observation or f"Aprobación formal por {gestor_username}. Galpón [{barn_to_assign}] de [{farm_to_assign}] con {qty_to_assign:,} aves reservadas."
                    m.updated_at = datetime.utcnow()

                    # Audit Log
                    current_log = list(m.audit_log or [])
                    current_log.append({
                        "id": f"log-{uuid4().hex[:6]}",
                        "action": "APROBADO_RESERVADO",
                        "actor_username": gestor_username,
                        "actor_role": user_role,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "description": f"Aprobación formal confirmada en {farm_to_assign} ({barn_to_assign}) por {qty_to_assign:,} aves.",
                    })
                    m.audit_log = current_log
                    flag_modified(m, "audit_log")

                    await db.commit()
                    await db.refresh(m)
                    order_dict = _model_to_order_dict(m)
                    return OrderResponse(**order_dict)
            except HTTPException:
                raise
            except Exception as e:
                print(f"[ComercialService] Error aprobando pedido en BD: {e}")
                await db.rollback()

        # Respaldo en memoria
        target_order = None
        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                target_order = o
                break

        if not target_order:
            raise HTTPException(status_code=404, detail=f"Pedido '{order_id}' no encontrado.")

        farm_to_assign = action_req.farm_code or target_order.get("suggested_farm_code") or "TRAD1"
        barn_to_assign = action_req.barn_code or target_order.get("suggested_barn_code") or "G-01"
        qty_to_assign = action_req.allocated_quantity or target_order["requested_quantity"]

        target_order["status"] = "APROBADO_RESERVADO"
        target_order["assigned_farm_code"] = farm_to_assign
        target_order["assigned_barn_code"] = barn_to_assign
        target_order["allocated_quantity"] = qty_to_assign
        target_order["gestor_username"] = gestor_username
        target_order["gestor_observation"] = action_req.observation or f"Aprobación formal por {gestor_username}."
        target_order["updated_at"] = datetime.utcnow().isoformat() + "Z"
        cls._add_audit_log(
            target_order,
            action="APROBADO_RESERVADO",
            actor_username=gestor_username,
            actor_role=user_role,
            description=f"Aprobación confirmada en {farm_to_assign} ({barn_to_assign}) por {qty_to_assign:,} aves.",
        )
        return OrderResponse(**target_order)

    dar_ok_pedido = aprobar_pedido

    @classmethod
    async def observar_pedido(
        cls,
        order_id: str,
        user_role: str,
        gestor_username: str,
        action_req: OrderActionRequest,
        db: Optional[AsyncSession] = None,
    ) -> OrderResponse:
        """Devuelve el pedido con una observación de asignación al Vendedor."""
        allowed_roles = ["gestor_comercial", "gerente_comercial", "admin_sistema"]
        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Únicamente el Gestor Comercial puede observar pedidos.")

        if not action_req.observation:
            raise HTTPException(status_code=400, detail="Debe ingresar el motivo de observación.")

        if db:
            try:
                try:
                    uuid_val = UUID(order_id)
                    stmt = select(OrderModel).where(or_(OrderModel.id == uuid_val, OrderModel.order_number == order_id))
                except Exception:
                    stmt = select(OrderModel).where(OrderModel.order_number == order_id)

                res = await db.execute(stmt)
                m = res.scalar_one_or_none()
                if m:
                    m.status = "CON_OBSERVACION"
                    m.gestor_username = gestor_username
                    m.gestor_observation = action_req.observation
                    m.updated_at = datetime.utcnow()

                    current_log = list(m.audit_log or [])
                    current_log.append({
                        "id": f"log-{uuid4().hex[:6]}",
                        "action": "OBSERVADO",
                        "actor_username": gestor_username,
                        "actor_role": user_role,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "description": f"Observación de Gestor: {action_req.observation}",
                    })
                    m.audit_log = current_log
                    flag_modified(m, "audit_log")

                    await db.commit()
                    await db.refresh(m)
                    return OrderResponse(**_model_to_order_dict(m))
            except Exception as e:
                print(f"[ComercialService] Error observando pedido en BD: {e}")
                await db.rollback()

        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                o["status"] = "CON_OBSERVACION"
                o["gestor_username"] = gestor_username
                o["gestor_observation"] = action_req.observation
                o["updated_at"] = datetime.utcnow().isoformat() + "Z"
                cls._add_audit_log(o, action="OBSERVADO", actor_username=gestor_username, actor_role=user_role, description=action_req.observation)
                return OrderResponse(**o)

        raise HTTPException(status_code=404, detail=f"Pedido '{order_id}' no encontrado.")

    @classmethod
    async def cancelar_pedido(
        cls,
        order_id: str,
        reason: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> OrderResponse:
        """Cancela un pedido comercial."""
        if db:
            try:
                try:
                    uuid_val = UUID(order_id)
                    stmt = select(OrderModel).where(or_(OrderModel.id == uuid_val, OrderModel.order_number == order_id))
                except Exception:
                    stmt = select(OrderModel).where(OrderModel.order_number == order_id)

                res = await db.execute(stmt)
                m = res.scalar_one_or_none()
                if m:
                    m.status = "CANCELADO"
                    m.notes = f"{m.notes or ''} [Cancelado: {reason or 'Sin motivo'}]".strip()
                    m.updated_at = datetime.utcnow()
                    await db.commit()
                    await db.refresh(m)
                    return OrderResponse(**_model_to_order_dict(m))
            except Exception as e:
                print(f"[ComercialService] Error cancelando pedido en BD: {e}")
                await db.rollback()

        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                o["status"] = "CANCELADO"
                o["notes"] = f"{o.get('notes') or ''} [Cancelado: {reason or 'Sin motivo'}]".strip()
                o["updated_at"] = datetime.utcnow().isoformat() + "Z"
                return OrderResponse(**o)

        raise HTTPException(status_code=404, detail=f"Pedido '{order_id}' no encontrado.")

    # =========================================================================
    # LOGÍSTICA, TRANSPORTE Y DESPACHO
    # =========================================================================
    @classmethod
    async def assign_transport_to_order(
        cls,
        order_id: str,
        user_role: str,
        gestor_username: str,
        transport_req: AssignTransportRequest,
        db: Optional[AsyncSession] = None,
    ) -> OrderResponse:
        """Designa vehículo y conductor a un pedido formalmente aprobado."""
        allowed_roles = ["gestor_comercial", "gerente_comercial", "admin_sistema"]
        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Solo el Gestor Comercial puede asignar transporte.")

        now_dt = datetime.utcnow()
        now_str = now_dt.isoformat() + "Z"

        if db:
            try:
                try:
                    uuid_val = UUID(order_id)
                    stmt = select(OrderModel).where(or_(OrderModel.id == uuid_val, OrderModel.order_number == order_id))
                except Exception:
                    stmt = select(OrderModel).where(OrderModel.order_number == order_id)

                res = await db.execute(stmt)
                m = res.scalar_one_or_none()
                if m:
                    m.transport_assigned = True
                    m.transport_truck_id = transport_req.truck_id
                    m.transport_plate = transport_req.plate
                    m.transport_model = transport_req.model
                    m.transport_driver_name = transport_req.driver_name
                    m.transport_driver_phone = transport_req.driver_phone
                    m.transport_crew = transport_req.crew
                    m.transport_shift = transport_req.shift
                    m.transport_capacity_cages = transport_req.capacity_cages
                    m.transport_notes = transport_req.transport_notes
                    m.transport_assigned_at = now_dt
                    m.transport_assigned_by = gestor_username
                    m.loading_slot_time = transport_req.loading_slot_time or "03:00 - 05:00 hrs"
                    m.dispatch_phase = "TRANSPORTE_ASIGNADO"
                    m.dispatch_phase_updated_at = now_dt
                    m.updated_at = now_dt

                    current_log = list(m.audit_log or [])
                    current_log.append({
                        "id": f"log-{uuid4().hex[:6]}",
                        "action": "TRANSPORTE_ASIGNADO",
                        "actor_username": gestor_username,
                        "actor_role": user_role,
                        "timestamp": now_str,
                        "description": f"Unidad {transport_req.plate} designada a {transport_req.driver_name}.",
                    })
                    m.audit_log = current_log
                    flag_modified(m, "audit_log")

                    await db.commit()
                    await db.refresh(m)
                    return OrderResponse(**_model_to_order_dict(m))
            except Exception as e:
                print(f"[ComercialService] Error asignando transporte en BD: {e}")
                await db.rollback()

        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                o["transport_assigned"] = True
                o["transport_truck_id"] = transport_req.truck_id
                o["transport_plate"] = transport_req.plate
                o["transport_driver_name"] = transport_req.driver_name
                o["transport_driver_phone"] = transport_req.driver_phone
                o["transport_crew"] = transport_req.crew
                o["transport_shift"] = transport_req.shift
                o["transport_assigned_at"] = now_str
                o["transport_assigned_by"] = gestor_username
                o["dispatch_phase"] = "TRANSPORTE_ASIGNADO"
                o["updated_at"] = now_str
                cls._add_audit_log(o, action="TRANSPORTE_ASIGNADO", actor_username=gestor_username, actor_role=user_role, description=f"Unidad {transport_req.plate} asignada.")
                return OrderResponse(**o)

        raise HTTPException(status_code=404, detail=f"Pedido '{order_id}' no encontrado.")

    @classmethod
    async def unassign_transport_from_order(
        cls,
        order_id: str,
        user_role: str,
        gestor_username: str,
        db: Optional[AsyncSession] = None,
    ) -> OrderResponse:
        """Libera la designación de transporte de un pedido."""
        if db:
            try:
                try:
                    uuid_val = UUID(order_id)
                    stmt = select(OrderModel).where(or_(OrderModel.id == uuid_val, OrderModel.order_number == order_id))
                except Exception:
                    stmt = select(OrderModel).where(OrderModel.order_number == order_id)

                res = await db.execute(stmt)
                m = res.scalar_one_or_none()
                if m:
                    m.transport_assigned = False
                    m.transport_truck_id = None
                    m.transport_plate = None
                    m.transport_driver_name = None
                    m.dispatch_phase = None
                    m.updated_at = datetime.utcnow()
                    await db.commit()
                    await db.refresh(m)
                    return OrderResponse(**_model_to_order_dict(m))
            except Exception as e:
                print(f"[ComercialService] Error liberando transporte en BD: {e}")
                await db.rollback()

        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                o["transport_assigned"] = False
                o["transport_plate"] = None
                o["dispatch_phase"] = None
                o["updated_at"] = datetime.utcnow().isoformat() + "Z"
                return OrderResponse(**o)

        raise HTTPException(status_code=404, detail=f"Pedido '{order_id}' no encontrado.")

    @classmethod
    async def update_dispatch_phase(
        cls,
        order_id: str,
        user_role: str,
        username: str,
        dispatch_phase: str,
        notes: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> OrderResponse:
        """Actualiza la fase de despacho (Tracking GPS / Despacho en Ruta)."""
        valid_phases = ["TRANSPORTE_ASIGNADO", "EN_GRANJA_CARGANDO", "EN_TRANSITO", "ENTREGADO_CONFORME"]
        if dispatch_phase not in valid_phases:
            raise HTTPException(status_code=400, detail=f"Fase '{dispatch_phase}' no válida.")

        now_dt = datetime.utcnow()
        now_str = now_dt.isoformat() + "Z"

        if db:
            try:
                try:
                    uuid_val = UUID(order_id)
                    stmt = select(OrderModel).where(or_(OrderModel.id == uuid_val, OrderModel.order_number == order_id))
                except Exception:
                    stmt = select(OrderModel).where(OrderModel.order_number == order_id)

                res = await db.execute(stmt)
                m = res.scalar_one_or_none()
                if m:
                    m.dispatch_phase = dispatch_phase
                    m.dispatch_phase_updated_at = now_dt
                    m.updated_at = now_dt
                    if dispatch_phase == "ENTREGADO_CONFORME":
                        m.status = "DESPACHADO"

                    current_log = list(m.audit_log or [])
                    current_log.append({
                        "id": f"log-{uuid4().hex[:6]}",
                        "action": "FASE_ACTUALIZADA",
                        "actor_username": username,
                        "actor_role": user_role,
                        "timestamp": now_str,
                        "description": f"Ciclo de despacho avanzado a '{dispatch_phase}'.",
                    })
                    m.audit_log = current_log
                    flag_modified(m, "audit_log")

                    await db.commit()
                    await db.refresh(m)
                    return OrderResponse(**_model_to_order_dict(m))
            except Exception as e:
                print(f"[ComercialService] Error actualizando fase en BD: {e}")
                await db.rollback()

        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                o["dispatch_phase"] = dispatch_phase
                o["dispatch_phase_updated_at"] = now_str
                o["updated_at"] = now_str
                if dispatch_phase == "ENTREGADO_CONFORME":
                    o["status"] = "DESPACHADO"
                return OrderResponse(**o)

        raise HTTPException(status_code=404, detail=f"Pedido '{order_id}' no encontrado.")

    @classmethod
    async def get_programacion_transporte(
        cls,
        delivery_date: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> ProgramacionTransporteResponse:
        """Genera la Hoja de Programación de Transporte desde pedidos aprobados en PostgreSQL."""
        orders_data: List[OrderResponse] = await cls.get_orders(status_filter="APROBADO_RESERVADO", db=db)
        if delivery_date:
            orders_data = [o for o in orders_data if o.target_delivery_date == delivery_date]

        items: List[ProgramacionTransporteItem] = []
        total_birds = 0
        total_cages = 0
        total_kg = 0.0

        for o in orders_data:
            allocated = o.allocated_quantity or o.requested_quantity or 0
            cages = o.estimated_cages or int(math.ceil(allocated / 8.0))
            order_kg = o.estimated_total_kg or round(allocated * ((o.min_weight_kg + o.max_weight_kg) / 2.0), 2)
            tons = round(order_kg / 1000.0, 2)

            total_birds += allocated
            total_cages += cages
            total_kg += order_kg

            items.append(
                ProgramacionTransporteItem(
                    order_id=o.id,
                    order_number=o.order_number,
                    target_delivery_date=o.target_delivery_date,
                    client_name=o.client_name,
                    client_tax_id=o.client_tax_id,
                    zone_code=o.zone_code,
                    assigned_farm_code=o.assigned_farm_code or "POR ASIGNAR",
                    assigned_barn_code=o.assigned_barn_code or "POR ASIGNAR",
                    allocated_quantity=allocated,
                    estimated_cages=cages,
                    estimated_total_kg=order_kg,
                    estimated_tons=tons,
                    sex_preference=o.sex_preference or "INDISTINTO",
                    min_weight_kg=o.min_weight_kg,
                    max_weight_kg=o.max_weight_kg,
                    gestor_username=o.gestor_username,
                    notes=o.notes,
                    external_reference=o.external_reference,
                    transport_assigned=o.transport_assigned,
                    transport_plate=o.transport_plate,
                    transport_driver_name=o.transport_driver_name,
                    transport_crew=o.transport_crew,
                    transport_shift=o.transport_shift,
                )
            )

        total_tons = round(total_kg / 1000.0, 2)
        estimated_trucks = int(math.ceil(total_cages / 450.0)) if total_cages > 0 else 0

        return ProgramacionTransporteResponse(
            delivery_date=delivery_date,
            total_orders=len(items),
            total_birds=total_birds,
            total_cages=total_cages,
            total_tons=total_tons,
            estimated_trucks=estimated_trucks,
            items=items,
        )
