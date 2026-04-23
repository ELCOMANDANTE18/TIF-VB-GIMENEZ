#!/bin/bash
# =============================================================================
# setup.sh — Entorno de desarrollo: Phishing Detector Instagram DMs
# Uso: bash setup.sh
# =============================================================================

set -e  # Detener el script si cualquier comando falla

# --- Colores para output legible ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # Sin color

print_step()  { echo -e "\n${CYAN}▶ $1${NC}"; }
print_ok()    { echo -e "${GREEN}✔ $1${NC}"; }
print_warn()  { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✘ $1${NC}"; }

echo -e "${CYAN}"
echo "=============================================="
echo "   Phishing Detector — Setup de entorno"
echo "=============================================="
echo -e "${NC}"

# --- 1. Verificar Python 3.10+ ---
print_step "Verificando versión de Python..."

if ! command -v python3 &> /dev/null; then
    print_error "Python3 no encontrado. Instalalo desde https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED="3.10"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)"; then
    print_ok "Python $PYTHON_VERSION detectado"
else
    print_error "Se requiere Python $REQUIRED o superior. Tenés: $PYTHON_VERSION"
    exit 1
fi

# --- 2. Crear entorno virtual si no existe ---
print_step "Configurando entorno virtual (.venv)..."

if [ -d ".venv" ]; then
    print_warn "El entorno virtual ya existe — omitiendo creación"
else
    python3 -m venv .venv
    print_ok "Entorno virtual creado en .venv/"
fi

# --- 3. Activar entorno virtual ---
print_step "Activando entorno virtual..."

source .venv/bin/activate
print_ok "Entorno virtual activo"

# --- 4. Actualizar pip ---
print_step "Actualizando pip..."
pip install --upgrade pip --quiet
print_ok "pip actualizado"

# --- 5. Instalar dependencias ---
print_step "Instalando dependencias desde requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    print_error "No se encontró requirements.txt en el directorio actual"
    print_warn "Asegurate de correr este script desde la raíz del proyecto"
    exit 1
fi

pip install -r requirements.txt --quiet
print_ok "Dependencias instaladas correctamente"

# --- 6. Verificar instalación de paquetes clave ---
print_step "Verificando paquetes clave..."

PACKAGES=("fastapi" "uvicorn" "pydantic" "pydantic_settings" "dotenv" "httpx" "pytest")

for pkg in "${PACKAGES[@]}"; do
    if python3 -c "import $pkg" &> /dev/null; then
        VERSION=$(python3 -c "import $pkg; print(getattr($pkg, '__version__', 'ok'))" 2>/dev/null || echo "ok")
        print_ok "$pkg ($VERSION)"
    else
        print_error "$pkg NO se instaló correctamente"
        exit 1
    fi
done

# --- 7. Crear .env si no existe ---
print_step "Verificando archivo .env..."

if [ -f ".env" ]; then
    print_warn ".env ya existe — no se sobreescribe"
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_ok ".env creado desde .env.example"
        print_warn "IMPORTANTE: Editá .env y completá tus credenciales antes de correr el servidor"
    else
        cat > .env << 'EOF'
# =============================================
# Variables de entorno — Phishing Detector
# NUNCA subas este archivo a git
# =============================================

META_APP_SECRET=tu_instagram_app_secret_aqui
META_VERIFY_TOKEN=phishing_detector_2024
PAGE_ACCESS_TOKEN=tu_page_access_token_aqui

# Umbrales de riesgo (opcionales, estos son los defaults)
RISK_THRESHOLD_HIGH=70
RISK_THRESHOLD_MEDIUM=40
URL_WEIGHT=0.6
TEXT_WEIGHT=0.4
EOF
        print_ok ".env creado con plantilla base"
        print_warn "IMPORTANTE: Editá .env y completá tus credenciales antes de correr el servidor"
    fi
fi

# --- 8. Verificar .gitignore ---
print_step "Verificando .gitignore..."

GITIGNORE_ENTRIES=(".venv/" ".env" "__pycache__/" "*.pyc" ".pytest_cache/")
GITIGNORE_UPDATED=false

for entry in "${GITIGNORE_ENTRIES[@]}"; do
    if [ ! -f ".gitignore" ] || ! grep -qF "$entry" .gitignore; then
        echo "$entry" >> .gitignore
        GITIGNORE_UPDATED=true
    fi
done

if [ "$GITIGNORE_UPDATED" = true ]; then
    print_ok ".gitignore actualizado con entradas necesarias"
else
    print_ok ".gitignore ya está correctamente configurado"
fi

# --- 9. Resumen final ---
echo ""
echo -e "${GREEN}=============================================="
echo "   Setup completado exitosamente"
echo -e "==============================================${NC}"
echo ""
echo -e "Próximos pasos:"
echo -e "  ${CYAN}1.${NC} Activar el entorno:     ${YELLOW}source .venv/bin/activate${NC}"
echo -e "  ${CYAN}2.${NC} Editar credenciales:    ${YELLOW}nano .env${NC}"
echo -e "  ${CYAN}3.${NC} Levantar el servidor:   ${YELLOW}uvicorn app.main:app --reload --port 8000${NC}"
echo -e "  ${CYAN}4.${NC} Exponer con ngrok:      ${YELLOW}ngrok http 8000${NC}"
echo -e "  ${CYAN}5.${NC} Correr los tests:       ${YELLOW}pytest tests/ -v${NC}"
echo ""
