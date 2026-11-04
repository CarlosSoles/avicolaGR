# ==============================================================================
# CONFIGURACIÓN DEL SISTEMA - BACKEND FASTAPI
# Archivo: backend/app/core/config.py
# ==============================================================================

import os
from pathlib import Path
from typing import List, Union, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, computed_field

# Ruta absoluta al archivo .env dentro de backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    # Metadatos del Proyecto
    PROJECT_NAME: str = "Sistema de Planificación de Saca de Aves - Avícola GR"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    # Permite autenticación de desarrollo (dev-token-* y peticiones sin token).
    # Debe quedar en False en producción: con True cualquiera puede suplantar roles.
    ALLOW_DEV_AUTH: bool = False
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://*.pages.dev",
        "*",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Supabase BaaS (Soporta formato tradicional y nuevo formato de Supabase)
    SUPABASE_URL: str = Field(default="https://kpssroraigncmpkwxiyb.supabase.co")
    
    # Llave pública / Anon
    SUPABASE_ANON_KEY: str = Field(default="")
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None

    # Llave secreta / Service Role
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="")
    SUPABASE_SECRET_KEY: Optional[str] = None

    # JWT y JWKS
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_JWKS_URL: Optional[str] = None

    @computed_field
    @property
    def anon_key(self) -> str:
        return self.SUPABASE_PUBLISHABLE_KEY or self.SUPABASE_ANON_KEY or ""

    @computed_field
    @property
    def secret_key(self) -> str:
        return self.SUPABASE_SECRET_KEY or self.SUPABASE_SERVICE_ROLE_KEY or ""

    # Base de Datos PostgreSQL en Supabase
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@db.kpssroraigncmpkwxiyb.supabase.co:5432/postgres?ssl=require"
    )

    @field_validator("DATABASE_URL", mode="before")
    def normalize_database_url(cls, v: str) -> str:
        if not v:
            return v
        # Si viene con prefijo postgresql:// tradicional, cambiar a postgresql+asyncpg://
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        
        # Eliminar pgbouncer=true ya que asyncpg no lo reconoce como parámetro de conexión
        if "?pgbouncer=true" in v:
            v = v.replace("?pgbouncer=true", "")
        elif "&pgbouncer=true" in v:
            v = v.replace("&pgbouncer=true", "")
            
        return v

    DATABASE_POOL_URL: Optional[str] = None

    # Motor de Asistencia IA (Google Gemini)
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Configuración de carga desde archivo .env usando la ruta absoluta segura
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
