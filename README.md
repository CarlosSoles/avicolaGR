# 🐔 Backend — Sistema de Planificación de Saca de Aves (Avícola GR)

Backend modular desarrollado con **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL en Supabase** y el copiloto **ROXI**.

Desplegado en **Render** (contenedor Docker). El frontend se publica en **Cloudflare Pages** y consume la API a través de un **Cloudflare Worker** que actúa como proxy con dominio propio.

---

## 📋 Tabla de Contenidos
1. [Arquitectura y Estructura](#-arquitectura-y-estructura)
2. [Instalación y Ejecución Local](#-instalación-y-ejecución-local)
3. [Base de Datos y Migraciones](#-base-de-datos-y-migraciones)
4. [Pruebas Automatizadas](#-pruebas-automatizadas)
5. [Despliegue del Backend en Render](#-despliegue-del-backend-en-render)
6. [Cloudflare Worker (proxy de API)](#-cloudflare-worker-proxy-de-api)
7. [Frontend en Cloudflare Pages](#-frontend-en-cloudflare-pages)
8. [Endpoints Principales](#-endpoints-principales)

---

## 🏛 Arquitectura y Estructura

Arquitectura modular por contextos delimitados (*Bounded Contexts*), con capas `domain` / `application` / `infrastructure` / `presentation`.

```text
backend/
├── Dockerfile                   # Imagen para Render (puerto dinámico vía $PORT)
├── .dockerignore
├── requirements.txt             # Dependencias Python fijadas
├── pytest.ini                   # Configuración de pruebas asíncronas
├── .env.example                 # Plantilla de variables de entorno
├── database/                    # Scripts SQL para Supabase
│   ├── schema.sql               # Esquema base
│   ├── seed.sql                 # Datos semilla (23 granjas, galpones, flota, clientes)
│   ├── migration_v2_comercial_roxi.sql
│   ├── migration_v3_coordinates.sql
│   ├── migration_v4_client_coordinates.sql
│   ├── migration_v5_order_density.sql
│   ├── migration_v6_order_status_check.sql
│   ├── migration_v7_notification_reads.sql
│   └── migration_v8_notifications.sql
├── tests/                       # Pruebas automatizadas (pytest)
└── app/
    ├── main.py                  # Entrada ASGI, CORS y montaje de routers
    ├── core/                    # Settings, conexión asyncpg y seguridad JWT
    ├── shared/                  # Excepciones, auditoría y notificaciones
    └── modules/
        ├── admin/               # Autenticación, usuarios, granjas y notificaciones
        ├── pecuaria/            # Pesajes, especiales, movimientos y saldos
        ├── comercial/           # Pedidos, clientes, densidad, flota y despacho
        └── agent/               # Agente ROXI (recomendación de galpón)
```

### Notas de comportamiento
- La base de datos es la **única fuente de verdad** del módulo comercial: no hay respaldos en memoria en producción.
- El **vendedor solo ve y modifica sus propios pedidos** (aislamiento por `seller_username` en la API).
- El estado "leído" de las notificaciones se guarda por usuario en `notification_reads`.
- Las notificaciones se generan por eventos (pedido creado/aprobado/observado, transporte, pesajes, especiales).

---

## 💻 Instalación y Ejecución Local

### 1. Clonar el repositorio y entrar en la carpeta
```bash
git clone <URL_DEL_REPOSITORIO>
cd backend
```

### 2. Crear y activar el entorno virtual (Python 3.10+)
* **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

> Si PowerShell bloquea `Activate.ps1`, puedes ejecutar sin activar:
> `.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`

### 3. Instalar dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```powershell
Copy-Item .env.example .env    # Windows
cp .env.example .env           # Linux / macOS
```

Variables principales:

```env
ENVIRONMENT="development"
DEBUG=True
API_V1_PREFIX="/api/v1"
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

DATABASE_URL="postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?ssl=require"
SUPABASE_URL="https://[PROJECT_REF].supabase.co"
SUPABASE_ANON_KEY="..."
SUPABASE_SERVICE_ROLE_KEY="..."
SUPABASE_JWT_SECRET="..."

GEMINI_API_KEY="..."
GEMINI_MODEL="gemini-2.0-flash"
```

> ⚠️ En producción `DEBUG` debe ser `False`. Con `DEBUG=True` el backend acepta tokens de desarrollo (`dev-token-*`) y omite la validación de firma.

### 5. Iniciar el servidor de desarrollo
```bash
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Healthcheck: http://localhost:8000/health (alias) y http://localhost:8000/api/v1/health

---

## 🗄 Base de Datos y Migraciones

Ejecutar en el **SQL Editor de Supabase**, en este orden:

1. `database/schema.sql`
2. `database/seed.sql`
3. `database/migration_v2_comercial_roxi.sql`
4. `database/migration_v3_coordinates.sql`
5. `database/migration_v4_client_coordinates.sql`
6. `database/migration_v5_order_density.sql`
7. `database/migration_v6_order_status_check.sql`
8. `database/migration_v7_notification_reads.sql`
9. `database/migration_v8_notifications.sql`

Las migraciones son incrementales e idempotentes en su mayoría (`IF NOT EXISTS`, `ON CONFLICT`). Si partes de una base ya existente, ejecuta desde la migración que corresponda.

### Tablas clave
| Tabla | Uso |
| :--- | :--- |
| `farms`, `barns` | Catálogo de 23 granjas y 230 galpones |
| `batches`, `barn_inventories` | Lotes e inventario (saldo disponible es columna generada) |
| `orders` | Pedidos, densidad de carga, transporte y despacho |
| `clients` | Catálogo de clientes con coordenadas de entrega |
| `notification_reads`, `notifications` | Estado leído y notificaciones por evento |
| `audit_logs` | Trazabilidad de operaciones |

---

## 🧪 Pruebas Automatizadas

```bash
pytest -v
pytest tests/test_roxi_agent.py -v
```

> Las pruebas de integración usan la conexión real configurada en `.env` y los tokens `dev-token-*` (requieren `DEBUG=True` y el usuario de desarrollo en `users_profile`).

---

## 🚀 Despliegue del Backend en Render

El backend se despliega como **Web Service (Docker)** en Render.

### 1. Crear el servicio
1. En [render.com](https://render.com) → **New** → **Web Service**.
2. Conecta el repositorio del backend.
3. Configura:
   - **Environment:** `Docker`
   - **Dockerfile Path:** `./Dockerfile`
   - **Health Check Path:** `/health`
   - **Auto-Deploy:** según tu preferencia (`On Commit` o manual)

### 2. Variables de entorno en Render
En **Environment → Environment Variables**, define:

| Variable | Valor |
| :--- | :--- |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `False` |
| `DATABASE_URL` | Cadena de Supabase (asyncpg, puerto 5432 o pooler 6543) |
| `SUPABASE_URL` | `https://<PROJECT_REF>.supabase.co` |
| `SUPABASE_ANON_KEY` | Anon key pública |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role (secreta) |
| `SUPABASE_JWT_SECRET` | JWT secret del proyecto |
| `GEMINI_API_KEY` | API key de Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.0-flash` |

> Render inyecta la variable `PORT`; el contenedor arranca con `uvicorn ... --port ${PORT}`. No fijes el puerto manualmente.

### 3. Verificación
Cuando el servicio esté **Live**, comprueba:

```text
https://<SERVICIO>.onrender.com/health
https://<SERVICIO>.onrender.com/docs
```

Ambas deben responder `200`. El healthcheck reporta también el estado de la base de datos.

### 4. Consideraciones
- El plan gratuito de Render **duerme** el servicio tras inactividad: la primera petición puede tardar ~30-60 s. El frontend hace un *warm-up* al cargar.
- El pool de conexiones está configurado para Supabase (PgBouncer/Supavisor): `statement_cache_size=0` y nombres de sentencia únicos.

---

## ☁️ Cloudflare Worker (proxy de API)

El frontend no consume directamente el dominio de Render: pasa por un **Cloudflare Worker** que:

- Expone la API bajo un dominio propio y estable.
- Evita bloqueos de red y añade control de CORS/origen.
- Permite cambiar el backend sin tocar el frontend.

Configuración típica del Worker (ejemplo):

```js
export default {
  async fetch(request) {
    const backend = "https://<SERVICIO>.onrender.com";
    const url = new URL(request.url);
    const target = backend + url.pathname + url.search;

    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
      "Access-Control-Allow-Headers": "Authorization,Content-Type",
    };

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });

    const response = await fetch(target, {
      method: request.method,
      headers: request.headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    });

    const out = new Response(response.body, response);
    Object.entries(cors).forEach(([k, v]) => out.headers.set(k, v));
    return out;
  },
};
```

La URL resultante tiene la forma:

```text
https://<WORKER>.<subdominio>.workers.dev/api/v1
```

---

## 🌐 Frontend en Cloudflare Pages

El frontend (React + Vite) se publica en **Cloudflare Pages**.

### Build
| Parámetro | Valor |
| :--- | :--- |
| Framework preset | `Vite` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `fronted` |

### Variables de entorno (Production)
```env
VITE_API_URL="https://<WORKER>.<subdominio>.workers.dev/api/v1"
VITE_SUPABASE_URL="https://<PROJECT_REF>.supabase.co"
VITE_SUPABASE_ANON_KEY="<anon-key>"
```

> El frontend usa `VITE_API_URL` (no `VITE_API_BASE_URL`).

### SPA routing
El proyecto incluye `public/_redirects` con:

```text
/*    /index.html   200
```

Esto evita 404 al recargar rutas como `/comercial` o `/admin`.

### CORS
El backend permite el origen del frontend mediante `CORS_ORIGINS` y `allow_origin_regex`. Mantén ambos alineados con el dominio real de Pages (`*.pages.dev` y el dominio personalizado si aplica).

---

## 📡 Endpoints Principales

| Módulo | Método | Endpoint | Descripción |
| :--- | :---: | :--- | :--- |
| **Salud** | `GET` | `/health` · `/api/v1/health` | Estado del backend y de la base de datos. |
| **Auth** | `POST` | `/api/v1/auth/login` | Login con usuario o correo. |
| **Auth** | `GET` | `/api/v1/auth/me` | Perfil del usuario autenticado. |
| **Admin** | `GET` | `/api/v1/admin/users` | Listado de usuarios (solo admin). |
| **Admin** | `PUT` | `/api/v1/admin/farms/{code}/coordinates` | Coordenadas GPS de la granja. |
| **Pecuaria** | `GET` | `/api/v1/pecuaria/tabla-general-saldo` | Saldo en vivo por galpón. |
| **Pecuaria** | `POST` | `/api/v1/pecuaria/samples` · `/samples/{id}/weights` | Pesaje ave por ave. |
| **Pecuaria** | `POST` | `/api/v1/pecuaria/specials` | Registro de aves especiales. |
| **Comercial** | `GET` | `/api/v1/comercial/orders` | Pedidos (el vendedor ve solo los suyos). |
| **Comercial** | `POST` | `/api/v1/comercial/orders` | Registro de pedido con densidad. |
| **Comercial** | `POST` | `/api/v1/comercial/orders/{id}/aprobar` | Aprobación y reserva. |
| **Comercial** | `PATCH` | `/api/v1/comercial/orders/{id}/density` | Ajuste de densidad (aves/jaula). |
| **Comercial** | `POST` | `/api/v1/comercial/orders/{id}/assign-transport` | Asignación de flota. |
| **Comercial** | `GET` | `/api/v1/comercial/clients` · `PUT /clients/{id}` | Catálogo de clientes y coordenadas. |
| **Notificaciones** | `GET` | `/api/v1/notifications` | Notificaciones del usuario. |
| **Notificaciones** | `PUT` | `/api/v1/notifications/reads` | Marcar leídas / no leídas. |
| **ROXI** | `POST` | `/api/v1/agent/recommend-barn` | Recomendación de galpón. |
| **ROXI** | `GET` | `/api/v1/agent/status` | Diagnóstico del agente. |

---

## 🔐 Notas de Seguridad

- `DEBUG=False` obligatorio en producción; desactiva los tokens `dev-token-*` y el fallback sin firma.
- `SUPABASE_JWT_SECRET` debe estar definido; el valor por defecto del código es solo para desarrollo.
- Los vendedores solo acceden a sus pedidos; el resto de roles mantienen visibilidad completa.
- No subir `.env` al repositorio (ya está en `.gitignore`).
