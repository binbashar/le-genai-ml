import streamlit as st
import boto3
import json
import tempfile
import os
from datetime import datetime
import base64
import io
import wave
import struct
import numpy as np
from pathlib import Path
import threading
import queue
import sounddevice as sd
import soundfile as sf
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import av

# Configuración de la página
st.set_page_config(
    page_title="Nova Sonic Voice Chat",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS personalizado para una interfaz más amigable
st.markdown(
    """
<style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        height: 3rem;
        font-size: 1.2rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 10px rgba(0,0,0,0.2);
    }
    .recording-button {
        background-color: #ff4444 !important;
        color: white !important;
        animation: pulse 1.5s infinite;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        animation: fadeIn 0.5s;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
    }
    .assistant-message {
        background-color: #F3E5F5;
        border-left: 4px solid #9C27B0;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .audio-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin: 2rem 0;
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 0.5rem;
        animation: pulse 1.5s infinite;
    }
    .status-ready { background-color: #4CAF50; }
    .status-processing { background-color: #FF9800; }
    .status-error { background-color: #F44336; }
    
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.1); }
        100% { opacity: 1; transform: scale(1); }
    }
    
    .mic-button {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border: none;
        color: white;
        padding: 2rem;
        border-radius: 50%;
        cursor: pointer;
        font-size: 3rem;
        transition: all 0.3s;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    
    .mic-button:hover {
        transform: scale(1.1);
        box-shadow: 0 15px 30px rgba(0,0,0,0.3);
    }
    
    .mic-button.recording {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        animation: pulse 1s infinite;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Clase para procesar audio del micrófono
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_buffer = []

    def recv(self, frame):
        audio = frame.to_ndarray()
        self.audio_buffer.extend(audio.flatten())
        return frame


# Inicializar cliente de Bedrock
@st.cache_resource
def init_bedrock_client():
    """Inicializa el cliente de Amazon Bedrock"""
    try:
        bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )
        return bedrock
    except Exception as e:
        st.error(f"Error al inicializar Bedrock: {str(e)}")
        return None


# Función para convertir audio a formato base64
def audio_to_base64(audio_data):
    """Convierte datos de audio a base64 para Nova Sonic"""
    if isinstance(audio_data, bytes):
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    else:
        # Si son datos numpy, convertir a bytes WAV
        audio_bytes = io.BytesIO()
        sf.write(audio_bytes, audio_data, 16000, format="WAV")
        audio_bytes.seek(0)
        audio_base64 = base64.b64encode(audio_bytes.read()).decode("utf-8")
    return audio_base64


# Función para grabar audio usando sounddevice
def record_audio_simple(duration=5, sample_rate=16000):
    """Graba audio del micrófono por una duración específica"""
    st.info(f"🎤 Grabando por {duration} segundos...")

    # Grabar audio
    recording = sd.rec(
        int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16"
    )
    sd.wait()  # Esperar hasta que termine la grabación

    # Convertir a bytes WAV
    audio_bytes = io.BytesIO()
    sf.write(audio_bytes, recording, sample_rate, format="WAV")
    audio_bytes.seek(0)

    return audio_bytes.read()


# Función principal de Speech-to-Speech con Nova Sonic
def process_speech_to_speech(audio_data, bedrock_client, system_prompt=""):
    """Procesa audio con Nova Sonic para respuesta Speech-to-Speech"""

    try:
        # Convertir audio a base64
        audio_base64 = audio_to_base64(audio_data)

        # Preparar el request para Nova Sonic
        model_id = "amazon.nova-sonic-v1:0"  # Modelo Nova Sonic

        request_body = {
            "schemaVersion": "messages-v1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "audio": {
                                "format": "audio/wav",
                                "source": {"bytes": audio_base64},
                            }
                        }
                    ],
                }
            ],
            "system": [
                {
                    "text": system_prompt
                    if system_prompt
                    else """Eres un asistente de voz amigable y conversacional. 
                    Responde de manera natural y empática. Mantén un tono cálido y cercano.
                    Tus respuestas deben ser claras y concisas."""
                }
            ],
            "inferenceConfig": {
                "voice": {
                    "voiceId": "nova-1",  # Voz de Nova Sonic
                    "languageCode": "es-ES",  # Español
                    "engine": "neural",
                },
                "max_new_tokens": 500,
                "temperature": 0.7,
                "top_p": 0.9,
            },
        }

        # Invocar Nova Sonic
        response = bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )

        # Procesar la respuesta
        response_body = json.loads(response["body"].read())

        # Extraer audio y transcripción
        audio_response = None
        transcript_text = ""

        if "output" in response_body:
            output = response_body["output"]
            if "message" in output:
                message = output["message"]
                # Buscar contenido de audio en la respuesta
                for content in message.get("content", []):
                    if "audio" in content:
                        audio_data = content["audio"]["source"]["bytes"]
                        audio_response = base64.b64decode(audio_data)
                    if "text" in content:
                        transcript_text = content["text"]

        # Si no encontramos en el formato anterior, buscar en formato alternativo
        if not audio_response and "outputAudio" in response_body:
            audio_response = base64.b64decode(response_body["outputAudio"])
            transcript_text = response_body.get("outputTranscript", "")

        return audio_response, transcript_text

    except Exception as e:
        st.error(f"Error en Nova Sonic: {str(e)}")
        st.error(f"Detalles: {type(e).__name__}")
        return None, None


# Interfaz principal
def main():
    # Header con animación
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
        <div style="text-align: center;">
            <h1 style="color: #667eea; font-size: 3rem; margin-bottom: 0;">
                🎙️ Nova Sonic Voice Chat
            </h1>
            <p style="color: #666; font-size: 1.2rem;">
                Habla con IA usando solo tu voz
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Verificar configuración
    if "AWS_ACCESS_KEY_ID" not in os.environ:
        st.warning("⚠️ Configura tus credenciales AWS primero")
        with st.expander("Ver instrucciones"):
            st.code(
                """
export AWS_ACCESS_KEY_ID=tu_access_key
export AWS_SECRET_ACCESS_KEY=tu_secret_key
export AWS_DEFAULT_REGION=us-east-1
            """
            )
        return

    # Inicializar cliente
    bedrock = init_bedrock_client()
    if not bedrock:
        return

    # Estado de la aplicación
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "recording" not in st.session_state:
        st.session_state.recording = False

    # Contenedor principal
    main_container = st.container()

    with main_container:
        # Área de chat
        chat_container = st.container()

        # Input de audio
        st.markdown(
            """
        <div class="audio-container">
            <h2>🎤 Habla con Nova Sonic</h2>
            <p>Elige cómo quieres enviar tu mensaje de voz</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Tabs para diferentes métodos de input
        tab1, tab2, tab3 = st.tabs(
            ["🎙️ Grabar ahora", "📁 Subir archivo", "⚙️ Configuración"]
        )

        with tab1:
            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)

                # Selector de duración
                duration = st.slider(
                    "Duración de grabación (segundos)",
                    min_value=2,
                    max_value=30,
                    value=5,
                    step=1,
                )

                # Botón de grabación
                if st.button(
                    "🎤 Presiona para grabar"
                    if not st.session_state.recording
                    else "⏹️ Detener grabación",
                    type="primary",
                    use_container_width=True,
                    key="record_button",
                ):
                    if not st.session_state.recording:
                        st.session_state.recording = True

                        # Grabar audio
                        with st.spinner(
                            f"🔴 Grabando por {duration} segundos... ¡Habla ahora!"
                        ):
                            try:
                                audio_data = record_audio_simple(duration=duration)

                                # Procesar con Nova Sonic
                                st.info("🎧 Procesando tu mensaje...")
                                audio_response, transcript = process_speech_to_speech(
                                    audio_data,
                                    bedrock,
                                    st.session_state.get("custom_prompt", ""),
                                )

                                if audio_response and transcript:
                                    # Agregar al historial
                                    st.session_state.messages.append(
                                        {
                                            "role": "user",
                                            "audio": audio_data,
                                            "timestamp": datetime.now(),
                                        }
                                    )

                                    st.session_state.messages.append(
                                        {
                                            "role": "assistant",
                                            "audio": audio_response,
                                            "transcript": transcript,
                                            "timestamp": datetime.now(),
                                        }
                                    )

                                    st.success("✅ ¡Respuesta generada!")
                                    st.balloons()

                            except Exception as e:
                                st.error(f"Error al grabar: {str(e)}")
                                st.info("Asegúrate de permitir el acceso al micrófono")

                            finally:
                                st.session_state.recording = False
                                st.rerun()

                # Alternativa: WebRTC para grabación en tiempo real
                st.markdown("---")
                st.markdown("### 🎯 O usa grabación en tiempo real")

                webrtc_ctx = webrtc_streamer(
                    key="speech",
                    mode=WebRtcMode.SENDONLY,
                    audio_processor_factory=AudioProcessor,
                    media_stream_constraints={"audio": True, "video": False},
                    async_processing=True,
                )

                if webrtc_ctx.audio_processor:
                    if st.button("💾 Procesar grabación WebRTC"):
                        audio_data = np.array(webrtc_ctx.audio_processor.audio_buffer)
                        if len(audio_data) > 0:
                            # Procesar audio...
                            st.info("Procesando audio WebRTC...")

                st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            audio_file = st.file_uploader(
                "Sube un archivo de audio",
                type=["wav", "mp3", "m4a"],
                help="Formatos soportados: WAV, MP3, M4A",
            )

            if audio_file:
                st.audio(audio_file, format=f'audio/{audio_file.type.split("/")[-1]}')

                if st.button("🚀 Procesar archivo", type="primary"):
                    with st.spinner("🎧 Procesando tu mensaje..."):
                        audio_data = audio_file.read()
                        audio_response, transcript = process_speech_to_speech(
                            audio_data,
                            bedrock,
                            st.session_state.get("custom_prompt", ""),
                        )

                        if audio_response and transcript:
                            # Agregar al historial
                            st.session_state.messages.append(
                                {
                                    "role": "user",
                                    "audio": audio_data,
                                    "timestamp": datetime.now(),
                                }
                            )

                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "audio": audio_response,
                                    "transcript": transcript,
                                    "timestamp": datetime.now(),
                                }
                            )

                            st.success("✅ ¡Respuesta generada!")
                            st.rerun()

        with tab3:
            # Personalización del asistente
            personality = st.selectbox(
                "Tipo de asistente",
                ["Amigable", "Profesional", "Creativo", "Educativo", "Motivacional"],
            )

            custom_prompt = st.text_area(
                "Instrucciones personalizadas (opcional)",
                placeholder="Ej: Responde como un coach motivacional...",
                height=100,
            )

            if st.button("💾 Guardar configuración"):
                prompts = {
                    "Amigable": "Eres un amigo cercano, cálido y empático. Usa un tono casual y cercano.",
                    "Profesional": "Eres un asistente profesional. Mantén un tono formal pero accesible.",
                    "Creativo": "Eres muy creativo e imaginativo. Usa metáforas y sé original en tus respuestas.",
                    "Educativo": "Eres un profesor paciente. Explica las cosas de forma clara y didáctica.",
                    "Motivacional": "Eres un coach motivacional. Inspira y anima en cada respuesta.",
                }

                st.session_state.custom_prompt = (
                    custom_prompt
                    if custom_prompt
                    else prompts.get(personality, prompts["Amigable"])
                )
                st.success("✅ Configuración guardada")

        # Mostrar historial de conversación
        with chat_container:
            st.markdown("### 💬 Conversación")

            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(
                        f"""
                    <div class="chat-message user-message">
                        <span class="status-indicator status-ready"></span>
                        <strong>Tú ({msg['timestamp'].strftime('%H:%M')})</strong>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    st.audio(msg["audio"], format="audio/wav")

                else:  # assistant
                    st.markdown(
                        f"""
                    <div class="chat-message assistant-message">
                        <span class="status-indicator status-ready"></span>
                        <strong>Nova Sonic ({msg['timestamp'].strftime('%H:%M')})</strong>
                        <p style="margin-top: 0.5rem;">{msg.get('transcript', '')}</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    st.audio(msg["audio"], format="audio/wav")

            if not st.session_state.messages:
                st.info("👋 ¡Hola! Graba un audio o sube un archivo para comenzar.")

    # Sidebar con información
    with st.sidebar:
        st.markdown("### 📊 Estadísticas")
        st.metric("Mensajes", len(st.session_state.messages))

        if st.button("🗑️ Limpiar conversación"):
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.markdown("### 🎯 Características")
        st.markdown(
            """
        - ✅ Grabación desde micrófono
        - ✅ Speech-to-Speech directo
        - ✅ Respuestas naturales
        - ✅ Múltiples personalidades
        - ✅ Historial de conversación
        """
        )

        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.info(
            """
        - Habla claramente
        - El micrófono debe estar habilitado
        - Prueba diferentes duraciones
        - Los audios cortos funcionan mejor
        """
        )


if __name__ == "__main__":
    main()
