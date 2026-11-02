# ==============================================================================
# PRUEBAS DEL MÓDULO COMERCIAL Y PROGRAMACIÓN
# Archivo: backend/tests/test_comercial.py
# ==============================================================================

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_list_comercial_clients():
    """Verifica que el catálogo de clientes autorizados retorne los clientes predeterminados."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/comercial/clients",
            headers={"Authorization": "Bearer dev-token-vendedor"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5
        assert any("Santa Anita" in c["business_name"] for c in data)


@pytest.mark.asyncio
async def test_create_order_by_vendedor():
    """Verifica que un vendedor pueda registrar un nuevo pedido de venta."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "client_name": "Pollerías Norky's Corp S.A.",
            "client_tax_id": "20100456789",
            "zone_code": "METROPOLITANA",
            "target_delivery_date": "2026-11-06",
            "requested_quantity": 3500,
            "min_weight_kg": 2.15,
            "max_weight_kg": 2.35,
            "suggested_farm_code": "TRAD1",
            "suggested_barn_code": "G-02",
            "external_reference": "OC-TEST-001",
            "notes": "Pedido de prueba automatizada",
        }
        response = await ac.post(
            "/api/v1/comercial/orders",
            json=payload,
            headers={"Authorization": "Bearer dev-token-vendedor"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["order_number"].startswith("PED-2026-")
        assert data["status"] == "REGISTRADO"
        assert data["requested_quantity"] == 3500


@pytest.mark.asyncio
async def test_vendedor_cannot_give_ok():
    """Verifica que un vendedor NO tenga autorización para aprobar un pedido."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/comercial/orders/ord-0002/aprobar",
            json={"farm_code": "TRAD2", "barn_code": "G-03"},
            headers={"Authorization": "Bearer dev-token-vendedor"},
        )
        # Debe ser 403 Forbidden
        assert response.status_code == 403
        assert "Únicamente el Gestor Comercial" in response.json()["detail"]


@pytest.mark.asyncio
async def test_gestor_comercial_can_give_ok():
    """Verifica que el Gestor Comercial SÍ pueda aprobar y autorizar la reserva."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/comercial/orders/ord-0002/aprobar",
            json={
                "farm_code": "TRAD2",
                "barn_code": "G-03",
                "allocated_quantity": 3000,
                "observation": "Aprobación formal verificada por Gestor Comercial. Stock conforme para saca.",
            },
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "APROBADO_RESERVADO"
        assert data["assigned_farm_code"] == "TRAD2"
        assert data["assigned_barn_code"] == "G-03"
        assert data["allocated_quantity"] == 3000


@pytest.mark.asyncio
async def test_create_comercial_client():
    """Verifica que se pueda registrar un nuevo cliente desde el formulario comercial."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "business_name": "Inversiones Avícolas Lurín S.A.C.",
            "tax_id": "20789123456",
            "zone_code": "SUR",
            "address": "Av. Separadora Industrial 123",
            "contact_phone": "+51 987 654 321",
            "preferred_min_weight": 2.20,
            "preferred_max_weight": 2.50,
        }
        response = await ac.post(
            "/api/v1/comercial/clients",
            json=payload,
            headers={"Authorization": "Bearer dev-token-vendedor"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["business_name"] == "Inversiones Avícolas Lurín S.A.C."
        assert data["tax_id"] == "20789123456"
        assert data["zone_code"] == "SUR"
        assert "id" in data


@pytest.mark.asyncio
async def test_get_programacion_transporte():
    """Verifica que se pueda obtener la Hoja de Programación Diaria para el equipo de Transporte."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/comercial/programacion-transporte",
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_orders" in data
        assert "total_birds" in data
        assert "total_cages" in data
        assert "estimated_trucks" in data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert data["total_orders"] >= 1
        first_item = data["items"][0]
        assert "order_number" in first_item
        assert "assigned_farm_code" in first_item
        assert "assigned_barn_code" in first_item


@pytest.mark.asyncio
async def test_list_transport_vehicles():
    """Verifica que se liste la flota de camiones de distribución con choferes y capacidades."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/comercial/transport/vehicles",
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert response.status_code == 200
        vehicles = response.json()
        assert len(vehicles) >= 6
        plates = [v["plate"] for v in vehicles]
        assert "T8C-940" in plates
        assert "W5A-712" in plates


@pytest.mark.asyncio
async def test_assign_transport_by_gestor():
    """Verifica que el Gestor Comercial pueda asignar formalmente una unidad de transporte a un pedido aprobado."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "vehicle_id": "VH-002",
            "plate": "V6B-821",
            "driver_name": "José Luis Quispe",
            "driver_phone": "+51 992 345 678",
            "crew_name": "Cuadrilla Centro 2",
            "shift": "MADRUGADA",
            "transport_notes": "Carga prioritaria en rampa 1",
        }
        response = await ac.post(
            "/api/v1/comercial/orders/ord-0001/assign-transport",
            json=payload,
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert response.status_code == 200
        order = response.json()
        assert order["transport_assigned"] is True
        assert order["transport_plate"] == "V6B-821"
        assert order["transport_driver_name"] == "José Luis Quispe"
        assert order["transport_shift"] == "MADRUGADA"


@pytest.mark.asyncio
async def test_vendedor_cannot_assign_transport():
    """Verifica que un vendedor NO tenga permisos para designar transporte de distribución."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "vehicle_id": "VH-001",
            "shift": "MANANA",
        }
        response = await ac.post(
            "/api/v1/comercial/orders/ord-0001/assign-transport",
            json=payload,
            headers={"Authorization": "Bearer dev-token-vendedor"},
        )
        assert response.status_code == 403
        assert "Únicamente el Gestor Comercial" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_dispatch_lifecycle_phases():
    """Verifica el ciclo de vida del despacho en sus 4 fases y su impacto en el estado."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Avanzar a EN_TRANSITO
        resp1 = await ac.patch(
            "/api/v1/comercial/orders/ord-0001/dispatch-phase",
            json={"dispatch_phase": "EN_TRANSITO", "notes": "Salida de balanza con precintos"},
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["dispatch_phase"] == "EN_TRANSITO"
        assert data1["dispatch_phase_updated_at"] is not None

        # 2. Avanzar a ENTREGADO_CONFORME
        resp2 = await ac.patch(
            "/api/v1/comercial/orders/ord-0001/dispatch-phase",
            json={"dispatch_phase": "ENTREGADO_CONFORME", "notes": "Guía firmada por recepción"},
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["dispatch_phase"] == "ENTREGADO_CONFORME"
        assert data2["status"] == "DESPACHADO"


@pytest.mark.asyncio
async def test_invalid_dispatch_phase_rejected():
    """Verifica que fases desconocidas sean rechazadas con 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            "/api/v1/comercial/orders/ord-0001/dispatch-phase",
            json={"dispatch_phase": "FASE_INVENTADA"},
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert resp.status_code == 400
        assert "no válida" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_partial_approval_and_order_split():
    """Verifica la aprobación parcial y generación automática del saldo fraccionado (Split)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "farm_code": "PACI6",
            "barn_code": "G-02",
            "allocated_quantity": 3000,
            "split_remaining": True,
            "split_delivery_date": "2026-11-06",
            "observation": "Aprobación parcial de 3,000 aves por cupo disponible de galpón",
        }
        resp = await ac.post(
            "/api/v1/comercial/orders/ord-0003/dar-ok",
            json=payload,
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert resp.status_code == 200
        parent_data = resp.json()
        assert parent_data["allocated_quantity"] == 3000
        assert parent_data["is_split_parent"] is True
        assert parent_data["status"] == "APROBADO_RESERVADO"

        # Verificar que el pedido hijo con el saldo de 2,000 aves fue registrado
        all_orders_resp = await ac.get(
            "/api/v1/comercial/orders",
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        orders = all_orders_resp.json()
        child = next((o for o in orders if o["order_number"] == "PED-2026-003-B"), None)
        assert child is not None
        assert child["requested_quantity"] == 2000
        assert child["status"] == "REGISTRADO"
        assert child["is_split_child"] is True
        assert child["target_delivery_date"] == "2026-11-06"


@pytest.mark.asyncio
async def test_assign_transport_with_slotting_and_audit():
    """Verifica asignación de transporte con ventana de carga nocturna (slotting) y trazabilidad."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "vehicle_id": "VH-001",
            "shift": "NOCHE",
            "loading_slot_time": "21:00 - 23:00 hrs",
            "transport_notes": "Control de temperatura nocturna",
        }
        resp = await ac.post(
            "/api/v1/comercial/orders/ord-0003/assign-transport",
            json=payload,
            headers={"Authorization": "Bearer dev-token-gestor_comercial"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["loading_slot_time"] == "21:00 - 23:00 hrs"
        assert len(data["audit_log"]) >= 2
        # Debe contener registro de auditoría de asignación de transporte
        assert any(entry["action"] == "TRANSPORTE_ASIGNADO" for entry in data["audit_log"])




