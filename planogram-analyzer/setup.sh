#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Planogram Analyzer - Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker no está instalado${NC}"
    echo "Por favor instale Docker desde: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose no está instalado${NC}"
    echo "Por favor instale Docker Compose desde: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker y Docker Compose detectados${NC}"
echo ""

# Create utils directory if it doesn't exist
if [ ! -d "utils" ]; then
    echo -e "${YELLOW}📁 Creando directorio utils...${NC}"
    mkdir -p utils
fi

# Create data directory for results
if [ ! -d "data" ]; then
    echo -e "${YELLOW}📁 Creando directorio data...${NC}"
    mkdir -p data
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Creando archivo .env desde plantilla...${NC}"
    
    # Create .env file
    cat > .env << 'EOL'
# Authentication
APP_USER=Prisma
APP_PASSWORD=Binbash2025

# AWS Configuration - IMPORTANTE: Reemplazar con sus credenciales reales
AWS_ACCESS_KEY_ID=your_actual_access_key_here
AWS_SECRET_ACCESS_KEY=your_actual_secret_key_here
AWS_DEFAULT_REGION=us-east-1

# Optional: If using temporary credentials (STS)
# AWS_SESSION_TOKEN=your_session_token_here

# App Configuration
APP_NAME=Planogram Compliance Analyzer
DEBUG=False

# Model Configuration
DEFAULT_MODEL=claude_3_sonnet
MAX_RETRIES=3
REQUEST_TIMEOUT=120
EOL
    
    echo -e "${RED}⚠️  IMPORTANTE: Configure sus credenciales AWS en el archivo .env${NC}"
    echo ""
    
    # Ask user if they want to configure AWS credentials now
    read -p "¿Desea configurar las credenciales AWS ahora? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        read -p "Ingrese su AWS_ACCESS_KEY_ID: " aws_key
        read -p "Ingrese su AWS_SECRET_ACCESS_KEY: " aws_secret
        read -p "Ingrese su AWS_DEFAULT_REGION (default: us-east-1): " aws_region
        
        # Set default region if empty
        if [ -z "$aws_region" ]; then
            aws_region="us-east-1"
        fi
        
        # Update .env file
        sed -i.bak "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$aws_key/" .env
        sed -i.bak "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$aws_secret/" .env
        sed -i.bak "s/AWS_DEFAULT_REGION=.*/AWS_DEFAULT_REGION=$aws_region/" .env
        
        # Remove backup file
        rm -f .env.bak
        
        echo -e "${GREEN}✅ Credenciales AWS configuradas${NC}"
    fi
else
    echo -e "${GREEN}✅ Archivo .env encontrado${NC}"
fi

echo ""

# Test AWS connection
echo -e "${YELLOW}🔍 Verificando conexión con AWS...${NC}"
python3 test_aws_connection.py 2>/dev/null || {
    echo -e "${YELLOW}⚠️  No se pudo verificar la conexión AWS${NC}"
    echo "   Puede verificar manualmente con: python3 test_aws_connection.py"
}

echo ""

# Ask if user wants to build and run with Docker
read -p "¿Desea construir y ejecutar la aplicación con Docker? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}🐳 Construyendo imagen Docker...${NC}"
    docker-compose build
    
    echo ""
    echo -e "${GREEN}🚀 Iniciando aplicación...${NC}"
    docker-compose up -d
    
    # Wait for app to start
    echo -e "${YELLOW}⏳ Esperando que la aplicación inicie...${NC}"
    sleep 5
    
    # Check if container is running
    if [ "$(docker ps -q -f name=planogram-analyzer)" ]; then
        echo -e "${GREEN}✅ Aplicación ejecutándose correctamente${NC}"
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  🎉 ¡Instalación Completa!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "📊 Acceda a la aplicación en: ${GREEN}http://localhost:8501${NC}"
        echo -e "👤 Usuario: ${GREEN}Prisma${NC}"
        echo -e "🔑 Contraseña: ${GREEN}Binbash2025${NC}"
        echo ""
        echo -e "📝 Para ver logs: ${YELLOW}docker-compose logs -f${NC}"
        echo -e "🛑 Para detener: ${YELLOW}docker-compose down${NC}"
    else
        echo -e "${RED}❌ Error al iniciar el contenedor${NC}"
        echo "Revise los logs con: docker-compose logs"
    fi
else
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Setup completado${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Para ejecutar la aplicación manualmente:"
    echo ""
    echo "  Con Docker:"
    echo -e "    ${YELLOW}docker-compose up --build${NC}"
    echo ""
    echo "  Sin Docker:"
    echo -e "    ${YELLOW}pip install -r requirements.txt${NC}"
    echo -e "    ${YELLOW}streamlit run app.py${NC}"
fi

echo ""