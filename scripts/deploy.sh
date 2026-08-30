#!/usr/bin/env bash
# deploy.sh - Script de despliegue robusto e inmutable para VPS

set -euo pipefail

PROJECT_DIR="/var/www/datamaq-hub"
SERVICE_NAME="datamaq-hub.service"
HEALTH_URL="http://127.0.0.1:8013/api/v1/health"
OPENAPI_URL="http://127.0.0.1:8013/openapi.json"

echo "🚀 Iniciando despliegue en: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 1. Sanitizar el working tree local de la VPS
echo "🧹 Limpiando modificaciones locales conflictivas..."
git restore data/paritarias/*.json || true
git clean -df -e .venv/ -e data/

# 2. Descargar los cambios más recientes
echo "📥 Realizando pull desde origin/main..."
git pull origin main

# 3. Validar / Actualizar dependencias de Python
echo "📦 Verificando dependencias..."
if [ -f "requirements.txt" ]; then
    .venv/bin/pip install -r requirements.txt --quiet
fi

# 4. Reiniciar el servicio FastAPI / Gunicorn
echo "🔄 Reiniciando servicio systemd..."
sudo systemctl restart "$SERVICE_NAME"

# 5. Smoke Tests: Verificación post-deploy activa
echo "🔍 Ejecutando Smoke Tests..."
sleep 3 # Esperar inicialización de workers

# Validar /health
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "500")
if [ "$HEALTH_STATUS" -ne 200 ]; then
    echo "❌ ERROR: El endpoint de salud retornó HTTP $HEALTH_STATUS"
    exit 1
fi

# Validar que los endpoints clave existan en el openapi.json
echo "🧬 Validando endpoints en OpenAPI..."
if ! curl -s "$OPENAPI_URL" | grep -q "tarjetas/cargar"; then
    echo "❌ ERROR: La ruta tarjetas/cargar no se encuentra registrada en OpenAPI"
    exit 1
fi

echo "✅ DESPLIEGUE EXITOSO Y CERTIFICADO!"
