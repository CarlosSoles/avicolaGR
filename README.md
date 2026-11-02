# 🐔 Backend - Sistema de Planificación de Saca de Aves (Avícola GR)

Backend modular desarrollado con **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL en Supabase** y el copiloto de IA **ROXI (Google Gemini 2.0 Flash a costo $0.00)**.

Este repositorio está preparado para ejecutarse localmente y para desplegarse de forma 100% gratuita y sin bloqueos de firewall en **Hugging Face Spaces (Docker)**.

---

## 📋 Tabla de Contenidos
1. [Arquitectura y Estructura](#-arquitectura-y-estructura)
2. [Configuración de Base de Datos en Supabase](#-configuración-de-base-de-datos-en-supabase)
3. [Instalación y Ejecución Local](#-instalación-y-ejecución-local)
4. [Ejecución de Pruebas Automatizadas](#-ejecución-de-pruebas-automatizadas)
5. [Guía de Despliegue en Hugging Face Spaces (Gratis)](#-guía-de-despliegue-en-hugging-face-spaces-gratis)
6. [Conexión con el Frontend (Cloudflare Pages)](#-conexión-con-el-frontend-cloudflare-pages)
7. [Endpoints Principales de la API](#-endpoints-principales-de-la-api)

---

## 🏛 Arquitectura y Estructura

El sistema sigue una arquitectura limpia hexagonal/modular con separación estricta de contextos delimitados (*Bounded Contexts*):

```text
backend/
├── Dockerfile                   # Configuración para Hugging Face Spaces (Puerto 7860)
├── .dockerignore                # Archivos omitidos en el contenedor Docker
├── .gitignore                   # Exclusiones de Git (previene filtrado de .env o venv)
├── requirements.txt             # Dependencias Python fijadas
├── pytest.ini                   # Configuración de pruebas asíncronas
├── .env.example                 # Plantilla de variables de entorno requeridas
├── database/                    # Scripts SQL oficiales para Supabase
│   ├── schema.sql               # Esquema DDL maestro completo (Tablas, Vistas, CDC)
│   ├── seed.sql                 # Datos semilla (23 Granjas, Galpones, Clientes, Flota)
│   └── migration_v2_comercial_roxi.sql # Migración incremental para bases de datos existentes
├── tests/                       # Suite de pruebas automatizadas con pytest
└── app/
    ├── main.py                  # Entrada ASGI FastAPI y configuración de CORS
    ├── core/                    # Conexión DB asyncpg, Settings y Seguridad JWT
    ├── shared/                  # Excepciones transversales de dominio
    └── modules/
        ├── admin/               # Autenticación, perfiles y catálogos técnicos
        ├── pecuaria/            # Pesajes ave por ave, especiales y Tabla General de Saldo
        ├── comercial/           # Captura de pedidos, flota, lifecycle y split
        └── agent/               # Agente ROXI: Gemini 2.0 Flash, distancias y scoring
```

---

## 🗄 Configuración de Base de Datos en Supabase

### Opción A: Base de Datos Nueva (Instalación desde Cero)
1. Entra a tu proyecto en [Supabase Dashboard](https://supabase.com/dashboard).
2. Ve a la sección **SQL Editor** en la barra lateral.
3. Abre y copia el contenido de [`database/schema.sql`](database/schema.sql) y haz clic en **Run**.
4. Luego, abre y copia el contenido de [`database/seed.sql`](database/seed.sql) y presiona **Run**.

### Opción B: Base de Datos Existente (Migración Incremental)
Si ya tenías datos creados en Supabase y solo deseas incorporar las tablas de **Flota**, **Campos de ROXI** y **Fraccionamiento de Pedidos**:
* Copia y ejecuta en el **SQL Editor** el archivo [`database/migration_v2_comercial_roxi.sql`](database/migration_v2_comercial_roxi.sql).

---

## 💻 Instalación y Ejecución Local

### 1. Clonar el repositorio y entrar a la carpeta
```bash
git clone <URL_DE_TU_REPOSITORIO_BACKEND>
cd backend
```

### 2. Crear y activar el entorno virtual Python (3.10 o superior)
* **En Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **En Linux / macOS / WSL:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Copia la plantilla y crea tu archivo `.env`:
* **Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```
* **Linux / Mac:**
  ```bash
  cp .env.example .env
  ```

Abre `.env` y coloca tus claves reales:
```env
DATABASE_URL="postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?ssl=require"
SUPABASE_URL="https://[PROJECT_REF].supabase.co"
SUPABASE_ANON_KEY="tu-anon-key"
SUPABASE_SERVICE_ROLE_KEY="tu-service-role-key"
GEMINI_API_KEY="tu-api-key-de-google-ai-studio"
GEMINI_MODEL="gemini-2.0-flash"
```

### 5. Iniciar el servidor de desarrollo
```bash
uvicorn app.main:app --reload --port 8000
```

* **Documentación Interactiva (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Documentación ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Ejecución de Pruebas Automatizadas

Para validar que todos los módulos y el agente ROXI funcionen al 100%:

```bash
# Ejecutar todas las pruebas (22 tests)
pytest -v

# Ejecutar únicamente las pruebas del Agente ROXI
pytest tests/test_roxi_agent.py -v
```

---

## 🚀 Guía de Despliegue en Hugging Face Spaces (Gratis)

Hugging Face Spaces es **100% gratuito**, te otorga **2 vCPUs y 16 GB de RAM**, y sus dominios (`*.hf.space`) **nunca son bloqueados por redes universitarias**.

### Paso 1: Crear el Space en Hugging Face
1. Inicia sesión en [huggingface.co](https://huggingface.co).
2. Haz clic en tu perfil $\rightarrow$ **New Space**.
3. Configura:
   * **Space name:** `avicola-backend` (o el nombre que elijas).
   * **License:** `mit` u `other`.
   * **Select the Space SDK:** Selecciona **Docker** $\rightarrow$ **Blank**.
   * **Space hardware:** Selecciona **CPU Basic · 2 vCPU · 16 GB RAM · Free** ($0/mo).
   * **Visibility:** `Public` (para que el frontend pueda conectarse).
4. Haz clic en **Create Space**.

### Paso 2: Configurar las Variables de Entorno y Secretos en el Space
1. En tu Space recién creado, ve a la pestaña **Settings** (engranaje).
2. Baja a la sección **Variables and secrets**.
3. Haz clic en **New secret** y agrega cada una de las siguientes variables (con tus valores reales):

| Secret Name | Valor de Ejemplo | Descripción |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:...` | Cadena directa a Supabase (puerto 5432) |
| `SUPABASE_URL` | `https://kpssroraigncmpkwxiyb.supabase.co` | URL del proyecto Supabase |
| `SUPABASE_ANON_KEY` | `eyJhbG...` | Anon Key pública de Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJhbG...` | Service Role secreta de Supabase |
| `GEMINI_API_KEY` | `AQ.Ab8RN6KeyKZES...` | Tu API Key de Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Modelo de Gemini a usar |
| `ENVIRONMENT` | `production` | Modo de ejecución |

> **Nota sobre el puerto:** El archivo `Dockerfile` incluido ya tiene preconfigurado el puerto `7860` que Hugging Face requiere por defecto.

### Paso 3: Subir el código del Backend al Space
En tu terminal local, dentro de la carpeta `backend`:

```bash
# 1. Inicializar repositorio git si no está inicializado
git init
git branch -M main

# 2. Agregar el remoto de Hugging Face (lo encuentras en la pestaña Files -> Clone repository)
git remote add origin https://huggingface.co/spaces/<TU_USUARIO>/<NOMBRE_DE_TU_SPACE>

# 3. Guardar y subir los archivos
git add .
git commit -m "feat: backend modular avicola con agente ROXI para Hugging Face"
git push -u origin main --force
```

*(Cuando te pida contraseña al hacer push, ingresa tu **Access Token** de Hugging Face generado en `Settings -> Access Tokens` con rol `Write`).*

Hugging Face compilará el contenedor automáticamente en ~2 minutos. Una vez diga **Running**, tu API estará activa en:
```text
https://<TU_USUARIO>-<NOMBRE_DE_TU_SPACE>.hf.space/docs
```

---

## 🌐 Conexión con el Frontend (Cloudflare Pages)

Cuando despliegues el Frontend (React + Vite) en **Cloudflare Pages** o **GitHub Pages**, configura la variable de entorno en el panel de Cloudflare Pages:

```text
VITE_API_BASE_URL=https://<TU_USUARIO>-<NOMBRE_DE_TU_SPACE>.hf.space/api/v1
```

La configuración CORS del backend ya incluye la directiva `allow_origin_regex=r"^https?://.*"`, lo que permite que tu frontend se comunique con el backend sin ningún bloqueo de CORS ni de red universitaria.

---

## 📡 Endpoints Principales de la API

| Módulo | Método | Endpoint | Descripción |
| :--- | :---: | :--- | :--- |
| **Diagnóstico** | `GET` | `/api/v1/health` | Estado del backend y pool de Supabase. |
| **Auth** | `POST` | `/api/v1/auth/login` | Login con credenciales de usuario. |
| **Pecuaria** | `GET` | `/api/v1/pecuaria/tabla-general-saldo` | Saldos oficiales en vivo de las 23 granjas. |
| **Comercial** | `GET` | `/api/v1/comercial/orders` | Bandeja de pedidos de venta. |
| **Comercial** | `POST` | `/api/v1/comercial/orders` | Registro de nuevo pedido por el vendedor. |
| **Gestión** | `POST` | `/api/v1/comercial/orders/{id}/dar-ok` | Aprobación formal y reserva en galpón. |
| **Gestión** | `POST` | `/api/v1/comercial/orders/{id}/assign-transport` | Asignación de flota y turno de despacho. |
| **Agente ROXI** | `POST` | `/api/v1/agent/recommend-barn` | Inferencia de galpón óptimo con Gemini 2.0. |
| **Agente ROXI** | `POST` | `/api/v1/agent/chat` | Chat operativo con guardrails de saca. |
| **Agente ROXI** | `GET` | `/api/v1/agent/status` | Diagnóstico de latencia y estado de IA. |
