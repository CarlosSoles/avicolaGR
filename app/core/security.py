# ==============================================================================
# SEGURIDAD, HASHING Y AUTENTICACIÓN EN FASTAPI
# Archivo: backend/app/core/security.py
# ==============================================================================

from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import hashlib
import os
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

try:
    from .config import settings
except ImportError:
    from app.core.config import settings

# auto_error=False evita que FastAPI rechace con 403 antes de que nuestra lógica evalúe el token
security = HTTPBearer(auto_error=False)

# Cliente de claves públicas JWKS de Supabase (con caché interna)
_jwks_client: Optional[PyJWKClient] = None

JWT_SECRET_KEY = settings.SUPABASE_JWT_SECRET or "avicola-gr-secret-key-2026-saca-stock-secure"
JWT_ALGORITHM = "HS256"


def get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = settings.SUPABASE_JWKS_URL or f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            _jwks_client = PyJWKClient(jwks_url)
        except Exception:
            _jwks_client = None
    return _jwks_client


# ------------------------------------------------------------------------------
# Hashing y Verificación de Contraseñas (PBKDF2-HMAC-SHA256 con Salt aleatorio)
# ------------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Genera un hash seguro con salt de 16 bytes usando PBKDF2."""
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash guardado."""
    if not hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 2:
            return False
        salt, key_hex = parts
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return key.hex() == key_hex
    except Exception:
        return False


# ------------------------------------------------------------------------------
# Generación de Tokens JWT
# ------------------------------------------------------------------------------
def create_access_token(
    user_id: UUID,
    email: str,
    role: str,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Genera un JWT firmado con los metadatos del usuario."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)

    payload = {
        "sub": str(user_id),
        "email": email,
        "username": username or email.split("@")[0],
        "full_name": full_name,
        "role": role,
        "app_metadata": {"role": role, "provider": "system"},
        "user_metadata": {"role": role, "username": username or email.split("@")[0], "full_name": full_name},
        "aud": "authenticated",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


class AuthenticatedUser(BaseModel):
    id: UUID
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    scopes: List[str] = []


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthenticatedUser:
    """
    Decodifica y valida el token JWT emitido por el sistema o por Supabase Auth (GoTrue).
    Soporta verificación asimétrica por JWKS, tokens JWT HS256 locales, dev-token y fallback DEBUG.
    """
    # 0. Si no hay credenciales enviadas
    if not credentials:
        if settings.ALLOW_DEV_AUTH:
            return AuthenticatedUser(
                id=UUID("11111111-2222-3333-4444-555555555555"),
                email="admin@avicolagr.com",
                username="admin",
                full_name="Administrador de Desarrollo",
                role="admin_sistema",
                scopes=["all"],
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecera Authorization: Bearer <token> requerida.",
        )

    token = credentials.credentials

    # 1. Soporte de tokens para desarrollo y pruebas rápidas (solo si está habilitado)
    if token.startswith("dev-token-") and settings.ALLOW_DEV_AUTH:
        role_from_token = token.replace("dev-token-", "").strip() or "supervisor_pecuario"
        return AuthenticatedUser(
            id=UUID("11111111-2222-3333-4444-555555555555"),
            email=f"{role_from_token}@avicolagr.com",
            username=role_from_token,
            full_name=None,
            role=role_from_token,
            scopes=["all"],
        )

    payload = None
    last_error = None

    # 2. Intento por Secreto Local HS256
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except Exception as e:
        last_error = e

    # 3. Intento por JWKS de Supabase (RS256/ES256)
    if payload is None:
        jwks = get_jwks_client()
        if jwks:
            try:
                signing_key = jwks.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256", "ES256"],
                    audience="authenticated",
                    options={"verify_aud": True},
                )
            except Exception as e:
                last_error = e

    # 4. Intento por SUPABASE_JWT_SECRET si está definido
    if payload is None and settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
        except Exception as e:
            last_error = e

    # 5. Fallback de desarrollo (NUNCA en producción: confiaría en tokens sin firma)
    if payload is None and settings.ALLOW_DEV_AUTH:
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
        except Exception:
            pass

    if payload is None:
        if settings.ALLOW_DEV_AUTH:
            return AuthenticatedUser(
                id=UUID("11111111-2222-3333-4444-555555555555"),
                email="admin@avicolagr.com",
                username="admin",
                full_name="Administrador de Desarrollo",
                role="admin_sistema",
                scopes=["all"],
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token de autenticación inválido o expirado. {str(last_error) if last_error else ''}",
        )

    user_id_str = payload.get("sub") or "11111111-2222-3333-4444-555555555555"
    user_metadata = payload.get("user_metadata", {})
    app_metadata = payload.get("app_metadata", {})

    role = payload.get("role") or app_metadata.get("role") or user_metadata.get("role") or "supervisor_pecuario"
    email = payload.get("email")
    username = payload.get("username") or user_metadata.get("username") or (email.split("@")[0] if email else "usuario")

    return AuthenticatedUser(
        id=UUID(user_id_str),
        email=email,
        username=username,
        full_name=payload.get("full_name") or user_metadata.get("full_name"),
        role=role,
        scopes=user_metadata.get("scopes", []),
    )


def require_role(allowed_roles: List[str]):
    """
    Fábrica de dependencias para Control de Acceso Basado en Roles (RBAC).
    """
    def role_checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los siguientes roles: {', '.join(allowed_roles)} (Rol actual: {current_user.role})",
            )
        return current_user
    return role_checker
