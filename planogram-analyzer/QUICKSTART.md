# 🚀 GUÍA DE INICIO RÁPIDO - Planogram Analyzer

## ⚡ Instalación en 3 Pasos

### Paso 1: Configurar Credenciales AWS

Edite el archivo `.env` y reemplace con sus credenciales reales:

```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE     # ← Su Access Key real
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI...      # ← Su Secret Key real
AWS_DEFAULT_REGION=us-east-1                # ← Su región preferida
```

**¿No tiene credenciales AWS?**
1. Vaya a [AWS Console](https://console.aws.amazon.com/)
2. IAM → Users → Su usuario → Security credentials
3. Create access key

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
   - Usuario: `Prisma`
   - Password: `Binbash2025`

3. **Cargar 4 archivos**:
   - 📷 Imagen del Planograma (JPG/PNG)
   - 📸 Imagen del Realograma (JPG/PNG)
   - 📄 JSON de Estructura del planograma
   - 📝 JSON Esperado (opcional)

4. **Analizar**:
   - Seleccionar modelo: `Claude 3 Sonnet (Recomendado)`
   - Click en `🚀 Analizar Cumplimiento`

5. **Resultados**:
   - Ver métricas de cumplimiento
   - Descargar reporte JSON

## 🔧 Solución Rápida de Problemas

### Error: "UnrecognizedClientException"
```bash
# Verificar credenciales en .env
cat .env | grep AWS_

# Probar credenciales
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

- [ ] AWS credentials configuradas en .env
- [ ] Modelo Claude habilitado en Bedrock
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