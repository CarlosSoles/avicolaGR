# ==============================================================================
# CLIENTE SUPABASE PARA OPERACIONES DE SERVICIO Y STORAGE
# Archivo: backend/app/core/supabase.py
# ==============================================================================

from supabase import create_client, Client
try:
    from .config import settings
except ImportError:
    from app.core.config import settings

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Retorna la instancia singleton del cliente Supabase con privilegios administrativos
    (service role) para operaciones de Storage y gestión de usuarios.
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    return _supabase_client

