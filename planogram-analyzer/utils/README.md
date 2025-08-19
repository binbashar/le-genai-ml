# 🎯 Planogram Compliance Analyzer

Sistema de análisis de cumplimiento de planogramas usando AWS Bedrock y modelos de visión AI.

## 🚀 Quick Start con Docker (Codespaces)

### 1. Clonar o crear el proyecto en Codespaces

```bash
# Si estás en Codespaces, el proyecto ya está listo
cd planogram-analyzer
```

### 2. Configurar variables de entorno

Edita el archivo `.env` con tus credenciales de AWS:

```bash
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_DEFAULT_REGION=us-east-1
```

### 3. Construir y ejecutar con Docker

```bash
# Construir la imagen
docker-compose build

# Ejecutar el contenedor
docker-compose up
```

### 4. Acceder a la aplicación

- En Codespaces: Click en el puerto 8501 cuando aparezca la notificación
- Local: Navegar a http://localhost:8501

## 📋 Credenciales de acceso

- **Usuario:** Prisma
- **Password:** Binbash2025

## 🎨 Características

- ✅ Login seguro con credenciales desde .env
- ✅ Integración con múltiples modelos de AWS Bedrock
- ✅ Análisis de cumplimiento de planogramas
- ✅ Cálculo de métricas (Recall, Precisión)
- ✅ Descarga de resultados en JSON
- ✅ Interfaz moderna y responsiva
- ✅ Prompt personalizable
- ✅ Soporte para múltiples modelos AI

## 🤖 Modelos soportados

1. Llama 3.2 11B Vision Instruct
2. Claude 4.1 Opus
3. Claude Sonnet 4
4. Claude 3.7 Sonnet

## 📊 Métricas calculadas

- Productos encontrados vs esperados
- Productos en posición correcta
- Recall (sensibilidad)
- Precisión
- Productos faltantes

## 🔧 Personalización

### Agregar nuevos modelos

Edita `config.yaml`:

```yaml
models:
  nuevo_modelo:
    name: "Nombre Display"
    model_id: "model-id-en-bedrock"
    max_tokens: 4096
    temperature: 0.1
```

### Modificar el prompt default

Edita la sección `default_prompt` en `config.yaml`

## 📝 Notas importantes

- Asegúrate de tener permisos en AWS Bedrock para los modelos configurados
- Las imágenes se redimensionan automáticamente a max 2048x2048
- El sistema está optimizado para detectar productos faltantes con alto recall

## 🐛 Troubleshooting

Si encuentras errores de conexión con AWS:
1. Verifica tus credenciales en `.env`
2. Confirma que tienes acceso a los modelos en Bedrock
3. Revisa la región configurada

## 📄 Licencia 

Binbash

# ====================
# INSTRUCCIONES DE USO
# ====================

## Para ejecutar en Codespaces:

1. Crea una nueva carpeta llamada `planogram-analyzer`
2. Copia todos los archivos según la estructura indicada
3. Configura tus credenciales AWS en el archivo `.env`
4. Ejecuta:
   ```bash
   docker-compose build
   docker-compose up
   ```
5. Accede a la aplicación en el puerto 8501

## Características implementadas:

✅ Login con usuario/contraseña desde .env
✅ Conexión parametrizable con AWS Bedrock
✅ Soporte para múltiples modelos AI
✅ Carga de planograma y realograma
✅ Prompt personalizable
✅ Análisis de cumplimiento con JSON estructurado
✅ Cálculo de métricas (Recall, Precisión)
✅ Descarga de resultados
✅ Interfaz moderna y profesional
✅ Docker y docker-compose listos para Codespaces

El sistema está optimizado para:
- Máximo recall en detección de productos faltantes
- Mínimos falsos positivos
- Código limpio y eficiente
- Fácil configuración y despliegue


