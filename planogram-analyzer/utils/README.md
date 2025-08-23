# 📊 Planogram Compliance Analyzer

Sistema de análisis de cumplimiento de planogramas usando AWS Bedrock con modelos de visión AI.

## 🚀 Instalación Rápida

### 1. Clonar el repositorio
```bash
git clone <your-repo>
cd planogram-analyzer
```

### 2. Configurar AWS Credentials

#### Opción A: Archivo .env (Recomendado)
```bash
cp env_example .env
# Editar .env con sus credenciales AWS reales
nano .env
```

**IMPORTANTE**: En el archivo `.env`, reemplace:
- `AWS_ACCESS_KEY_ID`: Su Access Key ID de AWS
- `AWS_SECRET_ACCESS_KEY`: Su Secret Access Key de AWS
- `AWS_DEFAULT_REGION`: La región donde tiene habilitado Bedrock (ej: us-east-1)

#### Opción B: AWS CLI
```bash
aws configure
# Ingrese sus credenciales cuando se le solicite
```

### 3. Verificar permisos en AWS

Asegúrese de que su usuario/rol de AWS tenga los siguientes permisos:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:*::foundation-model/meta.llama*"
            ]
        }
    ]
}
```

### 4. Habilitar modelos en AWS Bedrock

1. Ir a la consola de AWS Bedrock
2. Navegar a "Model access"
3. Solicitar acceso a:
   - Claude 3.7 Sonnet
   - Claude 4 Opus (si está disponible)
   - Llama 3.2 Vision (opcional)

### 5. Ejecutar con Docker (Recomendado)

```bash
# Construir y ejecutar
docker-compose up --build

# O ejecutar en segundo plano
docker-compose up -d
```

La aplicación estará disponible en: http://localhost:8501

### 6. Ejecutar sin Docker (Alternativa)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
streamlit run app.py
```

## 📁 Preparación de Archivos

Para usar la aplicación necesita 4 archivos:

### 1. **Imagen del Planograma** (JPG/PNG)
- Imagen clara del planograma esperado
- Resolución mínima recomendada: 1024x768

### 2. **Imagen del Realograma** (JPG/PNG)
- Foto actual de la góndola/estante
- Buena iluminación y ángulo frontal

### 3. **JSON de Estructura** (JSON)
Archivo con la estructura del planograma:
```json
{
  "diferencias": [
    {
      "nivel": 1,
      "resultado": {
        "productos": [
          {
            "posicion_producto": 1,
            "nombre": "Producto A",
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
```

### 4. **JSON Esperado** (Opcional)
Para validación y comparación de resultados.

## 🔧 Solución de Problemas

### Error: "UnrecognizedClientException"
**Causa**: Credenciales AWS inválidas
**Solución**: 
1. Verificar AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en .env
2. Confirmar que las credenciales son correctas en AWS IAM

### Error: "AccessDeniedException"
**Causa**: Sin permisos para Bedrock
**Solución**: 
1. Agregar política de Bedrock al usuario/rol IAM
2. Verificar que el modelo está habilitado en su región

### Error: "ValidationException"
**Causa**: Modelo no disponible en la región
**Solución**:
1. Cambiar AWS_DEFAULT_REGION a una región con Bedrock
2. Regiones recomendadas: us-east-1, us-west-2, eu-central-1

### Error: "Could not parse JSON response"
**Causa**: El modelo no devolvió JSON válido
**Solución**:
1. Reintentar el análisis
2. Verificar que las imágenes son claras
3. Ajustar el prompt si es necesario

## 📊 Métricas Calculadas

- **Recall**: Productos encontrados / Total productos
- **Precisión**: Productos en posición correcta / Total productos
- **Cumplimiento de Frentes**: Frentes encontrados / Frentes esperados
- **Cumplimiento General**: Score ponderado de todas las métricas

## 🔐 Seguridad

- **NUNCA** commitar el archivo .env con credenciales reales
- Use AWS IAM roles con permisos mínimos necesarios
- Rote las credenciales regularmente
- Use AWS Secrets Manager para producción

## 📝 Uso Básico

1. Acceder a http://localhost:8501
2. Login con usuario: `Prisma`, password: `Binbash2025`
3. Cargar los 4 archivos requeridos
4. Seleccionar modelo (recomendado: Claude 3.7 Sonnet)
5. Click en "Analizar Cumplimiento"
6. Revisar resultados y descargar reportes

## 🐛 Debug

Para habilitar modo debug:
```bash
# En .env
DEBUG=True

# Ver logs de Docker
docker-compose logs -f
```

## 📞 Soporte

Para problemas específicos:
1. Verificar logs: `docker-compose logs`
2. Revisar estado AWS: `aws bedrock list-foundation-models`
3. Validar credenciales: `aws sts get-caller-identity`