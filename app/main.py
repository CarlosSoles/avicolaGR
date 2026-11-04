# ==============================================================================
# ENTRADA PRINCIPAL DE LA APLICACIÓN FASTAPI
# Archivo: backend/app/main.py
# ==============================================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.shared.domain.exceptions import DomainException

# Importación de routers modulares
from app.modules.pecuaria.presentation.router import router as pecuaria_router
from app.modules.admin.presentation.router import auth_router, admin_router, notifications_router
from app.modules.comercial.presentation.router import router as comercial_router
from app.modules.agent.presentation.router import router as agent_router
from app.modules.admin.application.service import AdminService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    Verifica la conexión a Supabase PostgreSQL e inicializa el usuario admin al iniciar.
    """
    print(f"Iniciando {settings.PROJECT_NAME} en modo {settings.ENVIRONMENT}...")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("Conexión a PostgreSQL (Supabase) establecida exitosamente.")

        # Asegurar existencia del admin principal
        async with AsyncSessionLocal() as session:
            admin_service = AdminService(session)
            await admin_service.ensure_master_admin()
            print("Cuenta de Administrador Maestro ('admin' / 'admin 123') lista.")
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo conectar a la base de datos o inicializar: {e}")
        print("Asegúrate de configurar las variables en backend/.env")
    
    yield
    
    print("Cerrando conexiones del pool de base de datos...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.2.0",
    description="Backend modular para la planificación de saca de aves coordinando Pecuaria, Comercial, Gerencia Comercial y Administración.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración de CORS con soporte para entornos locales, Cloudflare Pages, Worker y Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Manejador global de excepciones del dominio de negocio
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_type": exc.__class__.__name__,
            "detail": exc.message,
        },
    )


# Montar routers modulares
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(pecuaria_router, prefix=settings.API_V1_PREFIX)
app.include_router(comercial_router, prefix=settings.API_V1_PREFIX)
app.include_router(agent_router, prefix=settings.API_V1_PREFIX)


# Endpoint de bienvenida
@app.get("/", tags=["General"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": "1.2.0",
        "status": "online",
        "docs": "/docs",
    }


# Healthcheck de sistema y base de datos
# Se expone en dos rutas: la canónica versionada y el alias corto /health,
# requerido por monitores externos y healthchecks de la plataforma de despliegue.
@app.get("/health", tags=["Salud del Sistema"], include_in_schema=False)
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Salud del Sistema"])
async def health_check():
    db_status = "connected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    return {
        "status": "healthy" if "disconnected" not in db_status else "degraded",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
    }
