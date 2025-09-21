#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ASCII Art Banner
print_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
    ____  __                                              
   / __ \/ /___ _____  ____  ____ __________ _____ ___  
  / /_/ / / __ `/ __ \/ __ \/ __ `/ ___/ __ `/ __ `__ \ 
 / ____/ / /_/ / / / / /_/ / /_/ / /  / /_/ / / / / / / 
/_/   /_/\__,_/_/ /_/\____/\__, /_/   \__,_/_/ /_/ /_/  
                          /____/                         
    ___                __                     
   /   |  ____  ____ _/ /_  ______  ___  _____
  / /| | / __ \/ __ `/ / / / /_  / / _ \/ ___/
 / ___ |/ / / / /_/ / / /_/ / / /_/  __/ /    
/_/  |_/_/ /_/\__,_/_/\__, / /___/\___/_/     
                     /____/                    
EOF
    echo -e "${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Planogram Compliance Analyzer Setup${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print step
print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Check system requirements
check_requirements() {
    print_step "Verificando requisitos del sistema..."
    
    local missing_requirements=0
    
    # Check Python
    if command_exists python3; then
        python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
        print_success "Python $python_version detectado"
    else
        print_error "Python 3 no está instalado"
        missing_requirements=1
    fi
    
    # Check pip
    if command_exists pip3; then
        print_success "pip3 detectado"
    else
        print_error "pip3 no está instalado"
        missing_requirements=1
    fi
    
    # Check Docker
    if command_exists docker; then
        docker_version=$(docker --version | grep -Po '\d+\.\d+\.\d+')
        print_success "Docker $docker_version detectado"
    else
        print_warning "Docker no está instalado (opcional para deployment)"
    fi
    
    # Check Docker Compose
    if command_exists docker-compose; then
        compose_version=$(docker-compose --version | grep -Po '\d+\.\d+\.\d+')
        print_success "Docker Compose $compose_version detectado"
    else
        print_warning "Docker Compose no está instalado (opcional para deployment)"
    fi
    
    # Check Git
    if command_exists git; then
        print_success "Git detectado"
    else
        print_warning "Git no está instalado"
    fi
    
    return $missing_requirements
}

# Create directories
create_directories() {
    print_step "Creando directorios necesarios..."
    
    directories=("utils" "data" "logs" "cache" ".streamlit" "backups")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Directorio $dir creado"
        else
            print_info "Directorio $dir ya existe"
        fi
    done
}

# Setup environment file
setup_environment() {
    print_step "Configurando archivo de entorno..."
    
    if [ ! -f ".env" ]; then
        print_info "Creando archivo .env desde plantilla..."
        
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
PORT=8501

# Model Configuration
DEFAULT_MODEL=claude_3_sonnet
MAX_RETRIES=3
REQUEST_TIMEOUT=120

# Optional: Database Configuration (if using PostgreSQL)
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=planogram
# DB_USER=planogram_user
# DB_PASSWORD=changeme

# Optional: Redis Configuration (if using Redis)
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_DB=0
EOL
        
        print_success "Archivo .env creado"
        print_warning "IMPORTANTE: Configure sus credenciales AWS en el archivo .env"
        echo ""
        
        # Ask user if they want to configure AWS credentials now
        read -p "¿Desea configurar las credenciales AWS ahora? (s/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            configure_aws_credentials
        fi
    else
        print_success "Archivo .env encontrado"
        
        # Check if AWS credentials are configured
        if grep -q "your_actual_access_key_here" .env; then
            print_warning "Las credenciales AWS aún no están configuradas"
            read -p "¿Desea configurar las credenciales AWS ahora? (s/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Ss]$ ]]; then
                configure_aws_credentials
            fi
        else
            print_success "Credenciales AWS parecen estar configuradas"
        fi
    fi
}

# Configure AWS credentials
configure_aws_credentials() {
    echo ""
    print_step "Configurando credenciales AWS..."
    
    read -p "Ingrese su AWS_ACCESS_KEY_ID: " aws_key
    read -p "Ingrese su AWS_SECRET_ACCESS_KEY: " aws_secret
    read -p "Ingrese su AWS_DEFAULT_REGION (default: us-east-1): " aws_region
    
    # Set default region if empty
    if [ -z "$aws_region" ]; then
        aws_region="us-east-1"
    fi
    
    # Update .env file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$aws_key/" .env
        sed -i '' "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$aws_secret/" .env
        sed -i '' "s/AWS_DEFAULT_REGION=.*/AWS_DEFAULT_REGION=$aws_region/" .env
    else
        # Linux
        sed -i "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$aws_key/" .env
        sed -i "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$aws_secret/" .env
        sed -i "s/AWS_DEFAULT_REGION=.*/AWS_DEFAULT_REGION=$aws_region/" .env
    fi
    
    print_success "Credenciales AWS configuradas"
}

# Install Python dependencies
install_dependencies() {
    print_step "Instalando dependencias de Python..."
    
    if [ -f "requirements.txt" ]; then
        pip3 install --upgrade pip
        pip3 install -r requirements.txt
        
        if [ $? -eq 0 ]; then
            print_success "Dependencias instaladas correctamente"
        else
            print_error "Error al instalar dependencias"
            return 1
        fi
    else
        print_error "Archivo requirements.txt no encontrado"
        return 1
    fi
}

# Test AWS connection
test_aws_connection() {
    print_step "Verificando conexión con AWS..."
    
    if [ -f "test_aws_connection.py" ]; then
        python3 test_aws_connection.py
        
        if [ $? -eq 0 ]; then
            print_success "Conexión AWS verificada"
        else
            print_warning "No se pudo verificar la conexión AWS completamente"
            print_info "Puede verificar manualmente con: python3 test_aws_connection.py"
        fi
    else
        print_warning "Script de prueba no encontrado"
    fi
}

# Setup Streamlit config
setup_streamlit_config() {
    print_step "Configurando Streamlit..."
    
    if [ ! -f ".streamlit/config.toml" ]; then
        mkdir -p .streamlit
        cat > .streamlit/config.toml << 'EOL'
[theme]
primaryColor = "#4CAF50"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
port = 8501
address = "0.0.0.0"
headless = true
runOnSave = true
maxUploadSize = 200

[browser]
gatherUsageStats = false
serverAddress = "localhost"
EOL
        print_success "Configuración de Streamlit creada"
    else
        print_info "Configuración de Streamlit ya existe"
    fi
}

# Create sample data files
create_sample_data() {
    print_step "Creando archivos de ejemplo..."
    
    # Create sample JSON structure
    if [ ! -f "data/sample_structure.json" ]; then
        cat > data/sample_structure.json << 'EOL'
{
  "diferencias": [
    {
      "nivel": 1,
      "resultado": {
        "productos": [
          {
            "posicion_producto": 1,
            "nombre": "Producto Ejemplo 500ml",
            "encontrado": null,
            "posicion_correcta": null,
            "frentes_esperados": 6,
            "frentes_encontrados": null
          }
        ]
      }
    }
  ],
  "conclusiones": []
}
EOL
        print_success "Archivo de ejemplo creado en data/sample_structure.json"
    fi
}

# Docker setup
setup_docker() {
    if command_exists docker && command_exists docker-compose; then
        print_step "Configurando Docker..."
        
        read -p "¿Desea construir la imagen Docker ahora? (s/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            print_info "Construyendo imagen Docker..."
            docker-compose build
            
            if [ $? -eq 0 ]; then
                print_success "Imagen Docker construida correctamente"
                
                read -p "¿Desea iniciar la aplicación con Docker? (s/n): " -n 1 -r
                echo ""
                if [[ $REPLY =~ ^[Ss]$ ]]; then
                    docker-compose up -d
                    
                    if [ $? -eq 0 ]; then
                        print_success "Aplicación iniciada con Docker"
                        print_info "Acceda a la aplicación en: http://localhost:8501"
                    else
                        print_error "Error al iniciar la aplicación con Docker"
                    fi
                fi
            else
                print_error "Error al construir imagen Docker"
            fi
        fi
    fi
}

# Main setup function
main() {
    clear
    print_banner
    
    # Check requirements
    check_requirements
    if [ $? -ne 0 ]; then
        print_error "Faltan requisitos del sistema. Por favor instálelos antes de continuar."
        exit 1
    fi
    
    # Create directories
    create_directories
    
    # Setup environment
    setup_environment
    
    # Install dependencies
    install_dependencies
    if [ $? -ne 0 ]; then
        print_error "Error al instalar dependencias"
        exit 1
    fi
    
    # Setup Streamlit config
    setup_streamlit_config
    
    # Create sample data
    create_sample_data
    
    # Test AWS connection
    test_aws_connection
    
    # Docker setup (optional)
    setup_docker
    
    # Final message
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  🎉 ¡Instalación Completa!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${CYAN}Próximos pasos:${NC}"
    echo ""
    
    if grep -q "your_actual_access_key_here" .env 2>/dev/null; then
        echo -e "1. ${YELLOW}Configure sus credenciales AWS en .env${NC}"
        echo -e "2. ${YELLOW}Ejecute: python3 test_aws_connection.py${NC}"
        echo -e "3. ${YELLOW}Inicie la aplicación con:${NC}"
    else
        echo -e "1. ${GREEN}Inicie la aplicación con:${NC}"
    fi
    
    echo -e "   ${MAGENTA}streamlit run app.py${NC}"
    echo -e "   ${CYAN}o${NC}"
    echo -e "   ${MAGENTA}docker-compose up${NC}"
    echo -e "   ${CYAN}o${NC}"
    echo -e "   ${MAGENTA}make run${NC}"
    echo ""
    echo -e "2. ${GREEN}Acceda a:${NC} ${YELLOW}http://localhost:8501${NC}"
    echo ""
    echo -e "3. ${GREEN}Credenciales de acceso:${NC}"
    echo -e "   Usuario: ${YELLOW}Prisma${NC}"
    echo -e "   Contraseña: ${YELLOW}Binbash2025${NC}"
    echo ""
    echo -e "${CYAN}Para más ayuda, ejecute:${NC} ${MAGENTA}make help${NC}"
    echo ""
}

# Run main function
main