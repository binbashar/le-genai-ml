# 🏗️ Infraestructura Terraform - client Planogram Analyzer

Este directorio contiene toda la configuración de infraestructura como código (IaC) para el proyecto client Planogram Analyzer, desplegado en AWS.

## 📋 Descripción General

La infraestructura está diseñada para soportar una aplicación Streamlit que utiliza Amazon Bedrock para análisis de imágenes de planogramas. El sistema está completamente containerizado y desplegado en AWS ECS Fargate con un Application Load Balancer para acceso público.

## 🏛️ Arquitectura

```
Internet → ALB → ECS Fargate → Streamlit App
                ↓
            ECR Repository
                ↓
            AWS Secrets Manager
                ↓
            Amazon Bedrock
```

## 📁 Estructura de Archivos

| Archivo | Descripción |
|---------|-------------|
| `alb.tf` | Configuración del Application Load Balancer |
| `config.tf` | Configuración del proveedor AWS y fuentes de datos |
| `ecr.tf` | Repositorio ECR para imágenes Docker |
| `ecs.tf` | Cluster y servicio ECS Fargate |
| `locals.tf` | Variables locales y definiciones de contenedores |
| `oidc.tf` | Configuración OIDC para GitHub Actions |
| `s3_tfstate.tf` | Backend S3 para almacenamiento del estado |
| `secrets.tf` | Integración con AWS Secrets Manager |
| `terraform.tfvars` | Valores de variables del entorno |
| `variables.tf` | Definiciones de variables de entrada |

## 🚀 Servicios AWS Utilizados

### Computación
- **Amazon ECS Fargate**: Ejecución serverless de contenedores
- **Application Load Balancer**: Distribución de tráfico y balanceo de carga

### Almacenamiento y Registro
- **Amazon ECR**: Registro de imágenes Docker
- **Amazon S3**: Almacenamiento del estado de Terraform

### Seguridad y Gestión
- **AWS Secrets Manager**: Gestión de secretos de la aplicación
- **AWS IAM**: Roles y políticas de acceso
- **OIDC**: Autenticación segura para GitHub Actions

### IA/ML
- **Amazon Bedrock**: Servicios de IA generativa para análisis de imágenes

## ⚙️ Configuración

### Variables Requeridas

```hcl
# terraform.tfvars
project_long = "client"
project = "client"
environment = "planogram-analyzer"

oidc_provider = {
  url       = "https://token.actions.githubusercontent.com"
  audiences = ["sts.amazonaws.com"]
  owner     = "karacas"
  repos     = ["clientVisionBinBash"]
}
```

## 🛠️ Despliegue

### Prerrequisitos

1. **AWS CLI** configurado con credenciales apropiadas
2. **Terraform** >= 1.2
3. **Docker** para construcción de imágenes
4. **Git** para control de versiones

### Variables de Entorno Requeridas

**⚠️ IMPORTANTE**: Antes de ejecutar Terraform, debe configurar las siguientes variables de entorno:

```bash
# Credenciales AWS (para el despliegue inicial)
export AWS_ACCESS_KEY_ID="tu_access_key_id"
export AWS_SECRET_ACCESS_KEY="tu_secret_access_key"
export AWS_DEFAULT_REGION="us-west-2"

# Opcional: Si usa MFA o roles temporales
export AWS_SESSION_TOKEN="tu_session_token"
```

**Alternativas de autenticación**:
- **Archivo de credenciales**: `~/.aws/credentials`
- **Perfil AWS**: `aws configure --profile nombre-perfil`
- **Roles IAM**: Si ejecuta desde EC2/ECS con rol asignado

**Verificar credenciales**:
```bash
aws sts get-caller-identity
```

### Pasos de Despliegue

1. **Inicializar Terraform**:
   ```bash
   cd terraform
   terraform init
   ```

2. **Revisar el plan**:
   ```bash
   terraform plan
   ```

3. **Aplicar la infraestructura**:
   ```bash
   terraform apply
   ```

4. **Configurar secretos**:
   - Acceder a AWS Secrets Manager
   - Crear/actualizar el secreto `/client-planogram-analyzer`
   - Agregar la clave `PWD_client` con la contraseña deseada

### Despliegue Automático

El despliegue automático se realiza a través de GitHub Actions cuando se hace push a las ramas `main` o `iac`. El workflow:

1. Construye la imagen Docker
2. La sube a ECR
3. Actualiza el servicio ECS
4. Espera a que el servicio se estabilice

## 🔧 Configuración de la Aplicación

### Variables de Entorno

La aplicación utiliza las siguientes variables de entorno:

- `AWS_DEFAULT_REGION`: Región AWS (us-west-2)
- `APP_USER`: Usuario de la aplicación (client)
- `APP_PASSWORD`: Contraseña obtenida de Secrets Manager

### Puertos

- **ALB**: Puerto 80 (HTTP)
- **Contenedor**: Puerto 8501 (Streamlit)

## 🔒 Seguridad

### Acceso Público
- El ALB está configurado para acceso público desde internet
- Los contenedores ECS solo son accesibles a través del ALB

### Autenticación
- La aplicación utiliza autenticación por contraseña
- Las credenciales AWS se manejan a través de roles IAM de ECS

### Secretos
- Todas las credenciales sensibles se almacenan en AWS Secrets Manager
- No hay credenciales hardcodeadas en el código

## 📊 Monitoreo

### Health Checks
- El ALB realiza health checks en la ruta `/`
- Timeout configurado en 5 segundos
- Intervalo de verificación cada 10 segundos

### Logs
- Los logs de la aplicación se pueden ver en CloudWatch Logs
- El servicio ECS está configurado para logging básico

---

**Región AWS**: us-west-2
