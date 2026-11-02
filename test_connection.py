# ==============================================================================
# SCRIPT DE COMPROBACIÓN DE CONEXIÓN A SUPABASE
# Archivo: backend/test_connection.py
# ==============================================================================

import asyncio
import sys

# En Windows, usar SelectorEventLoop para cerrar sockets SSL limpiamente
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine


async def test_supabase_connection():
    print("=" * 60)
    print("COMPROBACIÓN DE CONEXIÓN A SUPABASE (POSTGRESQL)")
    print("=" * 60)
    print(f"URL de Supabase: {settings.SUPABASE_URL}")
    print(f"Host BD:         {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'No configurada'}")
    print("-" * 60)

    try:
        print("Intentando conectar con Supabase...")
        async with engine.connect() as conn:
            # 1. Prueba de versión de PostgreSQL
            result = await conn.execute(text("SELECT version();"))
            db_version = result.scalar()
            print("\n [OK] ¡Conexión exitosa a Supabase!")
            print(f" Version PostgreSQL: {db_version.split(',')[0]}\n")

            # 2. Listar tablas del esquema public
            tables_result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            tables = [row[0] for row in tables_result.fetchall()]

            print(f" Tablas encontradas en tu base de datos ({len(tables)}):")
            for t in tables:
                print(f"   - {t}")

            # 3. Comprobar registros de granjas (seed.sql)
            if "farms" in tables:
                farms_result = await conn.execute(text("SELECT count(*) FROM public.farms;"))
                farms_count = farms_result.scalar()
                print(f"\n Granjas registradas (seed.sql): {farms_count}")

            # 4. Comprobar vista de la Tabla General de Saldo
            views_result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.views 
                WHERE table_schema = 'public';
            """))
            views = [row[0] for row in views_result.fetchall()]
            if "v_tabla_general_saldo" in views:
                print(" [OK] Vista 'v_tabla_general_saldo' verificada y lista.")

        print("\n" + "=" * 60)
        print("¡TODO FUNCIONA CORRECTAMENTE! El backend ya está conectado a Supabase.")
        print("=" * 60)

    except Exception as e:
        print("\n❌ [ERROR] No se pudo conectar a Supabase:")
        print(f"Detalle del error: {str(e)}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_supabase_connection())
