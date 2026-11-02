# ==============================================================================
# CONFIGURACIÓN DE BASE DE DATOS POSTGRESQL (SUPABASE) CON SQLALCHEMY ASYNC
# Archivo: backend/app/core/database.py
# ==============================================================================

import uuid
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Importación relativa robusta dentro del paquete app.core
try:
    from .config import settings
except ImportError:
    from app.core.config import settings


# Clase base moderna de SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass


# Engine asíncrono optimizado para PostgreSQL en Supabase
# Se configura para total compatibilidad con el Pooler (PgBouncer/Supavisor):
# - statement_cache_size=0 y prepared_statement_cache_size=0 desactivan caché local
# - prepared_statement_name_func genera identificadores únicos para evitar colisiones
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
    },
)

# Fábrica de sesiones asíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Inyector de dependencia para endpoints de FastAPI.
    Provee una sesión de base de datos asíncrona dentro del ciclo de vida de la petición.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
