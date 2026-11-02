# ==============================================================================
# SERVICIO DE APLICACIÓN DEL MÓDULO COMERCIAL
# Archivo: backend/app/modules/comercial/application/service.py
# ==============================================================================

import math
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, date
from fastapi import HTTPException, status

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

# Catálogo oficial predeterminado de clientes autorizados
DEFAULT_CLIENTS = [
    {
        "id": "c1000000-0000-0000-0000-000000000001",
        "business_name": "Distribuidora Santa Anita S.A.C.",
        "tax_id": "20548963211",
        "zone_code": "CENTRO",
        "address": "Av. Los Ruiseñores 450, Santa Anita, Lima",
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

# Flota de Transporte y Distribución disponible
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

# Pedidos iniciales de demostración y trazabilidad
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
                "description": "Pedido registrado formalmente por Comercial (Felipe) para 4,000 aves (Macho 2.20 - 2.50 kg).",
            },
            {
                "id": "log-002",
                "action": "APROBADO_RESERVADO",
                "actor_username": "gestor1",
                "actor_role": "gestor_comercial",
                "timestamp": "2026-11-01T09:15:00Z",
                "description": "Aprobación formal verificada. Reserva otorgada en Granja Tradición 1 (Galpón G-01) por 4,000 aves.",
            },
            {
                "id": "log-003",
                "action": "TRANSPORTE_ASIGNADO",
                "actor_username": "gestor1",
                "actor_role": "gestor_comercial",
                "timestamp": "2026-11-01T09:30:00Z",
                "description": "Unidad T8C-940 designada a Carlos Méndez Rojas en turno Madrugada (Ventana de Carga: 03:00 - 05:00 hrs).",
            },
            {
                "id": "log-004",
                "action": "FASE_ACTUALIZADA",
                "actor_username": "gestor1",
                "actor_role": "gestor_comercial",
                "timestamp": "2026-11-01T09:35:00Z",
                "description": "Ciclo de despacho avanzado a 'En Granja / Cargando Aves'. Cuadrilla Norte 1 en balanza.",
            },
        ],
    },
    {
        "id": "ord-0002",
        "order_number": "PED-2026-002",
        "client_id": "c1000000-0000-0000-0000-000000000002",
        "client_name": "Pollerías Norky's Corp S.A.",
        "client_tax_id": "20100456789",
        "seller_user_id": "u-seller-1",
        "seller_username": "vendedor1",
        "seller_full_name": "Juan Carlos Pérez Gálvez",
        "zone_code": "METROPOLITANA",
        "target_delivery_date": "2026-11-04",
        "requested_quantity": 3000,
        "allocated_quantity": 0,
        "min_weight_kg": 2.10,
        "max_weight_kg": 2.30,
        "sex_preference": "HEMBRA",
        "estimated_total_kg": 6600.0,
        "estimated_cages": 375,
        "suggested_farm_code": "TRAD2",
        "suggested_barn_code": "G-03",
        "assigned_farm_code": None,
        "assigned_barn_code": None,
        "status": "REGISTRADO",
        "external_reference": "OC-9921",
        "gestor_observation": None,
        "gestor_username": None,
        "notes": "Pollo entero de primera calidad para brasa. Requiere autorización del Gestor Comercial.",
        "delivery_address": "Av. Universitaria 1420, San Miguel - Lima",
        "farm_contact_phone": "+51 982 112 334 (Encargado Tradición 2)",
        "created_at": "2026-11-01T10:00:00Z",
        "updated_at": "2026-11-01T10:00:00Z",
        "audit_log": [
            {
                "id": "log-005",
                "action": "CREADO",
                "actor_username": "vendedor1",
                "actor_role": "vendedor",
                "timestamp": "2026-11-01T10:00:00Z",
                "description": "Pedido registrado por Comercial para 3,000 aves (Hembra 2.10 - 2.30 kg).",
            }
        ],
    },
    {
        "id": "ord-0003",
        "order_number": "PED-2026-003",
        "client_id": "c1000000-0000-0000-0000-000000000003",
        "client_name": "Supermercados Metro / Cencosud Perú",
        "client_tax_id": "20456123987",
        "seller_user_id": "u-seller-2",
        "seller_username": "vendedor2",
        "seller_full_name": "María Elena Rodríguez Soto",
        "zone_code": "NORTE",
        "target_delivery_date": "2026-11-04",
        "requested_quantity": 5000,
        "allocated_quantity": 0,
        "min_weight_kg": 2.30,
        "max_weight_kg": 2.60,
        "sex_preference": "INDISTINTO",
        "estimated_total_kg": 12250.0,
        "estimated_cages": 625,
        "suggested_farm_code": "PACI6",
        "suggested_barn_code": "G-02",
        "assigned_farm_code": None,
        "assigned_barn_code": None,
        "status": "REGISTRADO",
        "external_reference": "OC-METRO-110",
        "gestor_observation": None,
        "gestor_username": None,
        "notes": "Cliente corporativo de alta prioridad. Programar saca para despacho matutino.",
        "delivery_address": "Av. Alfredo Mendiola 1400, C.C. Plaza Norte - Independencia",
        "farm_contact_phone": "+51 977 443 221 (Encargado Pacahuara 6)",
        "created_at": "2026-11-01T11:20:00Z",
        "updated_at": "2026-11-01T11:20:00Z",
        "audit_log": [
            {
                "id": "log-006",
                "action": "CREADO",
                "actor_username": "vendedor2",
                "actor_role": "vendedor",
                "timestamp": "2026-11-01T11:20:00Z",
                "description": "Pedido registrado por Comercial para 5,000 aves corporativas.",
            }
        ],
    },
    {
        "id": "ord-0004",
        "order_number": "PED-2026-004",
        "client_id": "c1000000-0000-0000-0000-000000000004",
        "client_name": "Mercados del Norte Mayoristas S.A.C.",
        "client_tax_id": "20601234567",
        "seller_user_id": "u-seller-felipe",
        "seller_username": "areacomercial1",
        "seller_full_name": "Felipe",
        "zone_code": "NORTE",
        "target_delivery_date": "2026-11-05",
        "requested_quantity": 2500,
        "allocated_quantity": 0,
        "min_weight_kg": 2.40,
        "max_weight_kg": 2.70,
        "sex_preference": "MACHO",
        "estimated_total_kg": 6375.0,
        "estimated_cages": 313,
        "suggested_farm_code": "SISA1",
        "suggested_barn_code": "G-05",
        "assigned_farm_code": None,
        "assigned_barn_code": None,
        "status": "CON_OBSERVACION",
        "external_reference": "OC-UNI-55",
        "gestor_observation": "Galpón sugerido cuenta con peso promedio de 2.25 kg. Consultar al cliente si acepta rango 2.20 - 2.40 kg o mover fecha al 07 de Nov.",
        "gestor_username": "gestor1",
        "notes": "Esperando respuesta de negociación con el cliente.",
        "delivery_address": "Mercado Mayorista Conzac, Puestos 12-14 - Los Olivos",
        "farm_contact_phone": "+51 966 887 711 (Encargado Sisa 1)",
        "created_at": "2026-11-01T12:00:00Z",
        "updated_at": "2026-11-01T13:40:00Z",
        "audit_log": [
            {
                "id": "log-007",
                "action": "CREADO",
                "actor_username": "vendedor1",
                "actor_role": "vendedor",
                "timestamp": "2026-11-01T12:00:00Z",
                "description": "Pedido registrado por Comercial para 2,500 aves (Macho 2.40 - 2.70 kg).",
            },
            {
                "id": "log-008",
                "action": "OBSERVADO",
                "actor_username": "gestor1",
                "actor_role": "gestor_comercial",
                "timestamp": "2026-11-01T13:40:00Z",
                "description": "Observado por Gestor Comercial: Galpón sugerido cuenta con peso promedio de 2.25 kg. Devolver a Comercial.",
            },
        ],
    },
]


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
        """Registra un evento inmutable en la línea de tiempo de auditoría del pedido."""
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

    @classmethod
    def get_transport_vehicles(cls) -> List[TransportVehicle]:
        """Obtiene la flota de transporte y distribución disponible de Avícola GR."""
        return [TransportVehicle(**v) for v in cls._vehicles_store]

    @classmethod
    def assign_transport_to_order(
        cls,
        order_id: str,
        user_role: str,
        gestor_username: str,
        transport_req: AssignTransportRequest,
    ) -> OrderResponse:
        """
        DESIGNACIÓN DE TRANSPORTE DE DISTRIBUCIÓN:
        El Gestor Comercial asigna la unidad de transporte, conductor, turno de saca y cuadrilla
        a un pedido formalmente aprobado.
        """
        allowed_roles = ["gestor_comercial", "gerente_comercial", "admin_sistema"]
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: Únicamente el Gestor Comercial puede designar transporte de distribución.",
            )

        target_order = None
        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                target_order = o
                break

        if not target_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido '{order_id}' no encontrado.",
            )

        if target_order["status"] != "APROBADO_RESERVADO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede designar transporte a pedidos que cuenten con la aprobación formal del Gestor Comercial (APROBADO_RESERVADO).",
            )

        # Buscar el vehículo en la flota
        vehicle = next((v for v in cls._vehicles_store if v["id"] == transport_req.vehicle_id), None)
        plate = transport_req.plate or (vehicle["plate"] if vehicle else "UNIDAD-DESCONOCIDA")
        model = vehicle["model"] if vehicle else "Camión Estándar"
        driver = transport_req.driver_name or (vehicle["driver_name"] if vehicle else "Conductor Asignado")
        phone = transport_req.driver_phone or (vehicle.get("driver_phone") if vehicle else None)
        crew = transport_req.crew_name or (vehicle.get("default_crew") if vehicle else "Cuadrilla Oficial")
        capacity = vehicle["capacity_cages"] if vehicle else 450

        now_str = datetime.utcnow().isoformat() + "Z"
        target_order["transport_assigned"] = True
        target_order["transport_truck_id"] = transport_req.vehicle_id
        target_order["transport_plate"] = plate
        target_order["transport_model"] = model
        target_order["transport_driver_name"] = driver
        target_order["transport_driver_phone"] = phone
        target_order["transport_crew"] = crew
        target_order["transport_shift"] = transport_req.shift or "MADRUGADA"
        target_order["transport_capacity_cages"] = capacity
        target_order["transport_notes"] = transport_req.transport_notes
        target_order["transport_assigned_at"] = now_str
        target_order["transport_assigned_by"] = gestor_username
        target_order["loading_slot_time"] = transport_req.loading_slot_time or "03:00 - 05:00 hrs"
        target_order["dispatch_phase"] = "TRANSPORTE_ASIGNADO"
        target_order["dispatch_phase_updated_at"] = now_str
        target_order["updated_at"] = now_str

        cls._add_audit_log(
            target_order,
            action="TRANSPORTE_ASIGNADO",
            actor_username=gestor_username,
            actor_role=user_role,
            description=f"Unidad {plate} ({driver}) asignada en turno {target_order['transport_shift']} con ventana de carga {target_order['loading_slot_time']}.",
        )

        return OrderResponse(**target_order)

    @classmethod
    def unassign_transport_from_order(
        cls,
        order_id: str,
        user_role: str,
    ) -> OrderResponse:
        """Libera la asignación de transporte de un pedido en caso de contingencia logística."""
        allowed_roles = ["gestor_comercial", "gerente_comercial", "admin_sistema"]
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: Únicamente el Gestor Comercial puede modificar la asignación de transporte.",
            )

        target_order = None
        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                target_order = o
                break

        if not target_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido '{order_id}' no encontrado.",
            )

        now_str = datetime.utcnow().isoformat() + "Z"
        target_order["transport_assigned"] = False
        target_order["transport_truck_id"] = None
        target_order["transport_plate"] = None
        target_order["transport_model"] = None
        target_order["transport_driver_name"] = None
        target_order["transport_driver_phone"] = None
        target_order["transport_crew"] = None
        target_order["transport_shift"] = None
        target_order["transport_capacity_cages"] = None
        target_order["transport_notes"] = None
        target_order["dispatch_phase"] = None
        target_order["dispatch_phase_updated_at"] = None
        target_order["loading_slot_time"] = None
        target_order["updated_at"] = now_str

        cls._add_audit_log(
            target_order,
            action="TRANSPORTE_LIBERADO",
            actor_username="gestor_comercial",
            actor_role=user_role,
            description="Asignación de transporte liberada por el Gestor Comercial.",
        )

        return OrderResponse(**target_order)

    @classmethod
    def update_dispatch_phase(
        cls,
        order_id: str,
        user_role: str,
        username: str,
        dispatch_phase: str,
        notes: Optional[str] = None,
    ) -> OrderResponse:
        """
        CICLO DE VIDA DEL DESPACHO (Tracking de 4 Fases):
        1. TRANSPORTE_ASIGNADO
        2. EN_GRANJA_CARGANDO
        3. EN_TRANSITO
        4. ENTREGADO_CONFORME
        """
        valid_phases = [
            "TRANSPORTE_ASIGNADO",
            "EN_GRANJA_CARGANDO",
            "EN_TRANSITO",
            "ENTREGADO_CONFORME",
        ]
        if dispatch_phase not in valid_phases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fase '{dispatch_phase}' no válida. Opciones permitidas: {valid_phases}",
            )

        target_order = None
        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                target_order = o
                break

        if not target_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido '{order_id}' no encontrado.",
            )

        if not target_order.get("transport_assigned"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El pedido debe tener un vehículo de transporte asignado previamente para avanzar su ciclo de despacho.",
            )

        now_str = datetime.utcnow().isoformat() + "Z"
        target_order["dispatch_phase"] = dispatch_phase
        target_order["dispatch_phase_updated_at"] = now_str
        target_order["updated_at"] = now_str
        if notes:
            target_order["notes"] = f"{target_order.get('notes', '')} | [Fase {dispatch_phase}]: {notes}".strip(" |")

        if dispatch_phase == "ENTREGADO_CONFORME":
            target_order["status"] = "DESPACHADO"
        elif target_order.get("status") == "DESPACHADO":
            target_order["status"] = "APROBADO_RESERVADO"

        phase_names = {
            "TRANSPORTE_ASIGNADO": "Transporte Asignado",
            "EN_GRANJA_CARGANDO": "En Granja / Cargando Aves",
            "EN_TRANSITO": "En Tránsito Carretera",
            "ENTREGADO_CONFORME": "Entregado / Conforme en Destino",
        }
        cls._add_audit_log(
            target_order,
            action="FASE_ACTUALIZADA",
            actor_username=username,
            actor_role=user_role,
            description=f"Ciclo de despacho avanzado a '{phase_names.get(dispatch_phase, dispatch_phase)}'.",
        )

        return OrderResponse(**target_order)

    @classmethod
    def get_clients(cls) -> List[ClientResponse]:
        """Obtiene el catálogo de clientes autorizados."""
        return [ClientResponse(**c) for c in cls._clients_store]

    @classmethod
    def create_client(cls, client_in: ClientCreate) -> ClientResponse:
        """Registra un nuevo cliente en el catálogo."""
        # Verificar RUC duplicado
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
        cls._clients_store.append(new_client)
        return ClientResponse(**new_client)

    @classmethod
    def get_orders(
        cls,
        status_filter: Optional[str] = None,
        zone_filter: Optional[str] = None,
        seller_username: Optional[str] = None,
    ) -> List[OrderResponse]:
        """Lista los pedidos registrados en el sistema."""
        orders = cls._orders_store
        if status_filter:
            orders = [o for o in orders if o["status"] == status_filter]
        if zone_filter:
            orders = [o for o in orders if o["zone_code"] == zone_filter]
        if seller_username:
            orders = [o for o in orders if o["seller_username"] == seller_username]

        # Ordenar por fecha de entrega y fecha de creación descendente
        orders_sorted = sorted(
            orders,
            key=lambda x: (x["target_delivery_date"], x["created_at"]),
            reverse=True,
        )
        return [OrderResponse(**o) for o in orders_sorted]

    @classmethod
    def get_order_by_id(cls, order_id: str) -> OrderResponse:
        """Obtiene un pedido específico por su ID."""
        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                return OrderResponse(**o)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido '{order_id}' no encontrado.",
        )

    @classmethod
    def create_order(
        cls,
        order_in: OrderCreate,
        seller_user_id: str,
        seller_username: str,
    ) -> OrderResponse:
        """
        Crea un nuevo pedido de venta desde el Área Comercial.
        Valida coherencia de peso y cantidad.
        """
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

        cls._order_counter += 1
        order_number = f"PED-2026-{str(cls._order_counter).padStart(3, '0') if hasattr(str, 'padStart') else str(cls._order_counter).zfill(3)}"
        initial_status = "BORRADOR" if order_in.is_draft else "REGISTRADO"

        now_str = datetime.utcnow().isoformat() + "Z"
        avg_weight = (order_in.min_weight_kg + order_in.max_weight_kg) / 2.0
        est_kg = round(order_in.requested_quantity * avg_weight, 2)
        est_cages = (order_in.requested_quantity + 7) // 8  # 8 aves por jaula

        client_match = next((c for c in cls._clients_store if c.get("id") == order_in.client_id or c.get("tax_id") == order_in.client_tax_id), None)
        delivery_addr = order_in.delivery_address or (client_match.get("address") if client_match else f"Punto de distribución oficial - Zona {order_in.zone_code}")

        seller_full_name = getattr(order_in, "seller_full_name", None)
        if not seller_full_name:
            if seller_username in ("vendedor1", "vendedor"):
                seller_full_name = "Juan Carlos Pérez Gálvez"
            elif seller_username == "vendedor2":
                seller_full_name = "María Elena Rodríguez Soto"
            else:
                seller_full_name = seller_username.replace(".", " ").title()

        new_order = {
            "id": f"ord-{uuid4().hex[:8]}",
            "order_number": order_number,
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
            "delivery_address": delivery_addr,
            "delivery_latitude": order_in.delivery_latitude,
            "delivery_longitude": order_in.delivery_longitude,
            "created_at": now_str,
            "updated_at": now_str,
            "audit_log": [
                {
                    "id": f"log-{uuid4().hex[:6]}",
                    "action": "CREADO",
                    "actor_username": seller_username,
                    "actor_role": "vendedor",
                    "timestamp": now_str,
                    "description": f"Pedido registrado formalmente por Comercial para {order_in.requested_quantity:,} aves.",
                }
            ],
        }

        cls._orders_store.insert(0, new_order)
        return OrderResponse(**new_order)

    @classmethod
    def aprobar_pedido(
        cls,
        order_id: str,
        user_role: str,
        gestor_username: str,
        action_req: OrderActionRequest,
    ) -> OrderResponse:
        """
        ACCIÓN CENTRAL DEL GESTOR COMERCIAL:
        El Gestor Comercial aprueba formalmente el pedido, reservando las aves del galpón.
        """
        # REGLA: Solo Gestor Comercial, Gerente Comercial o Administrador Maestro pueden aprobar
        allowed_roles = ["gestor_comercial", "gerente_comercial", "admin_sistema"]
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: Únicamente el Gestor Comercial tiene la facultad de autorizar y aprobar pedidos.",
            )

        target_order = None
        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                target_order = o
                break

        if not target_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pedido '{order_id}' no encontrado.",
            )

        if target_order["status"] == "CANCELADO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede aprobar un pedido que ha sido cancelado.",
            )

        # Asignar galpón y reservar
        farm_to_assign = action_req.farm_code or target_order.get("suggested_farm_code") or "TRAD1"
        barn_to_assign = action_req.barn_code or target_order.get("suggested_barn_code") or "G-01"
        qty_to_assign = action_req.allocated_quantity or target_order["requested_quantity"]

        if qty_to_assign <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cantidad asignada para reserva debe ser mayor a 0 aves.",
            )

        target_order["status"] = "APROBADO_RESERVADO"
        target_order["assigned_farm_code"] = farm_to_assign
        target_order["assigned_barn_code"] = barn_to_assign
        target_order["allocated_quantity"] = qty_to_assign
        target_order["gestor_username"] = gestor_username
        target_order["gestor_observation"] = (
            action_req.observation or f"Aprobación formal otorgada por Gestor Comercial ({gestor_username}). Galpón [{barn_to_assign}] de [{farm_to_assign}] asignado con {qty_to_assign:,} aves reservadas para saca."
        )
        now_str = datetime.utcnow().isoformat() + "Z"
        target_order["updated_at"] = now_str

        # Fraccionamiento de pedido (Split de Pedidos)
        original_qty = target_order.get("requested_quantity", qty_to_assign)
        if action_req.split_remaining and qty_to_assign < original_qty:
            remaining_qty = original_qty - qty_to_assign
            split_delivery_date = action_req.split_delivery_date or target_order["target_delivery_date"]

            target_order["is_split_parent"] = True
            target_order["original_requested_quantity"] = original_qty

            cls._order_counter += 1
            child_order_number = f"{target_order['order_number']}-B"
            avg_w = (target_order["min_weight_kg"] + target_order["max_weight_kg"]) / 2.0
            child_id = f"ord-{uuid4().hex[:8]}"

            child_order = {
                "id": child_id,
                "order_number": child_order_number,
                "client_id": target_order.get("client_id"),
                "client_name": target_order["client_name"],
                "client_tax_id": target_order.get("client_tax_id"),
                "seller_user_id": target_order["seller_user_id"],
                "seller_username": target_order["seller_username"],
                "zone_code": target_order["zone_code"],
                "target_delivery_date": split_delivery_date,
                "requested_quantity": remaining_qty,
                "allocated_quantity": 0,
                "min_weight_kg": target_order["min_weight_kg"],
                "max_weight_kg": target_order["max_weight_kg"],
                "sex_preference": target_order.get("sex_preference", "INDISTINTO"),
                "estimated_total_kg": round(remaining_qty * avg_w, 2),
                "estimated_cages": (remaining_qty + 7) // 8,
                "suggested_farm_code": target_order.get("suggested_farm_code"),
                "suggested_barn_code": target_order.get("suggested_barn_code"),
                "assigned_farm_code": None,
                "assigned_barn_code": None,
                "status": "REGISTRADO",
                "external_reference": target_order.get("external_reference"),
                "gestor_observation": f"Saldo fraccionado ({remaining_qty:,} aves) derivado de {target_order['order_number']}.",
                "gestor_username": gestor_username,
                "notes": f"Saldo restante por aprobación parcial del pedido matriz {target_order['order_number']}.",
                "delivery_address": target_order.get("delivery_address"),
                "created_at": now_str,
                "updated_at": now_str,
                "is_split_child": True,
                "parent_order_id": target_order["id"],
                "original_requested_quantity": original_qty,
                "audit_log": [
                    {
                        "id": f"log-{uuid4().hex[:6]}",
                        "action": "FRACCIONADO",
                        "actor_username": gestor_username,
                        "actor_role": user_role,
                        "timestamp": now_str,
                        "description": f"Generado como saldo fraccionado ({remaining_qty:,} aves) del pedido matriz {target_order['order_number']}.",
                    }
                ],
            }

            if not isinstance(target_order.get("split_children_ids"), list):
                target_order["split_children_ids"] = []
            target_order["split_children_ids"].append(child_id)
            cls._orders_store.insert(0, child_order)

            cls._add_audit_log(
                target_order,
                action="FRACCIONADO",
                actor_username=gestor_username,
                actor_role=user_role,
                description=f"Aprobación parcial de {qty_to_assign:,} aves. Saldo de {remaining_qty:,} aves fraccionado en orden {child_order_number}.",
            )

        cls._add_audit_log(
            target_order,
            action="APROBADO_RESERVADO",
            actor_username=gestor_username,
            actor_role=user_role,
            description=f"Aprobación formal confirmada en {farm_to_assign} ({barn_to_assign}) por {qty_to_assign:,} aves.",
        )

        return OrderResponse(**target_order)

    # Alias para compatibilidad de rutas
    dar_ok_pedido = aprobar_pedido

    @classmethod
    def observar_pedido(
        cls,
        order_id: str,
        user_role: str,
        gestor_username: str,
        action_req: OrderActionRequest,
    ) -> OrderResponse:
        """
        El Gestor Comercial devuelve el pedido con una observación / propuesta de ajuste al Vendedor.
        """
        allowed_roles = ["gestor_comercial", "gerente_comercial", "admin_sistema"]
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: Únicamente el Gestor Comercial puede emitir observaciones de asignación.",
            )

        if not action_req.observation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe ingresar el motivo u observación para el vendedor y cliente.",
            )

        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                o["status"] = "CON_OBSERVACION"
                o["gestor_username"] = gestor_username
                o["gestor_observation"] = action_req.observation
                o["updated_at"] = datetime.utcnow().isoformat() + "Z"
                cls._add_audit_log(
                    o,
                    action="OBSERVADO",
                    actor_username=gestor_username,
                    actor_role=user_role,
                    description=f"Pedido devuelto con observación: {action_req.observation}",
                )
                return OrderResponse(**o)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido '{order_id}' no encontrado.",
        )

    @classmethod
    def cancelar_pedido(
        cls,
        order_id: str,
        reason: Optional[str] = None,
    ) -> OrderResponse:
        """Cancela un pedido registrado."""
        for o in cls._orders_store:
            if o["id"] == order_id or o["order_number"] == order_id:
                o["status"] = "CANCELADO"
                o["notes"] = f"{o.get('notes') or ''} [Cancelado: {reason or 'Sin motivo'}]".strip()
                o["updated_at"] = datetime.utcnow().isoformat() + "Z"
                return OrderResponse(**o)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pedido '{order_id}' no encontrado.",
        )

    @classmethod
    def get_programacion_transporte(
        cls,
        delivery_date: Optional[str] = None,
    ) -> ProgramacionTransporteResponse:
        """
        Genera la Hoja de Programación Diaria para el equipo de Transporte y Logística.
        Filtra únicamente los pedidos formalmente aprobados por el Gestor (APROBADO_RESERVADO).
        """
        approved_orders = [o for o in cls._orders_store if o["status"] == "APROBADO_RESERVADO"]
        if delivery_date:
            approved_orders = [o for o in approved_orders if o.get("target_delivery_date") == delivery_date]

        # Ordenar por fecha de entrega, granja y galpón
        approved_orders = sorted(
            approved_orders,
            key=lambda x: (
                x.get("target_delivery_date") or "",
                x.get("assigned_farm_code") or "",
                x.get("assigned_barn_code") or "",
            )
        )

        items: List[ProgramacionTransporteItem] = []
        total_birds = 0
        total_cages = 0
        total_kg = 0.0

        for o in approved_orders:
            allocated = o.get("allocated_quantity") or o.get("requested_quantity") or 0
            cages = o.get("estimated_cages") or int(math.ceil(allocated / 8.0))
            order_kg = o.get("estimated_total_kg")
            if not order_kg:
                avg_w = (o["min_weight_kg"] + o["max_weight_kg"]) / 2.0
                order_kg = round(allocated * avg_w, 2)
            tons = round(order_kg / 1000.0, 2)

            total_birds += allocated
            total_cages += cages
            total_kg += order_kg

            items.append(
                ProgramacionTransporteItem(
                    order_id=o["id"],
                    order_number=o["order_number"],
                    target_delivery_date=o["target_delivery_date"],
                    client_name=o["client_name"],
                    client_tax_id=o.get("client_tax_id"),
                    zone_code=o["zone_code"],
                    assigned_farm_code=o.get("assigned_farm_code") or "POR ASIGNAR",
                    assigned_barn_code=o.get("assigned_barn_code") or "POR ASIGNAR",
                    allocated_quantity=allocated,
                    estimated_cages=cages,
                    estimated_total_kg=order_kg,
                    estimated_tons=tons,
                    sex_preference=o.get("sex_preference") or "INDISTINTO",
                    min_weight_kg=o["min_weight_kg"],
                    max_weight_kg=o["max_weight_kg"],
                    gestor_username=o.get("gestor_username"),
                    notes=o.get("notes"),
                    external_reference=o.get("external_reference"),
                    transport_assigned=o.get("transport_assigned", False),
                    transport_plate=o.get("transport_plate"),
                    transport_driver_name=o.get("transport_driver_name"),
                    transport_crew=o.get("transport_crew"),
                    transport_shift=o.get("transport_shift"),
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

