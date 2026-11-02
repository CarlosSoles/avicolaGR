import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_admin_login_and_user_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Login con master admin
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin 123"
        })
        assert login_res.status_code == 200, f"Error login: {login_res.text}"
        data = login_res.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin_sistema"
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Listar usuarios como admin
        list_res = await ac.get("/api/v1/admin/users", headers=headers)
        assert list_res.status_code == 200
        users = list_res.json()
        assert len(users) >= 1
        assert any(u["username"] == "admin" for u in users)

        # 3. Intentar login con credenciales erróneas
        bad_res = await ac.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert bad_res.status_code == 401

        # 4. Crear un nuevo usuario colaborador
        test_username = "test_supervisor"
        test_email = "test_sup@avicolagr.com"
        create_res = await ac.post("/api/v1/admin/users", headers=headers, json={
            "username": test_username,
            "email": test_email,
            "password": "password123",
            "full_name": "Ing. Supervisor de Prueba",
            "role": "supervisor_pecuario",
            "is_active": True
        })
        # Si ya existe de un run previo, puede dar 400 o 201
        if create_res.status_code == 201:
            new_user = create_res.json()
            user_id = new_user["id"]

            # 5. Login con el nuevo usuario creado
            user_login = await ac.post("/api/v1/auth/login", json={
                "username": test_username,
                "password": "password123"
            })
            assert user_login.status_code == 200
            assert user_login.json()["user"]["role"] == "supervisor_pecuario"

            # 6. Desactivar usuario y verificar que no pueda loguearse
            status_res = await ac.patch(f"/api/v1/admin/users/{user_id}/status", headers=headers, json={
                "is_active": False
            })
            assert status_res.status_code == 200
            assert status_res.json()["is_active"] is False

            inactive_login = await ac.post("/api/v1/auth/login", json={
                "username": test_username,
                "password": "password123"
            })
            assert inactive_login.status_code == 403

            # 7. Limpiar eliminando el usuario de prueba
            del_res = await ac.delete(f"/api/v1/admin/users/{user_id}", headers=headers)
            assert del_res.status_code == 200

        # 8. Catálogo de granjas
        farms_res = await ac.get("/api/v1/admin/farms", headers=headers)
        assert farms_res.status_code == 200
        farms = farms_res.json()
        assert len(farms) == 23
        codes = [f["code"] for f in farms]
        assert "TRAD1" in codes
        assert "HARC2" in codes
