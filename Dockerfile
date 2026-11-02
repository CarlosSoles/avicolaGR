# ==============================================================================
# DOCKERFILE - BACKEND FASTAPI (AVÍCOLA GR)
# Compatible con Hugging Face Spaces (Puerto 7860), Cloud Run, Koyeb y Docker local
# ==============================================================================

FROM python:3.10-slim

# Evitar escritura de archivos .pyc y forzar salida inmediata en logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

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

# Crear usuario estándar para compatibilidad con Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user && \
    chown -R user:user /app
USER user

# Exponer el puerto estándar de Hugging Face
EXPOSE 7860

# Comando de arranque dinámico (toma el puerto asignado por el entorno o 7860 por defecto)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]

