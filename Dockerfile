# ==============================================================================
# DOCKERFILE - BACKEND FASTAPI (AVÍCOLA GR)
# Imagen para Render (Web Service con Docker) y ejecución local.
# Render inyecta la variable PORT; el contenedor la respeta automáticamente.
# ==============================================================================

FROM python:3.10-slim

# Evitar escritura de archivos .pyc y forzar salida inmediata en logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Instalar dependencias mínimas de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Usuario sin privilegios
RUN useradd -m -u 1000 user && \
    chown -R user:user /app
USER user

# Puerto por defecto (Render lo sobrescribe con su propia variable PORT)
EXPOSE 8000

# Arranque dinámico: usa el puerto asignado por la plataforma o 8000 en local
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
