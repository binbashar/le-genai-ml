import streamlit as st
import os
from dotenv import load_dotenv
from utils.auth import check_password
from utils.bedrock_client import BedrockClient
from utils.image_processor import process_images, calculate_metrics, analyze_differences
import yaml
import json
import base64
from PIL import Image
import io

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title=os.getenv("APP_NAME", "Planogram Analyzer"),
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .upload-box {
        border: 2px dashed #4CAF50;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background-color: #f9f9f9;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        margin: 1rem 0;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Load configuration
@st.cache_resource
def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def validate_json_structure(json_data):
    """Validate that the JSON has the expected structure"""
    if not isinstance(json_data, dict):
        return False, "JSON debe ser un objeto"
    if 'diferencias' not in json_data:
        return False, "JSON debe contener 'diferencias'"
    if not isinstance(json_data['diferencias'], list):
        return False, "'diferencias' debe ser una lista"
    return True, "JSON válido"

def build_strict_prompt(base_prompt: str) -> str:
    """
    Refuerza el prompt: JSON-only + estructura exacta.
    (Si el prompt ya incluye las reglas, esto sólo reafirma.)
    """
    rules = """
REGLAS DE FORMATO ESTRICTO (OBLIGATORIAS):
- Devuelve EXCLUSIVAMENTE un JSON válido, sin texto adicional, sin markdown, sin comentarios.
- El JSON DEBE tener exactamente estas claves raíz: "diferencias" (array) y "conclusiones" (array).
- Cada item en "diferencias" tiene:
  {
    "nivel": <número>,
    "resultado": {
      "productos": [
        {
          "posicion_producto": <número>,
          "nombre": <string>,
          "encontrado": <true|false>,
          "posicion_correcta": <true|false>,
          "frentes_esperados": <número>,
          "frentes_encontrados": <número>
        }
      ]
    }
  }
- "conclusiones" es un array de strings con hallazgos.
- NO incluyas otras claves en la raíz (como "gondola", "productos", "metricas", "observaciones", etc.).
- Recorre TODO el planograma y evalúa CADA producto.
- Si no puedes confirmar un dato: "encontrado": false, "posicion_correcta": false, "frentes_encontrados": 0.
- No inventes productos: sólo evalúa los del JSON base.
"""
    return f"{base_prompt}\n\n{rules}".strip()

def compare_results(actual, expected):
    """Compare actual results with expected results"""
    comparison = {
        'matches': True,
        'differences': []
    }
    try:
        actual_json = json.dumps(actual, sort_keys=True)
        expected_json = json.dumps(expected, sort_keys=True)
        if actual_json != expected_json:
            comparison['matches'] = False
            comparison['differences'].append("Los resultados no coinciden exactamente con lo esperado")
    except Exception:
        comparison['matches'] = False
        comparison['differences'].append("No se pudo comparar los resultados")
    return comparison

def main():
    # Authentication
    if not check_password():
        st.stop()

    config = load_config()

    # Header
    st.title("🎯 " + os.getenv("APP_NAME", "Planogram Compliance Analyzer"))
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Model selection
        model_key = st.selectbox(
            "🤖 Modelo AI",
            options=list(config['models'].keys()),
            format_func=lambda x: config['models'][x]['name']
        )
        selected_model = config['models'][model_key]
        st.info(f"Model ID: `{selected_model['model_id']}`")

        # AWS Credentials Check
        st.subheader("🔐 Estado AWS")
        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            st.success("✅ Credenciales AWS configuradas")
        else:
            st.error("❌ Credenciales AWS no encontradas")
            st.warning("Por favor, configure AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en el archivo .env")

        # Prompt customization
        st.subheader("📝 Prompt Personalizado")
        lock_prompt = st.checkbox("🔒 Usar el prompt del config (enforzado) y deshabilitar edición", value=False)
        custom_prompt = st.text_area(
            "Ingrese su prompt:",
            value=config['default_prompt'],
            height=220,
            disabled=lock_prompt
        )

        # Advanced settings
        with st.expander("⚡ Configuración Avanzada"):
            temperature = st.slider("Temperature", 0.0, 1.0, float(selected_model.get('temperature', 0.1)))
            max_tokens = st.number_input("Max Tokens", 100, 8000, int(selected_model.get('max_tokens', 4096)))

            # Analysis options
            st.subheader("🔍 Opciones de Análisis")
            check_false_negatives = st.checkbox("Detectar Falsos Negativos", value=True)
            check_wrong_positions = st.checkbox("Detectar Productos Mal Posicionados", value=True)
            check_extra_products = st.checkbox("Detectar Productos No Planogramados", value=True)

    # Main content - 4 file inputs
    st.subheader("📁 Carga de Archivos")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📋 Planograma (Esperado)")
        planogram_file = st.file_uploader(
            "Cargar imagen del planograma",
            type=['png', 'jpg', 'jpeg'],
            key="planogram",
            help="Imagen que muestra cómo deben estar dispuestos los productos"
        )
        if planogram_file:
            st.image(planogram_file, use_column_width=True)

    with col2:
        st.markdown("#### 📸 Realograma (Actual)")
        realogram_file = st.file_uploader(
            "Cargar imagen del realograma",
            type=['png', 'jpg', 'jpeg'],
            key="realogram",
            help="Imagen que muestra cómo están dispuestos los productos actualmente"
        )
        if realogram_file:
            st.image(realogram_file, use_column_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("#### 📊 JSON Estructura del Planograma")
        json_structure_file = st.file_uploader(
            "Cargar JSON con estructura del planograma",
            type=['json', 'txt'],
            key="json_structure",
            help="JSON que describe la estructura esperada del planograma"
        )

        json_structure = None
        if json_structure_file:
            try:
                json_content = json_structure_file.read().decode('utf-8')
                json_structure = json.loads(json_content)
                st.success("✅ JSON de estructura cargado correctamente")

                # Validate JSON structure
                is_valid, message = validate_json_structure(json_structure)
                if is_valid:
                    # Show preview
                    with st.expander("Ver estructura del planograma"):
                        st.json(json_structure)
                else:
                    st.error(f"❌ Error en estructura JSON: {message}")
                    json_structure = None
            except Exception as e:
                st.error(f"❌ Error al parsear JSON: {str(e)}")

    with col4:
        st.markdown("#### 📝 JSON Resultado Esperado (Opcional)")
        json_expected_file = st.file_uploader(
            "Cargar JSON con resultado esperado (para validación)",
            type=['json', 'txt'],
            key="json_expected",
            help="JSON opcional para comparar con el resultado del análisis"
        )

        json_expected = None
        if json_expected_file:
            try:
                json_content = json_expected_file.read().decode('utf-8')
                json_expected = json.loads(json_content)
                st.success("✅ JSON esperado cargado correctamente")

                # Show preview
                with st.expander("Ver resultado esperado"):
                    st.json(json_expected)
            except Exception as e:
                st.error(f"❌ Error al parsear JSON esperado: {str(e)}")

    # Analysis button
    if st.button("🚀 Analizar Cumplimiento", type="primary"):
        # Validate required files
        if not planogram_file:
            st.error("❌ Por favor cargue la imagen del planograma")
            st.stop()

        if not realogram_file:
            st.error("❌ Por favor cargue la imagen del realograma")
            st.stop()

        if not json_structure:
            st.error("❌ Por favor cargue el JSON con la estructura del planograma")
            st.stop()

        # Check AWS credentials
        if not (os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")):
            st.error("❌ Configure las credenciales AWS en el archivo .env")
            st.stop()

        with st.spinner("🔄 Procesando imágenes y ejecutando análisis con IA..."):
            try:
                # Initialize Bedrock client
                bedrock_client = BedrockClient(
                    model_id=selected_model['model_id'],
                    region=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                )

                # Process images
                planogram_b64 = process_images(planogram_file)
                realogram_b64 = process_images(realogram_file)

                # Elegir prompt (bloqueado o editable) + refuerzo estricto
                base_prompt = config['default_prompt'] if lock_prompt else custom_prompt
                enhanced_prompt = build_strict_prompt(base_prompt)
                if check_false_negatives:
                    enhanced_prompt += "\n\n⚠️ Enfatiza búsqueda de FALSOS NEGATIVOS (productos presentes pero omitidos)."
                if check_wrong_positions:
                    enhanced_prompt += "\n⚠️ Verifica POSICIONES exactas (IZQ→DER por nivel)."
                if check_extra_products:
                    enhanced_prompt += "\n⚠️ Identifica PRODUCTOS NO PLANOGRAMADOS y menciónalos SOLO en 'conclusiones' (no en 'diferencias')."

                # Execute analysis
                result = bedrock_client.analyze_compliance(
                    planogram_b64,
                    realogram_b64,
                    enhanced_prompt,
                    json_structure,
                    float(temperature),
                    int(max_tokens)
                )

                st.success("✅ Análisis completado exitosamente!")

                # Calculate metrics
                differences_analysis = []
                if isinstance(result, dict):
                    metrics = calculate_metrics(result)

                    # Display metrics
                    st.markdown("### 📊 Métricas de Cumplimiento")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📦 Productos Encontrados", 
                                f"{metrics['found']}/{metrics['total']}",
                                delta=f"{metrics['found'] - metrics['total']}" if metrics['found'] != metrics['total'] else None)
                    with col2:
                        st.metric("✅ Posición Correcta", 
                                f"{metrics['correct_position']}/{metrics['total']}",
                                delta=f"{metrics['correct_position'] - metrics['total']}" if metrics['correct_position'] != metrics['total'] else None)
                    with col3:
                        st.metric("🔍 Recall", f"{metrics['recall']:.2%}",
                                delta="Objetivo: 100%" if metrics['recall'] < 1 else "✓")
                    with col4:
                        st.metric("🎯 Precisión", f"{metrics['precision']:.2%}",
                                delta="Objetivo: 100%" if metrics['precision'] < 1 else "✓")

                    # Additional analysis
                    if metrics['missing'] > 0:
                        st.warning(f"⚠️ {metrics['missing']} productos no fueron encontrados en el realograma")
                    
                    if metrics['wrong_position'] > 0:
                        st.warning(f"⚠️ {metrics['wrong_position']} productos están en posición incorrecta")

                # Results tabs
                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📄 JSON Resultado", "🔍 Análisis Detallado", "📊 Comparación", "🎯 Conclusiones", "💾 Descargar", "🛠️ Debug de invocación"])
                
                with tab1:
                    st.json(result)
                
                with tab2:
                    if isinstance(result, dict) and 'diferencias' in result:
                        st.subheader("📋 Análisis por Nivel")
                        differences_analysis = analyze_differences(result, json_expected)
                        
                        for nivel_info in differences_analysis:
                            with st.expander(f"Nivel {nivel_info['nivel']} - {nivel_info['status']}"):
                                st.write(f"**Total productos:** {nivel_info['total_products']}")
                                st.write(f"**Encontrados:** {nivel_info['found']}")
                                st.write(f"**Posición correcta:** {nivel_info['correct_position']}")
                                
                                if nivel_info['missing_products']:
                                    st.error(f"❌ Productos faltantes: {', '.join(nivel_info['missing_products'])}")
                                
                                if nivel_info['wrong_position_products']:
                                    st.warning(f"⚠️ Mal posicionados: {', '.join(nivel_info['wrong_position_products'])}")
                                
                                if nivel_info['frentes_issues']:
                                    st.info(f"📊 Problemas de frentes: {', '.join(nivel_info['frentes_issues'])}")
                
                with tab3:
                    if json_expected:
                        st.subheader("📊 Comparación con Resultado Esperado")
                        comparison = compare_results(result, json_expected)
                        
                        if comparison['matches']:
                            st.success("✅ El análisis coincide con el resultado esperado")
                        else:
                            st.warning("⚠️ Hay diferencias con el resultado esperado")
                            for diff in comparison['differences']:
                                st.write(f"• {diff}")
                
                with tab4:
                    if isinstance(result, dict) and 'conclusiones' in result and result['conclusiones']:
                        st.subheader("🔍 Conclusiones del Análisis")
                        for i, conclusion in enumerate(result['conclusiones'], 1):
                            if "no se encontr" in conclusion.lower() or "faltante" in conclusion.lower():
                                st.error(f"{i}. {conclusion}")
                            elif "mal posicion" in conclusion.lower() or "incorrecto" in conclusion.lower():
                                st.warning(f"{i}. {conclusion}")
                            else:
                                st.info(f"{i}. {conclusion}")
                    else:
                        st.info("No se generaron conclusiones automáticas")
                
                with tab5:
                    # Download JSON result
                    json_str = json.dumps(result, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📥 Descargar Resultado JSON",
                        data=json_str,
                        file_name="planogram_analysis_result.json",
                        mime="application/json"
                    )
                    
                    # Download metrics
                    if isinstance(result, dict):
                        metrics_data = {
                            "metrics": metrics,
                            "analysis_details": differences_analysis if 'diferencias' in result else []
                        }
                        metrics_str = json.dumps(metrics_data, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="📊 Descargar Métricas Detalladas",
                            data=metrics_str,
                            file_name="planogram_metrics.json",
                            mime="application/json"
                        )
                
                with tab6:
                    debug = result.get("_debug", {}) if isinstance(result, dict) else {}
                    st.write("**Debug de invocación**")
                    st.code(json.dumps(debug, indent=2, ensure_ascii=False))
                    
            except Exception as e:
                st.error(f"❌ Error en el análisis: {str(e)}")
                
                # Show more detailed error information
                if "UnrecognizedClientException" in str(e) or "security token" in str(e):
                    st.error("🔐 Error de autenticación AWS. Por favor verifique:")
                    st.write("1. Las credenciales AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en el archivo .env")
                    st.write("2. Que las credenciales tengan permisos para usar Bedrock")
                    st.write("3. Que la región configurada sea correcta")
                elif "ValidationException" in str(e):
                    st.error("❌ Error de validación. Verifique que el modelo esté disponible en su región o invoque vía Inference Profile (usar 'us.<model_id>' o ARN).")
                
                # Show full error for debugging
                with st.expander("Ver detalles del error"):
                    st.exception(e)

if __name__ == "__main__":
    main()
