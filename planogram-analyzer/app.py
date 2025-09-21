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
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title=os.getenv("APP_NAME", "Planogram Analyzer"),
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for Professional Platform Interface
st.markdown("""
<style>
    /* Main Layout */
    .main {
        padding: 1.5rem 2rem;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }

    /* Buttons */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        font-weight: 600;
        border-radius: 10px;
        border: none;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
        font-size: 16px;
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, #45a049 0%, #3d8b40 100%);
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
    }

    /* Primary Analysis Button */
    .stButton[data-testid="baseButton-primary"]>button {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
        font-size: 18px;
        padding: 1rem 2rem;
    }

    .stButton[data-testid="baseButton-primary"]>button:hover {
        background: linear-gradient(135deg, #FF5252 0%, #FF7043 100%);
        box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        backdrop-filter: blur(10px);
        margin: 1rem 0;
    }

    /* Upload Areas */
    .upload-container {
        background: white;
        border: 3px dashed #4CAF50;
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .upload-container:hover {
        border-color: #45a049;
        box-shadow: 0 6px 25px rgba(76, 175, 80, 0.2);
        transform: translateY(-2px);
    }

    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 0 15px 15px 0;
    }

    /* File Uploader */
    .stFileUploader {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }

    /* Alert Boxes */
    .stAlert {
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }

    /* Success Alert */
    .stAlert[data-baseweb="notification"][kind="success"] {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-left: 4px solid #28a745;
    }

    /* Warning Alert */
    .stAlert[data-baseweb="notification"][kind="warning"] {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border-left: 4px solid #ffc107;
    }

    /* Error Alert */
    .stAlert[data-baseweb="notification"][kind="error"] {
        background: linear-gradient(135deg, #f8d7da 0%, #f1c0c7 100%);
        border-left: 4px solid #dc3545;
    }

    /* Info Alert */
    .stAlert[data-baseweb="notification"][kind="info"] {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        border-left: 4px solid #17a2b8;
    }

    /* Tabs */
    .stTabs {
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        padding: 1rem;
        margin: 1rem 0;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 10px;
        font-weight: 600;
    }

    /* Code blocks */
    .stCodeBlock {
        border-radius: 10px;
        background: #2d3748;
        border: none;
    }

    /* JSON display */
    .stJson {
        background: #1a202c;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    /* Metrics */
    .metric-container {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin: 0.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }

    .metric-container:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    }

    /* Spinner */
    .stSpinner {
        background: rgba(255,255,255,0.9);
        border-radius: 15px;
        backdrop-filter: blur(10px);
    }

    /* Progress indicators */
    .stProgress .stProgress-bar {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        border-radius: 10px;
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

def build_final_prompt(user_prompt: str, custom_instructions: str = None) -> str:
    """
    Construye el prompt final combinando las instrucciones del usuario con reglas estrictas
    """

    # Reglas de formato que siempre se aplican
    format_rules = """

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
- NO incluyas otras claves en la raíz.
- Recorre TODO el planograma y evalúa CADA producto.
- Si no puedes confirmar un dato: "encontrado": false, "posicion_correcta": false, "frentes_encontrados": 0.
- No inventes productos: sólo evalúa los del JSON base.
"""

    # Construir prompt final
    final_prompt = user_prompt

    # Agregar instrucciones personalizadas si existen
    if custom_instructions and custom_instructions.strip():
        final_prompt += f"\n\nINSTRUCCIONES ADICIONALES DEL USUARIO:\n{custom_instructions.strip()}"

    # Siempre agregar reglas de formato al final
    final_prompt += format_rules

    return final_prompt.strip()

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

def save_prompt_context(prompt: str):
    """Guardar el prompt personalizado en session state como contexto"""
    if 'saved_prompts' not in st.session_state:
        st.session_state.saved_prompts = []
    st.session_state.saved_prompts.append(prompt)
    st.session_state.current_context = prompt

def main():
    # Authentication
    if not check_password():
        st.stop()

    config = load_config()

    # Initialize session state
    if 'current_context' not in st.session_state:
        st.session_state.current_context = None
    if 'use_custom_context' not in st.session_state:
        st.session_state.use_custom_context = False

    # Header with enhanced styling
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; text-align: center; margin: 0; font-size: 2.5em; font-weight: 700;">
            🎯 """ + os.getenv("APP_NAME", "Planogram Compliance Analyzer") + """
        </h1>
        <p style="color: rgba(255,255,255,0.9); text-align: center; margin: 1rem 0 0 0; font-size: 1.2em;">
            Análisis inteligente de cumplimiento con AWS Bedrock
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Model selection
        st.subheader("🤖 Modelo AI")
        model_key = st.selectbox(
            "Seleccionar modelo:",
            options=list(config['models'].keys()),
            format_func=lambda x: config['models'][x]['name']
        )
        selected_model = config['models'][model_key]
        st.info(f"Model ID: `{selected_model['model_id']}`")

        # System Status
        st.subheader("📊 Estado del Sistema")

        # AWS Status
        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            st.success("✅ AWS Bedrock: Conectado")
            st.info(f"🌍 Región: {os.getenv('AWS_DEFAULT_REGION', 'us-east-1')}")
        else:
            st.error("❌ AWS: No configurado")
            st.warning("Configure credenciales AWS en .env")

        # Model Status
        st.success(f"🤖 Modelo: {selected_model['name']}")
        st.info(f"🔧 ID: {selected_model['model_id']}")

        st.markdown("---")

        # Enhanced Prompt Customization
        st.subheader("📝 Instrucciones del Análisis")
        st.markdown("<p style='color: #7f8c8d; font-size: 0.9em;'>Personalice las instrucciones para el modelo AI</p>", unsafe_allow_html=True)

        # Prompt mode selection
        prompt_mode = st.radio(
            "Modo de prompt:",
            ["default", "custom", "instructions_only"],
            format_func=lambda x: {
                "default": "🎯 Usar prompt predefinido del sistema",
                "custom": "✏️ Editar prompt completo",
                "instructions_only": "📝 Solo agregar instrucciones adicionales"
            }[x],
            index=0,
            help="Seleccione cómo desea configurar las instrucciones"
        )

        if prompt_mode == "default":
            st.info("📝 Usando el prompt predefinido del sistema. El modelo seguirá las instrucciones estándar de análisis.")
            custom_prompt = config['default_prompt']
            lock_prompt = True

        elif prompt_mode == "custom":
            st.warning("⚠️ Modo avanzado: Edite el prompt completo. Use con precaución.")
            custom_prompt = st.text_area(
                "Prompt completo (incluye todas las instrucciones):",
                value=config['default_prompt'],
                height=300,
                help="Este será el prompt base. Se agregarán reglas de formato automáticamente."
            )
            lock_prompt = False

        else:  # instructions_only
            st.success("✨ Modo recomendado: Agregue instrucciones específicas que se combinarán con el prompt base.")
            custom_prompt = config['default_prompt']  # Always use base prompt
            lock_prompt = True

            # Custom instructions box
            additional_instructions = st.text_area(
                "Instrucciones adicionales (ejemplos: 'Solo analizar el primer nivel', 'Enfocarse en productos de marca X', etc.):",
                value="",
                height=150,
                placeholder="Ejemplo: Solo analizar los productos del nivel 1 y 2. Ignorar productos de marca Z.",
                help="Estas instrucciones se agregarán al prompt base del sistema."
            )

            # Save and load custom instructions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Guardar instrucciones") and additional_instructions.strip():
                    st.session_state.current_context = additional_instructions.strip()
                    st.session_state.use_custom_context = True
                    st.success("✅ Instrucciones guardadas")

            with col2:
                if st.button("🗑️ Limpiar instrucciones"):
                    st.session_state.current_context = None
                    st.session_state.use_custom_context = False
                    st.success("✅ Instrucciones limpiadas")

            # Show saved instructions
            if st.session_state.current_context:
                with st.expander("📄 Ver instrucciones guardadas"):
                    st.info(f"Instrucciones activas: {st.session_state.current_context}")

            # Update the custom_prompt with additional instructions if provided
            if additional_instructions.strip():
                st.session_state.current_context = additional_instructions.strip()
                st.session_state.use_custom_context = True

            # Advanced settings
            with st.expander("⚡ Configuración Avanzada"):
                temperature = st.slider("Temperature", 0.0, 1.0, float(selected_model.get('temperature', 0.1)))
                max_tokens = st.number_input("Max Tokens", 100, 8000, int(selected_model.get('max_tokens', 4096)))

                # Analysis options
                st.subheader("🔍 Opciones de Análisis")
                check_false_negatives = st.checkbox("Detectar Falsos Negativos", value=True)
                check_wrong_positions = st.checkbox("Detectar Productos Mal Posicionados", value=True)
                check_extra_products = st.checkbox("Detectar Productos No Planogramados", value=True)
                check_empty_spaces = st.checkbox("🆕 Detectar Espacios Vacíos", value=True)

    # Main content - File uploads with enhanced design
    st.markdown("<h2 style='text-align: center; color: #2c3e50; margin: 2rem 0;'>📁 Carga de Archivos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #7f8c8d; margin-bottom: 2rem;'>Suba las imágenes y archivos necesarios para el análisis</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="upload-container">
            <h4 style="color: #2c3e50; margin-bottom: 1rem;">📋 Planograma (Esperado)</h4>
            <p style="color: #7f8c8d; font-size: 0.9em;">Imagen que muestra cómo deben estar dispuestos los productos</p>
        </div>
        """, unsafe_allow_html=True)

        planogram_file = st.file_uploader(
            "Cargar imagen del planograma",
            type=['png', 'jpg', 'jpeg'],
            key="planogram",
            help="Imagen que muestra cómo deben estar dispuestos los productos"
        )
        if planogram_file:
            st.image(planogram_file, use_column_width=True, caption="Planograma cargado")

    with col2:
        st.markdown("""
        <div class="upload-container">
            <h4 style="color: #2c3e50; margin-bottom: 1rem;">📸 Realograma (Actual)</h4>
            <p style="color: #7f8c8d; font-size: 0.9em;">Imagen que muestra cómo están dispuestos los productos actualmente</p>
        </div>
        """, unsafe_allow_html=True)

        realogram_file = st.file_uploader(
            "Cargar imagen del realograma",
            type=['png', 'jpg', 'jpeg'],
            key="realogram",
            help="Imagen que muestra cómo están dispuestos los productos actualmente"
        )
        if realogram_file:
            st.image(realogram_file, use_column_width=True, caption="Realograma cargado")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("""
        <div class="upload-container">
            <h4 style="color: #2c3e50; margin-bottom: 1rem;">📊 JSON Estructura</h4>
            <p style="color: #7f8c8d; font-size: 0.9em;">JSON que describe la estructura esperada del planograma</p>
        </div>
        """, unsafe_allow_html=True)

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
        st.markdown("""
        <div class="upload-container">
            <h4 style="color: #2c3e50; margin-bottom: 1rem;">🎯 JSON Esperado (Opcional)</h4>
            <p style="color: #7f8c8d; font-size: 0.9em;">JSON opcional para comparar con el resultado del análisis</p>
        </div>
        """, unsafe_allow_html=True)

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

    # Analysis button with better validation
    st.markdown("<h2 style='text-align: center; color: #2c3e50; margin: 2rem 0;'>🚀 Ejecutar Análisis</h2>", unsafe_allow_html=True)

    # Pre-flight checks
    ready_to_analyze = True
    issues = []

    if not planogram_file:
        issues.append("📋 Imagen del planograma")
        ready_to_analyze = False

    if not realogram_file:
        issues.append("📸 Imagen del realograma")
        ready_to_analyze = False

    if not json_structure:
        issues.append("📊 JSON de estructura")
        ready_to_analyze = False

    if not (os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")):
        issues.append("🔐 Credenciales AWS")
        ready_to_analyze = False

    # Show status
    if ready_to_analyze:
        st.success("✅ Todo listo para el análisis")
    else:
        st.error(f"❌ Faltan elementos requeridos: {', '.join(issues)}")

    # Analysis button
    if st.button("🚀 Iniciar Análisis de Cumplimiento",
                type="primary",
                disabled=not ready_to_analyze,
                use_container_width=True):

        if not ready_to_analyze:
            st.error("❌ Complete todos los elementos requeridos antes de continuar")
            st.stop()

        with st.spinner("🔄 Procesando imágenes y ejecutando análisis con IA..."):
            try:
                result = None
                
                # Process images
                planogram_b64 = process_images(planogram_file)
                realogram_b64 = process_images(realogram_file)
                
                # Execute Bedrock analysis
                st.info("🤖 Ejecutando análisis con AWS Bedrock...")

                bedrock_client = BedrockClient(
                    model_id=selected_model['model_id'],
                    region=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                )

                # Build final prompt correctly
                if lock_prompt:
                    # Use default prompt from config
                    base_prompt = config['default_prompt']
                    user_instructions = None
                else:
                    # Use user's custom prompt
                    base_prompt = custom_prompt
                    user_instructions = None

                # If using saved context, treat it as additional instructions
                if st.session_state.use_custom_context and st.session_state.current_context:
                    user_instructions = st.session_state.current_context

                # Build analysis options as additional instructions
                analysis_options = []
                if 'check_false_negatives' in locals() and check_false_negatives:
                    analysis_options.append("⚠️ Enfatiza búsqueda de FALSOS NEGATIVOS.")
                if 'check_wrong_positions' in locals() and check_wrong_positions:
                    analysis_options.append("⚠️ Verifica POSICIONES exactas.")
                if 'check_extra_products' in locals() and check_extra_products:
                    analysis_options.append("⚠️ Identifica PRODUCTOS NO PLANOGRAMADOS.")
                if 'check_empty_spaces' in locals() and check_empty_spaces:
                    analysis_options.append("⚠️ Identifica ESPACIOS VACÍOS en góndola.")

                # Combine user instructions with analysis options
                combined_instructions = []
                if user_instructions:
                    combined_instructions.append(user_instructions)
                if analysis_options:
                    combined_instructions.extend(analysis_options)

                final_instructions = "\n".join(combined_instructions) if combined_instructions else None

                # Build the enhanced prompt
                enhanced_prompt = build_final_prompt(base_prompt, final_instructions)

                result = bedrock_client.analyze_compliance(
                    planogram_b64,
                    realogram_b64,
                    enhanced_prompt,
                    json_structure,
                    float(temperature) if 'temperature' in locals() else 0.1,
                    int(max_tokens) if 'max_tokens' in locals() else 4096
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
                                delta="Objetivo: 100%" if metrics['recall'] < 1 else "✔")
                    with col4:
                        st.metric("🎯 Precisión", f"{metrics['precision']:.2%}",
                                delta="Objetivo: 100%" if metrics['precision'] < 1 else "✔")

                    # Additional analysis
                    if metrics['missing'] > 0:
                        st.warning(f"⚠️ {metrics['missing']} productos no fueron encontrados en el realograma")
                    
                    if metrics['wrong_position'] > 0:
                        st.warning(f"⚠️ {metrics['wrong_position']} productos están en posición incorrecta")

                # Results tabs
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📄 Resultado JSON",
                    "🔍 Análisis Detallado",
                    "📊 Comparación",
                    "🎯 Conclusiones",
                    "💾 Descargar"
                ])

                with tab1:  # JSON Result
                    st.subheader("📄 Resultado del Análisis")
                    st.json(result)

                with tab2:  # Detailed Analysis
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
                
                with tab3:  # Comparison
                    st.subheader("📊 Comparación con Resultado Esperado")
                    if json_expected:
                        comparison = compare_results(result, json_expected)

                        if comparison['matches']:
                            st.success("✅ El análisis coincide con el resultado esperado")
                        else:
                            st.warning("⚠️ Hay diferencias con el resultado esperado")
                            for diff in comparison['differences']:
                                st.write(f"• {diff}")
                    else:
                        st.info("ℹ️ No se cargó un JSON esperado para comparación")
                
                with tab4:  # Conclusions
                    st.markdown("<h3 style='color: #2c3e50;'>🎯 Conclusiones del Análisis</h3>", unsafe_allow_html=True)
                    st.markdown("<p style='color: #7f8c8d;'>Resumen de hallazgos y recomendaciones del AI</p>", unsafe_allow_html=True)

                    if isinstance(result, dict) and 'conclusiones' in result and result['conclusiones']:
                        st.markdown("---")

                        for i, conclusion in enumerate(result['conclusiones'], 1):
                            if "no se encontr" in conclusion.lower() or "faltante" in conclusion.lower():
                                st.error(f"🔴 **Problema Crítico {i}:** {conclusion}")
                            elif "mal posicion" in conclusion.lower() or "incorrecto" in conclusion.lower():
                                st.warning(f"⚠️ **Problema Moderado {i}:** {conclusion}")
                            elif "vacío" in conclusion.lower() or "espacio" in conclusion.lower():
                                st.info(f"🔲 **Espacio Vacío {i}:** {conclusion}")
                            else:
                                st.success(f"✅ **Observación {i}:** {conclusion}")
                    else:
                        st.info("ℹ️ No se generaron conclusiones automáticas en esta ejecución")
                
                with tab5:  # Download
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
                            "analysis_details": differences_analysis if 'diferencias' in result else [],
                            "analysis_mode": "bedrock",
                            "custom_context_used": st.session_state.use_custom_context
                        }
                        metrics_str = json.dumps(metrics_data, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="📊 Descargar Métricas Detalladas",
                            data=metrics_str,
                            file_name="planogram_metrics.json",
                            mime="application/json"
                        )
                

                    # Debug information
                    with st.expander("🛠️ Debug Information"):
                        debug = result.get("_debug", {}) if isinstance(result, dict) else {}
                        debug['analysis_mode'] = "bedrock"
                        debug['custom_context_used'] = st.session_state.use_custom_context
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
                    st.error("❌ Error de validación. Verifique que el modelo esté disponible en su región.")
                elif "InvalidImageException" in str(e):
                    st.error("❌ Error con las imágenes. Verifique que las imágenes sean válidas.")
                
                # Show full error for debugging
                with st.expander("Ver detalles del error"):
                    st.exception(e)

if __name__ == "__main__":
    main()