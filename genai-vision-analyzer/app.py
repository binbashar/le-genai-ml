import streamlit as st
import os
from dotenv import load_dotenv
from utils.bedrock_client import BedrockClient
from utils.image_processor import process_images
import yaml
import json
import base64
from PIL import Image
import io
import pandas as pd
from datetime import datetime

# Load environment variables FIRST
load_dotenv()

# Page config
st.set_page_config(
    page_title=os.getenv("APP_NAME", "Planogram Compliance Platform"),
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Minimal CSS - Let Streamlit's light theme handle most styling
st.markdown(
    """
<style>
    /* Just enhance the header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Upload containers with subtle enhancement */
    .upload-box {
        border: 2px dashed #e0e0e0;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        background: #fafafa;
        margin: 0.5rem 0;
    }
    
    .upload-box:hover {
        border-color: #667eea;
        background: #f8f9ff;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Load configuration
@st.cache_resource
def load_config():
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except:
        # Default config if file doesn't exist
        st.error("❌ config.yaml not found. Please create configuration file.")
        return {
            "models": {
                "anthropic-sonnet": {
                    "name": "Anthropic Sonnet 3",
                    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                    "temperature": 0.1,
                    "max_tokens": 4096,
                }
            },
            "default_prompt": "Analyze the planogram compliance comparing the expected vs actual images.",
        }


def check_password():
    """Returns True if the user has the correct username and password"""

    def verify_credentials():
        """Checks whether username and password entered are correct"""
        # Read from environment variables - NO DEFAULTS
        correct_username = os.getenv("APP_USER")
        correct_password = os.getenv("APP_PASSWORD")

        if not correct_username or not correct_password:
            st.error(
                "❌ Authentication not configured. Please set APP_USER and APP_PASSWORD in .env file"
            )
            st.session_state["password_correct"] = False
            return

        if (
            st.session_state.get("username") == correct_username
            and st.session_state.get("password") == correct_password
        ):
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
            if "username" in st.session_state:
                del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # First time - no password check yet
    if "password_correct" not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(
                """
            <div style="text-align: center; margin-top: 100px;">
                <h2 style="color: #333;">🔐 Platform Authentication</h2>
                <p style="color: #666;">Enter your credentials to access</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            with st.form("login_form"):
                st.text_input("Username", key="username", placeholder="Enter username")
                st.text_input(
                    "Password",
                    type="password",
                    key="password",
                    placeholder="Enter password",
                )
                submitted = st.form_submit_button(
                    "Login", type="primary", use_container_width=True
                )

                if submitted:
                    verify_credentials()

            if os.getenv("APP_USER") and os.getenv("APP_PASSWORD"):
                st.caption("✅ Credentials configured in .env file")
            else:
                st.warning("⚠️ Please configure APP_USER and APP_PASSWORD in .env file")
        return False

    # Password was wrong
    elif not st.session_state.get("password_correct", False):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(
                """
            <div style="text-align: center; margin-top: 100px;">
                <h2 style="color: #333;">🔐 Platform Authentication</h2>
            </div>
            """,
                unsafe_allow_html=True,
            )

            with st.form("login_form"):
                st.text_input("Username", key="username", placeholder="Enter username")
                st.text_input(
                    "Password",
                    type="password",
                    key="password",
                    placeholder="Enter password",
                )
                submitted = st.form_submit_button(
                    "Login", type="primary", use_container_width=True
                )

                if submitted:
                    verify_credentials()

            st.error("❌ Incorrect username or password. Please try again.")

            if not (os.getenv("APP_USER") and os.getenv("APP_PASSWORD")):
                st.warning("⚠️ Please configure APP_USER and APP_PASSWORD in .env file")
        return False

    # Password correct
    else:
        return True


def validate_json_structure(json_data):
    """Validate JSON structure"""
    if not isinstance(json_data, dict):
        return False, "JSON must be an object"
    return True, "Valid JSON"


def calculate_metrics_from_result(result, json_structure=None):
    """Calculate metrics from analysis result based on actual vs expected"""
    metrics = {
        "total_expected": 0,
        "total_found": 0,
        "correct_position": 0,
        "missing": 0,
        "wrong_position": 0,
        "recall": 0.0,
        "precision": 0.0,
        "compliance_rate": 0.0,
    }

    try:
        # First, count expected products from compliance JSON if available
        if json_structure and isinstance(json_structure, dict):
            # Count total expected products from the structure
            if "diferencias" in json_structure:
                for level in json_structure["diferencias"]:
                    if "resultado" in level and "productos" in level["resultado"]:
                        metrics["total_expected"] += len(
                            level["resultado"]["productos"]
                        )
            elif "niveles" in json_structure:
                for level in json_structure["niveles"]:
                    if "productos" in level:
                        metrics["total_expected"] += len(level["productos"])
            elif "products" in json_structure:
                metrics["total_expected"] = len(json_structure["products"])

        # Handle both dict and string responses
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                return metrics

        # Count actual results
        if isinstance(result, dict) and "diferencias" in result:
            products_analyzed = []

            for level in result["diferencias"]:
                if "resultado" in level and "productos" in level["resultado"]:
                    for product in level["resultado"]["productos"]:
                        products_analyzed.append(product)

                        # Count if product was found
                        if product.get("encontrado", False):
                            metrics["total_found"] += 1

                            # Check if in correct position
                            if product.get("posicion_correcta", False):
                                metrics["correct_position"] += 1
                            else:
                                metrics["wrong_position"] += 1
                        else:
                            metrics["missing"] += 1

            # If no expected count from structure, use analyzed count
            if metrics["total_expected"] == 0:
                metrics["total_expected"] = len(products_analyzed)

            # Calculate rates
            if metrics["total_expected"] > 0:
                # Recall: How many of expected products were found
                metrics["recall"] = metrics["total_found"] / metrics["total_expected"]
                # Compliance: How many are in correct position out of total expected
                metrics["compliance_rate"] = (
                    metrics["correct_position"] / metrics["total_expected"]
                )

            if metrics["total_found"] > 0:
                # Precision: Of those found, how many are correct
                metrics["precision"] = (
                    metrics["correct_position"] / metrics["total_found"]
                )

    except Exception as e:
        st.warning(f"Note: Metrics calculation encountered an issue: {str(e)}")

    return metrics


def build_final_prompt(user_prompt: str) -> str:
    """Build the final prompt with format rules"""
    format_rules = """

STRICT OUTPUT FORMAT - Return ONLY valid JSON:
{
  "diferencias": [
    {
      "nivel": <number>,
      "resultado": {
        "productos": [
          {
            "posicion_producto": <number>,
            "nombre": <string>,
            "encontrado": <boolean>,
            "posicion_correcta": <boolean>,
            "frentes_esperados": <number>,
            "frentes_encontrados": <number>
          }
        ]
      }
    }
  ],
  "conclusiones": [<strings>]
}

Return ONLY JSON, no markdown, no text.
"""

    return user_prompt + format_rules


def parse_bedrock_response(response_text):
    """Parse Bedrock response handling various formats"""
    try:
        if isinstance(response_text, dict):
            return response_text

        if isinstance(response_text, str):
            cleaned = response_text.strip()

            # Remove markdown formatting if present
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]

            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            cleaned = cleaned.strip()
            return json.loads(cleaned)
    except Exception as e:
        st.error(f"Failed to parse AI response: {str(e)}")
        return None


def main():
    # Check authentication
    if not check_password():
        st.stop()

    # Load config
    config = load_config()

    # Header with gradient
    st.markdown(
        """
    <div class="main-header">
        <h1 style="color: white; text-align: center; margin: 0; font-size: 2.5em; font-weight: 700;">
            🎯 Planogram Compliance Platform
        </h1>
        <p style="color: rgba(255,255,255,0.9); text-align: center; margin: 0.5rem 0 0 0; font-size: 1.1em;">
            AI-Powered Retail Execution Analysis with AWS Bedrock
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Model Selection
        st.subheader("🤖 AI Model")
        model_key = st.selectbox(
            "Select model:",
            options=list(config["models"].keys()),
            format_func=lambda x: config["models"][x]["name"],
        )
        selected_model = config["models"][model_key]

        # System Status
        st.subheader("📊 System Status")

        # Check AWS credentials from .env
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")

        if aws_key and aws_secret:
            st.success("✅ AWS Connected")
            st.info(f"🌍 Region: {aws_region}")
        else:
            st.error("❌ AWS Not Configured")
            st.warning("Add AWS credentials to .env file")

        st.success(f"🤖 Model: {selected_model['name']}")

        with st.expander("📋 Model Details"):
            st.code(f"ID: {selected_model['model_id']}")

        st.divider()

        # Analysis Configuration - ONLY 2 MODES
        st.subheader("📝 Analysis Configuration")

        prompt_mode = st.radio(
            "Prompt mode:",
            ["default", "custom"],
            format_func=lambda x: {
                "default": "🎯 Use Configuration Default",
                "custom": "✏️ Full Custom Prompt",
            }[x],
            index=0,
            help="Default uses config.yaml prompt, Custom ignores config and uses only your input",
        )

        if prompt_mode == "default":
            # DEFAULT MODE - Use config.yaml prompt
            final_prompt = config.get(
                "default_prompt", "Analyze the planogram compliance."
            )
            st.success("✅ Using prompt from config.yaml")

            with st.expander("View Default Prompt"):
                st.text_area(
                    "Current default prompt:",
                    value=final_prompt,
                    height=150,
                    disabled=True,
                    help="This prompt is defined in config.yaml",
                )

        else:  # custom
            # CUSTOM MODE - Ignore config, use only user input
            st.warning("⚠️ Custom mode - config.yaml prompt will be ignored")

            custom_prompt = st.text_area(
                "Enter your complete custom prompt:",
                value="",
                height=200,
                placeholder="Enter your full prompt here. This will completely replace the default prompt.",
                help="This prompt will be used instead of config.yaml default",
            )

            if custom_prompt.strip():
                final_prompt = custom_prompt.strip()
            else:
                st.error("❌ Please enter a custom prompt")
                final_prompt = None

        # Advanced Settings
        with st.expander("⚙️ Advanced Settings"):
            temperature = st.slider(
                "Temperature",
                0.0,
                1.0,
                float(selected_model.get("temperature", 0.1)),
                0.1,
                help="Lower = more focused, Higher = more creative",
            )
            max_tokens = st.number_input(
                "Max Tokens",
                1000,
                8000,
                int(selected_model.get("max_tokens", 4096)),
                500,
                help="Maximum length of response",
            )

    # Main Content Area
    st.header("📁 File Upload")

    # File upload section with columns
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
        <div class="upload-box">
            <h4>📋 Planogram Image</h4>
            <p style="color: #666; font-size: 0.9em;">Expected product arrangement</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        planogram_file = st.file_uploader(
            "Upload planogram",
            type=["png", "jpg", "jpeg"],
            key="planogram",
            label_visibility="collapsed",
        )
        if planogram_file:
            st.image(
                planogram_file, use_column_width=True, caption="✅ Planogram loaded"
            )

    with col2:
        st.markdown(
            """
        <div class="upload-box">
            <h4>📸 Realogram Image</h4>
            <p style="color: #666; font-size: 0.9em;">Actual shelf photograph</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        realogram_file = st.file_uploader(
            "Upload realogram",
            type=["png", "jpg", "jpeg"],
            key="realogram",
            label_visibility="collapsed",
        )
        if realogram_file:
            st.image(
                realogram_file, use_column_width=True, caption="✅ Realogram loaded"
            )

    # Compliance JSON upload
    st.markdown(
        """
    <div class="upload-box">
        <h4>📊 Compliance JSON</h4>
        <p style="color: #666; font-size: 0.9em;">Product structure and compliance rules</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    json_structure_file = st.file_uploader(
        "Upload JSON",
        type=["json", "txt"],
        key="json_structure",
        label_visibility="collapsed",
    )

    json_structure = None
    if json_structure_file:
        try:
            json_content = json_structure_file.read().decode("utf-8")
            json_structure = json.loads(json_content)
            st.success("✅ Compliance JSON loaded successfully")

            is_valid, message = validate_json_structure(json_structure)
            if is_valid:
                with st.expander("📄 View Structure"):
                    st.json(json_structure)
            else:
                st.error(f"❌ Invalid JSON: {message}")
                json_structure = None
        except Exception as e:
            st.error(f"❌ Error parsing JSON: {str(e)}")

    # Analysis Section
    st.header("🚀 Analysis")

    # Requirements check
    ready = True
    missing = []

    if not planogram_file:
        missing.append("Planogram Image")
        ready = False
    if not realogram_file:
        missing.append("Realogram Image")
        ready = False
    if not json_structure:
        missing.append("Compliance JSON")
        ready = False
    if not (aws_key and aws_secret):
        missing.append("AWS Credentials in .env")
        ready = False
    if prompt_mode == "custom" and not final_prompt:
        missing.append("Custom Prompt")
        ready = False

    # Status display
    if ready:
        st.success("✅ All requirements satisfied - Ready to analyze")
    else:
        st.warning(f"⚠️ Missing requirements: {', '.join(missing)}")

    # Analysis button
    if st.button(
        "🚀 START COMPLIANCE ANALYSIS",
        type="primary",
        disabled=not ready,
        use_container_width=True,
    ):
        if not ready:
            st.error("❌ Please complete all requirements before starting")
            st.stop()

        with st.spinner("🔄 Processing images and executing AI analysis..."):
            try:
                # Process images
                planogram_b64 = process_images(planogram_file)
                realogram_b64 = process_images(realogram_file)

                # Progress indication
                progress = st.progress(0)
                status = st.empty()

                status.text("📤 Connecting to AWS Bedrock...")
                progress.progress(20)

                # Initialize Bedrock client with credentials from .env
                bedrock_client = BedrockClient(
                    model_id=selected_model["model_id"], region=aws_region
                )

                # Build the enhanced prompt with format rules
                enhanced_prompt = build_final_prompt(final_prompt)

                status.text("🤖 Analyzing compliance with AI...")
                progress.progress(50)

                # Execute analysis
                result = bedrock_client.analyze_compliance(
                    planogram_b64,
                    realogram_b64,
                    enhanced_prompt,
                    json_structure,
                    temperature,
                    max_tokens,
                )

                status.text("📊 Processing results...")
                progress.progress(80)

                # Parse response
                if isinstance(result, str):
                    result = parse_bedrock_response(result)

                if result is None:
                    st.error("❌ Failed to parse AI response")
                    st.stop()

                # Calculate metrics
                metrics = calculate_metrics_from_result(result, json_structure)

                progress.progress(100)
                status.empty()
                progress.empty()

                st.success("✅ **Analysis completed successfully!**")

                # Store results in session_state for later comparison
                st.session_state["bedrock_result"] = result
                st.session_state["bedrock_metrics"] = metrics

                # Display token usage
                if "_usage" in result:
                    usage = result["_usage"]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "📥 Tokens de Entrada", f"{usage.get('input_tokens', 0):,}"
                        )
                    with col2:
                        st.metric(
                            "📤 Tokens de Salida", f"{usage.get('output_tokens', 0):,}"
                        )
                    with col3:
                        st.metric(
                            "📊 Total Tokens", f"{usage.get('total_tokens', 0):,}"
                        )

                # Results tabs
                tab1, tab2 = st.tabs(["📄 Analysis Results", "💾 Export Data"])

                with tab1:
                    st.subheader("JSON Output")
                    st.json(result)

                with tab2:
                    st.subheader("Export Options")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        # JSON export
                        json_str = json.dumps(result, indent=2, ensure_ascii=False)
                        st.download_button(
                            "📥 Download JSON",
                            json_str,
                            f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            "application/json",
                            use_container_width=True,
                        )

                    with col2:
                        # Metrics export
                        metrics_data = {
                            "timestamp": datetime.now().isoformat(),
                            "model": selected_model["model_id"],
                            "region": aws_region,
                            "metrics": {
                                "total_expected": metrics["total_expected"],
                                "total_found": metrics["total_found"],
                                "correct_position": metrics["correct_position"],
                                "missing": metrics["missing"],
                                "wrong_position": metrics["wrong_position"],
                                "recall": f"{metrics['recall']:.2%}",
                                "precision": (
                                    f"{metrics['precision']:.2%}"
                                    if metrics["precision"] > 0
                                    else "N/A"
                                ),
                                "compliance_rate": f"{metrics['compliance_rate']:.2%}",
                            },
                            "configuration": {
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "prompt_mode": prompt_mode,
                            },
                        }
                        metrics_str = json.dumps(metrics_data, indent=2)
                        st.download_button(
                            "📊 Download Metrics",
                            metrics_str,
                            f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            "application/json",
                            use_container_width=True,
                        )

                    with col3:
                        # CSV export
                        data = []
                        if isinstance(result, dict) and "diferencias" in result:
                            for level in result["diferencias"]:
                                if (
                                    "resultado" in level
                                    and "productos" in level["resultado"]
                                ):
                                    for product in level["resultado"]["productos"]:
                                        frentes_actual = product.get(
                                            "frentes_encontrados"
                                        )
                                        if frentes_actual is None:
                                            frentes_actual = product.get(
                                                "cantidad_frentes_encontrados", 0
                                            )

                                        data.append(
                                            {
                                                "Level": level.get("nivel", "N/A"),
                                                "Product": product.get(
                                                    "nombre", "Unknown"
                                                ),
                                                "Found": (
                                                    "✅"
                                                    if product.get("encontrado", False)
                                                    else "❌"
                                                ),
                                                "Correct": (
                                                    "✅"
                                                    if product.get(
                                                        "posicion_correcta", False
                                                    )
                                                    else "❌"
                                                ),
                                                "Expected": product.get(
                                                    "frentes_esperados", 0
                                                ),
                                                "Actual": frentes_actual,
                                            }
                                        )

                        if data:
                            df = pd.DataFrame(data)
                            csv = df.to_csv(index=False)
                            st.download_button(
                                "📑 Download CSV",
                                csv,
                                f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                "text/csv",
                                use_container_width=True,
                            )

                # Debug info
                with st.expander("🛠️ Technical Details"):
                    debug_info = {
                        "timestamp": datetime.now().isoformat(),
                        "model": selected_model["model_id"],
                        "region": aws_region,
                        "aws_configured": bool(aws_key and aws_secret),
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "prompt_mode": prompt_mode,
                        "prompt_source": (
                            "config.yaml" if prompt_mode == "default" else "user_input"
                        ),
                    }
                    st.json(debug_info)

            except Exception as e:
                st.error(f"❌ Analysis Error: {str(e)}")

                error_type = type(e).__name__

                if "UnrecognizedClientException" in str(e) or "security token" in str(
                    e
                ):
                    st.error("🔐 AWS Authentication Failed")
                    st.write("Please check in your .env file:")
                    st.code("""
APP_USER=your_username
APP_PASSWORD=your_password
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=us-west-2
                    """)
                elif "ValidationException" in str(e):
                    st.error("❌ Model validation error")
                    st.write(
                        f"Model {selected_model['model_id']} may not be available in {aws_region}"
                    )

                with st.expander("🔍 Full Error Details"):
                    st.exception(e)

    # Comparison Section - Outside button block to persist across reruns
    if "bedrock_result" in st.session_state:
        st.divider()
        st.subheader("🔍 Optional: Compare with Expected Results")
        st.info(
            "📤 Sube un JSON esperado para comparar la salida de Bedrock con los resultados esperados y calcular métricas de precisión del modelo."
        )

        expected_json_file = st.file_uploader(
            "Upload Expected JSON (Optional)",
            type=["json", "txt"],
            key="expected_json_comparison",
            help="Sube el JSON con los resultados esperados para comparar con la salida de Bedrock",
        )

        if expected_json_file:
            try:
                expected_json_content = expected_json_file.read().decode("utf-8")
                expected_json = json.loads(expected_json_content)
                st.success("✅ Expected JSON loaded successfully")

                # AI-powered comparison
                st.subheader("📋 Comparación: Bedrock vs Expected")

                with st.spinner("🤖 Analizando diferencias con IA..."):
                    bedrock_result = st.session_state["bedrock_result"]

                    # Build prompt for AI comparison
                    comparison_prompt = f"""
Compara estos dos JSONs y genera un análisis de diferencias detallado.

JSON 1 (Bedrock - Resultado de IA):
{json.dumps(bedrock_result, indent=2, ensure_ascii=False)}

JSON 2 (Expected - Ground Truth):
{json.dumps(expected_json, indent=2, ensure_ascii=False)}

Tu tarea:
1. Compara producto por producto, usando el nombre y posición para hacer el matching
2. Para cada producto comparado, indica si coinciden los campos: encontrado, posicion_correcta, frentes_encontrados
3. Cuenta las diferencias totales
4. Genera un JSON con este formato:

{{
  "total_productos": <número>,
  "coincidencias_exactas": <número>,
  "diferencias_encontrado": <número>,
  "diferencias_posicion": <número>,
  "diferencias_frentes": <número>,
  "productos": [
    {{
      "nivel": <número>,
      "posicion": <número>,
      "nombre": "<nombre del producto>",
      "bedrock": {{
        "encontrado": <true/false>,
        "posicion_correcta": <true/false>,
        "frentes_encontrados": <número>
      }},
      "expected": {{
        "encontrado": <true/false>,
        "posicion_correcta": <true/false>,
        "frentes_encontrados": <número>
      }},
      "matches": {{
        "encontrado": <true/false>,
        "posicion_correcta": <true/false>,
        "frentes_encontrados": <true/false>,
        "exacto": <true/false>
      }}
    }}
  ]
}}

IMPORTANTE: Devuelve SOLO el JSON, sin texto adicional.
"""

                    # Call Bedrock for intelligent comparison
                    bedrock_client = BedrockClient(
                        model_id=selected_model["model_id"], region=aws_region
                    )

                    # Build request body based on provider
                    provider = bedrock_client._provider_from_id(
                        bedrock_client.original_model_id
                    )

                    if provider == "anthropic":
                        body = {
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 10000,
                            "temperature": 0.1,
                            "messages": [
                                {"role": "user", "content": comparison_prompt}
                            ],
                        }
                    else:
                        # Generic/Nova format
                        body = {
                            "schemaVersion": "messages-v1",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [{"inputText": comparison_prompt}],
                                }
                            ],
                            "inferenceConfig": {"maxTokens": 10000, "temperature": 0.1},
                        }

                    # Use resolved_model_id (with inference profile)
                    comparison_response = bedrock_client.client.invoke_model(
                        modelId=bedrock_client.resolved_model_id, body=json.dumps(body)
                    )

                    response_body = json.loads(comparison_response["body"].read())

                    # Extract text and usage
                    comparison_text = (
                        bedrock_client._extract_text(response_body, provider) or ""
                    )
                    comparison_usage = bedrock_client._extract_usage(
                        response_body, provider
                    )

                    # Parse the JSON response
                    try:
                        # Extract JSON from response (in case there's extra text)
                        import re

                        json_match = re.search(r"\{.*\}", comparison_text, re.DOTALL)
                        if json_match:
                            comparison_result = json.loads(json_match.group())
                        else:
                            comparison_result = json.loads(comparison_text)
                    except:
                        st.error("Error parsing AI comparison response")
                        comparison_result = {
                            "total_productos": 0,
                            "coincidencias_exactas": 0,
                            "diferencias_encontrado": 0,
                            "diferencias_posicion": 0,
                            "diferencias_frentes": 0,
                            "productos": [],
                        }

                # Display comparison token usage
                if comparison_usage:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "📥 Tokens Entrada (Comparación)",
                            f"{comparison_usage.get('input_tokens', 0):,}",
                        )
                    with col2:
                        st.metric(
                            "📤 Tokens Salida (Comparación)",
                            f"{comparison_usage.get('output_tokens', 0):,}",
                        )
                    with col3:
                        st.metric(
                            "📊 Total Tokens (Comparación)",
                            f"{comparison_usage.get('total_tokens', 0):,}",
                        )

                # Display results
                st.json(comparison_result)

                # Download button
                comparison_json_str = json.dumps(
                    comparison_result, indent=2, ensure_ascii=False
                )
                st.download_button(
                    "📥 Descargar Comparación JSON",
                    comparison_json_str,
                    f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "application/json",
                    use_container_width=True,
                )

                # Summary
                total = comparison_result["total_productos"]
                matches = comparison_result["coincidencias_exactas"]
                st.success(
                    f"✅ Coincidencias exactas: {matches}/{total} productos ({matches/total*100:.1f}%)"
                    if total > 0
                    else "Sin productos"
                )

                if comparison_result["diferencias_encontrado"] > 0:
                    st.warning(
                        f"⚠️ Diferencias en 'encontrado': {comparison_result['diferencias_encontrado']}"
                    )
                if comparison_result["diferencias_posicion"] > 0:
                    st.warning(
                        f"⚠️ Diferencias en 'posicion_correcta': {comparison_result['diferencias_posicion']}"
                    )
                if comparison_result["diferencias_frentes"] > 0:
                    st.warning(
                        f"⚠️ Diferencias en 'frentes_encontrados': {comparison_result['diferencias_frentes']}"
                    )

            except Exception as e:
                st.error(f"❌ Error loading expected JSON: {str(e)}")


if __name__ == "__main__":
    main()
