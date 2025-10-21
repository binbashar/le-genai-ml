# 🚀 GUÍA DE INICIO RÁPIDO - Planogram Analyzer

## ⚡ Instalación en 3 Pasos

### Paso 1: Configurar Credenciales AWS

Copie el archivo de ejemplo y configure sus credenciales:

```bash
cp env_example .env
# Edite el archivo .env con sus credenciales reales
```

**IMPORTANTE:** Nunca comparta o versione el archivo `.env` con credenciales reales.

**¿No tiene credenciales AWS?**
1. Vaya a [AWS Console](https://console.aws.amazon.com/)
2. IAM → Users → Su usuario → Security credentials
3. Create access key
4. Configure las credenciales en el archivo `.env`

### Paso 2: Verificar Configuración

```bash
# Ejecutar script de verificación
python3 test_aws_connection.py
```

Debería ver:
- ✅ Credenciales válidas
- ✅ Acceso a Bedrock confirmado

### Paso 3: Ejecutar Aplicación

**Opción A: Con Docker (Recomendado)**
```bash
docker-compose up --build
```

**Opción B: Sin Docker**
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📱 Usar la Aplicación

1. **Abrir navegador**: http://localhost:8501

2. **Login**:
   - Usuario y contraseña configurados en archivo `.env` (APP_USER y APP_PASSWORD)

3. **Cargar 4 archivos**:
   - 📷 Imagen del Planograma (JPG/PNG)
   - 📸 Imagen del Realograma (JPG/PNG)
   - 📄 JSON de Estructura del planograma
   - 📝 JSON Esperado (opcional)

4. **Analizar**:
   - Seleccionar modelo: `Anthropic Sonnet 3.7 (Recomendado)`
   - Click en `🚀 Analizar Cumplimiento`

5. **Resultados**:
   - Ver métricas de cumplimiento
   - Descargar reporte JSON

## 🔧 Solución Rápida de Problemas

### Error: "UnrecognizedClientException"
```bash
# Verificar que .env está configurado
ls -la .env

# Probar credenciales (requiere AWS CLI configurado)
aws sts get-caller-identity
```

### Error: "AccessDeniedException"
```bash
# Necesita permisos de Bedrock en IAM
# Agregar política: AmazonBedrockFullAccess
```

### Error: "Model not found"
```bash
# Cambiar región en .env a una con Bedrock
AWS_DEFAULT_REGION=us-west-2  # o us-east-1
```

## 📊 Estructura del JSON de Entrada

```json
{
  "diferencias": [
    {
      "nivel": 1,
      "resultado": {
        "productos": [
          {
            "posicion_producto": 1,
            "nombre": "Producto A 500ml",
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

## 🎯 Métricas Calculadas

- **Recall**: % de productos encontrados
- **Precisión**: % en posición correcta
- **Cumplimiento Frentes**: % de frentes correctos
- **Score General**: Promedio ponderado

## 📞 Comandos Útiles

```bash
# Ver logs
docker-compose logs -f

# Detener aplicación
docker-compose down

# Limpiar y reconstruir
docker-compose down
docker-compose build --no-cache
docker-compose up

# Verificar estado
docker ps
```

## ✅ Checklist Pre-Análisis

- [ ] Archivo `.env` creado desde `env_example`
- [ ] AWS credentials y APP_USER/APP_PASSWORD configurados en `.env`
- [ ] Modelos Anthropic habilitados en AWS Bedrock
- [ ] Imagen planograma clara y frontal
- [ ] Imagen realograma buena iluminación
- [ ] JSON estructura con todos los productos
- [ ] Aplicación ejecutándose en http://localhost:8501

## 🆘 ¿Necesita Ayuda?

1. Ejecute el test: `python3 test_aws_connection.py`
2. Revise logs: `docker-compose logs`
3. Verifique AWS: `aws bedrock list-foundation-models`
4. Consulte README.md para más detalles

---
**Inicio Rápido Automático:**
```bash
chmod +x setup.sh
./setup.sh
```