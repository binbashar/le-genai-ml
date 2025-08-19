import streamlit as st
import os
from dotenv import load_dotenv
from utils.auth import check_password
from utils.bedrock_client import BedrockClient
from utils.image_processor import process_images, calculate_metrics
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
</style>
""", unsafe_allow_html=True)

# Load configuration
@st.cache_resource
def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

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
            "📤 Modelo AI",
            options=list(config['models'].keys()),
            format_func=lambda x: config['models'][x]['name']
        )
        
        selected_model = config['models'][model_key]
        st.info(f"Model ID: `{selected_model['model_id']}`")
        
        # Prompt customization
        st.subheader("📝 Prompt Personalizado")
        custom_prompt = st.text_area(
            "Ingrese su prompt:",
            value=config['default_prompt'],
            height=300
        )
        
        # Advanced settings
        with st.expander("⚡ Configuración Avanzada"):
            temperature = st.slider("Temperature", 0.0, 1.0, selected_model['temperature'])
            max_tokens = st.number_input("Max Tokens", 100, 8000, selected_model['max_tokens'])
    
    # Main content
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Planograma (Esperado)")
        planogram_file = st.file_uploader(
            "Cargar imagen del planograma",
            type=['png', 'jpg', 'jpeg'],
            key="planogram"
        )
        if planogram_file:
            st.image(planogram_file, use_column_width=True)
    
    with col2:
        st.subheader("📸 Realograma (Actual)")
        realogram_file = st.file_uploader(
            "Cargar imagen del realograma",
            type=['png', 'jpg', 'jpeg'],
            key="realogram"
        )
        if realogram_file:
            st.image(realogram_file, use_column_width=True)
    
    # JSON structure input
    st.subheader("📊 Estructura JSON del Planograma")
    json_structure = st.text_area(
        "Ingrese el JSON con la estructura del planograma:",
        height=200,
        placeholder='{"diferencias": [...], "conclusiones": [...]}'
    )
    
    # Analysis button
    if st.button("🚀 Analizar Cumplimiento", type="primary"):
        if planogram_file and realogram_file:
            with st.spinner("🔄 Procesando imágenes y ejecutando análisis..."):
                try:
                    # Initialize Bedrock client
                    bedrock_client = BedrockClient(
                        model_id=selected_model['model_id'],
                        region=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                    )
                    
                    # Process images
                    planogram_b64 = process_images(planogram_file)
                    realogram_b64 = process_images(realogram_file)
                    
                    # Parse JSON if provided
                    json_data = {}
                    if json_structure:
                        try:
                            json_data = json.loads(json_structure)
                        except:
                            st.warning("⚠️ JSON inválido, continuando sin estructura")
                    
                    # Execute analysis
                    result = bedrock_client.analyze_compliance(
                        planogram_b64,
                        realogram_b64,
                        custom_prompt,
                        json_data,
                        temperature,
                        max_tokens
                    )
                    
                    # Display results
                    st.success("✅ Análisis completado exitosamente!")
                    
                    # Metrics
                    if isinstance(result, dict):
                        metrics = calculate_metrics(result)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("📦 Productos Encontrados", f"{metrics['found']}/{metrics['total']}")
                        with col2:
                            st.metric("✅ Posición Correcta", f"{metrics['correct_position']}/{metrics['total']}")
                        with col3:
                            st.metric("📊 Recall", f"{metrics['recall']:.2%}")
                        with col4:
                            st.metric("🎯 Precisión", f"{metrics['precision']:.2%}")
                    
                    # Results tabs
                    tab1, tab2, tab3 = st.tabs(["📄 JSON Resultado", "📊 Análisis Visual", "💾 Descargar"])
                    
                    with tab1:
                        st.json(result)
                    
                    with tab2:
                        if 'conclusiones' in result:
                            st.subheader("🔍 Conclusiones")
                            for i, conclusion in enumerate(result['conclusiones'], 1):
                                st.write(f"{i}. {conclusion}")
                    
                    with tab3:
                        # Download JSON
                        json_str = json.dumps(result, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="📥 Descargar JSON",
                            data=json_str,
                            file_name="planogram_analysis.json",
                            mime="application/json"
                        )
                        
                        # Download metrics
                        if isinstance(result, dict):
                            metrics_str = json.dumps(metrics, indent=2)
                            st.download_button(
                                label="📊 Descargar Métricas",
                                data=metrics_str,
                                file_name="metrics.json",
                                mime="application/json"
                            )
                    
                except Exception as e:
                    st.error(f"❌ Error en el análisis: {str(e)}")
                    st.exception(e)
        else:
            st.warning("⚠️ Por favor cargue ambas imágenes antes de analizar")

if __name__ == "__main__":
    main()