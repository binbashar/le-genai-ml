import streamlit as st
import boto3
import json
import tempfile
import os
from datetime import datetime
import base64
import io
import time
import uuid
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la página
st.set_page_config(
    page_title="Speech-to-Speech AI Assistant",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS personalizado
st.markdown(
    """
<style>
    .main { 
        padding: 1rem; 
        max-width: 1200px;
        margin: 0 auto;
    }
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 2.5rem;
        font-size: 1rem;
        font-weight: 600;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 4px solid;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
    }
    .assistant-message {
        background-color: #f3e5f5;
        border-left-color: #9c27b0;
    }
    .audio-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin: 1rem 0;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 10px;
    }
    .step {
        flex: 1;
        text-align: center;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0 0.25rem;
    }
    .step.active {
        background-color: #4caf50;
        color: white;
    }
    .step.completed {
        background-color: #2196f3;
        color: white;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def init_aws_clients():
    """Inicializa todos los clientes AWS necesarios"""
    try:
        region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        clients = {
            "transcribe": boto3.client("transcribe", region_name=region),
            "bedrock": boto3.client("bedrock-runtime", region_name=region),
            "polly": boto3.client("polly", region_name=region),
            "s3": boto3.client("s3", region_name=region),
        }

        logger.info(f"Clientes AWS inicializados en región {region}")
        return clients

    except Exception as e:
        st.error(f"Error al inicializar clientes AWS: {str(e)}")
        logger.error(f"Error AWS: {e}")
        return None


def upload_audio_to_s3(audio_file, s3_client):
    """Sube audio a S3 para Transcribe"""
    try:
        bucket_name = f"speech-to-speech-temp-{uuid.uuid4().hex[:8]}"
        key = f"audio/{uuid.uuid4().hex}.wav"

        # Crear bucket temporal
        try:
            s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"Bucket creado: {bucket_name}")
        except ClientError as e:
            if e.response["Error"]["Code"] != "BucketAlreadyExists":
                raise e

        # Subir archivo
        audio_file.seek(0)
        s3_client.upload_fileobj(audio_file, bucket_name, key)

        s3_uri = f"s3://{bucket_name}/{key}"
        logger.info(f"Audio subido a: {s3_uri}")

        return s3_uri, bucket_name, key

    except Exception as e:
        logger.error(f"Error subiendo a S3: {e}")
        raise e


def transcribe_audio(s3_uri, transcribe_client):
    """Transcribe audio usando AWS Transcribe"""
    try:
        job_name = f"transcribe-job-{uuid.uuid4().hex[:8]}"

        # Iniciar job de transcripción
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": s3_uri},
            MediaFormat="wav",
            LanguageCode="es-ES",
        )

        logger.info(f"Job de transcripción iniciado: {job_name}")

        # Esperar a que termine
        max_wait = 120  # 2 minutos máximo
        wait_time = 0

        while wait_time < max_wait:
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )

            status = response["TranscriptionJob"]["TranscriptionJobStatus"]

            if status == "COMPLETED":
                # Obtener transcripción
                transcript_uri = response["TranscriptionJob"]["Transcript"][
                    "TranscriptFileUri"
                ]

                # Descargar resultado
                import requests

                transcript_response = requests.get(transcript_uri)
                transcript_data = transcript_response.json()

                transcript = transcript_data["results"]["transcripts"][0]["transcript"]
                logger.info(f"Transcripción completada: {transcript[:100]}...")

                return transcript

            elif status == "FAILED":
                raise Exception("Transcripción falló")

            time.sleep(5)
            wait_time += 5

        raise Exception("Timeout en transcripción")

    except Exception as e:
        logger.error(f"Error en transcripción: {e}")
        raise e


def generate_response_with_claude(transcript, bedrock_client, system_prompt=""):
    """Genera respuesta usando Claude"""
    try:
        # Intentar diferentes modelos disponibles
        models_to_try = [
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0",  # Inference profile
            "anthropic.claude-3-5-sonnet-20241022-v2:0",  # Directo
            "amazon.nova-pro-v1:0",  # Nova Pro como alternativa
            "amazon.nova-lite-v1:0",  # Nova Lite como fallback
            "anthropic.claude-3-sonnet-20240229-v1:0",  # Claude 3 Sonnet
        ]

        last_error = None

        for model_id in models_to_try:
            try:
                logger.info(f"Intentando con modelo: {model_id}")

                if model_id.startswith("amazon.nova"):
                    # Formato para modelos Nova
                    request_body = {
                        "messages": [
                            {"role": "user", "content": [{"text": transcript}]}
                        ],
                        "system": [
                            {
                                "text": (
                                    system_prompt
                                    if system_prompt
                                    else """Eres un asistente de voz amigable en español. 
                        Responde de manera natural, clara y concisa. Mantén un tono conversacional y cálido.
                        Tus respuestas deben ser apropiadas para ser leídas en voz alta."""
                                )
                            }
                        ],
                        "inferenceConfig": {
                            "maxTokens": 300,
                            "temperature": 0.7,
                            "topP": 0.9,
                        },
                    }
                else:
                    # Formato para modelos Claude
                    request_body = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 300,
                        "temperature": 0.7,
                        "system": (
                            system_prompt
                            if system_prompt
                            else """Eres un asistente de voz amigable en español. 
                        Responde de manera natural, clara y concisa. Mantén un tono conversacional y cálido.
                        Tus respuestas deben ser apropiadas para ser leídas en voz alta."""
                        ),
                        "messages": [{"role": "user", "content": transcript}],
                    }

                response = bedrock_client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(request_body),
                )

                response_body = json.loads(response["body"].read())

                if model_id.startswith("amazon.nova"):
                    # Extraer respuesta de Nova
                    text_response = response_body["output"]["message"]["content"][0][
                        "text"
                    ]
                else:
                    # Extraer respuesta de Claude
                    text_response = response_body["content"][0]["text"]

                logger.info(f"✅ Modelo exitoso: {model_id}")
                logger.info(f"Respuesta: {text_response[:100]}...")
                return text_response

            except ClientError as e:
                last_error = e
                logger.warning(
                    f"❌ Modelo {model_id} falló: {e.response['Error']['Code']}"
                )
                continue

        # Si todos los modelos fallaron
        raise last_error if last_error else Exception("No hay modelos disponibles")

    except Exception as e:
        logger.error(f"Error con modelos de IA: {e}")
        raise e


def synthesize_speech(text, polly_client, voice_id="Lupe"):
    """Sintetiza texto a voz usando AWS Polly"""
    try:
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=voice_id,
            Engine="neural",
            LanguageCode="es-ES",
        )

        # Obtener audio
        audio_data = response["AudioStream"].read()
        logger.info(f"Audio sintetizado: {len(audio_data)} bytes")

        return audio_data

    except Exception as e:
        logger.error(f"Error con Polly: {e}")
        raise e


def cleanup_s3_resources(s3_client, bucket_name, key):
    """Limpia recursos temporales de S3"""
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=key)
        s3_client.delete_bucket(Bucket=bucket_name)
        logger.info("Recursos S3 limpiados")
    except Exception as e:
        logger.error(f"Error limpiando S3: {e}")


def process_speech_to_speech(audio_file, clients, system_prompt=""):
    """Pipeline completo de Speech-to-Speech"""

    steps = [
        "🎵 Subir audio",
        "🎤 Transcribir",
        "🧠 Generar respuesta",
        "🗣️ Sintetizar voz",
    ]
    current_step = 0

    # Mostrar indicador de progreso
    step_container = st.empty()

    def update_steps(current):
        step_html = '<div class="step-indicator">'
        for i, step in enumerate(steps):
            if i < current:
                step_class = "step completed"
            elif i == current:
                step_class = "step active"
            else:
                step_class = "step"
            step_html += f'<div class="{step_class}">{step}</div>'
        step_html += "</div>"
        step_container.markdown(step_html, unsafe_allow_html=True)

    try:
        # Paso 1: Subir a S3
        update_steps(0)
        s3_uri, bucket_name, key = upload_audio_to_s3(audio_file, clients["s3"])

        # Paso 2: Transcribir
        update_steps(1)
        transcript = transcribe_audio(s3_uri, clients["transcribe"])

        # Paso 3: Generar respuesta
        update_steps(2)
        response_text = generate_response_with_claude(
            transcript, clients["bedrock"], system_prompt
        )

        # Paso 4: Sintetizar
        update_steps(3)
        response_audio = synthesize_speech(response_text, clients["polly"])

        # Limpiar recursos
        cleanup_s3_resources(clients["s3"], bucket_name, key)

        # Mostrar completado
        update_steps(4)

        return transcript, response_text, response_audio

    except Exception as e:
        st.error(f"Error en el pipeline: {str(e)}")
        return None, None, None


def main():
    # Header
    st.markdown(
        """
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="color: #667eea; font-size: 2.5rem;">
            🎙️ Speech-to-Speech AI Chat
        </h1>
        <p style="color: #666; font-size: 1.1rem;">
            Conversación por voz usando Binbash Speech2Speech Assistant
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Inicializar clientes AWS
    clients = init_aws_clients()
    if not clients:
        st.error("❌ No se pudieron inicializar los clientes AWS")
        st.stop()

    # Estado de la aplicación
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing" not in st.session_state:
        st.session_state.processing = False

    # Área principal
    st.markdown(
        """
    <div class="audio-container">
        <h3>🎤 Carga tu archivo de audio</h3>
        <p>El sistema transcribirá tu voz, generará una respuesta con IA, y la convertirá a audio</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Layout en columnas
    col1, col2 = st.columns([2, 1])

    with col1:
        # File uploader
        uploaded_file = st.file_uploader(
            "Selecciona un archivo de audio:",
            type=["wav", "mp3", "m4a"],
            disabled=st.session_state.processing,
            help="WAV es el formato más confiable para transcripción",
        )

        if uploaded_file is not None:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.info(f"📁 **Archivo**: {uploaded_file.name} ({file_size_mb:.2f} MB)")
            st.audio(uploaded_file)

    with col2:
        # Configuración
        st.markdown("### ⚙️ Configuración")

        personalities = {
            "Conversacional": "Responde de manera natural y amigable, como una conversación casual.",
            "Profesional": "Mantén un tono profesional pero accesible y servicial.",
            "Educativo": "Explica las cosas de manera clara y pedagógica.",
            "Creativo": "Sé imaginativo y original en tus respuestas.",
            "Motivacional": "Responde de manera inspiradora y positiva.",
        }

        selected_personality = st.selectbox(
            "Personalidad:",
            list(personalities.keys()),
            disabled=st.session_state.processing,
        )

        # Selección de voz
        voices = {
            "Lupe": "Voz femenina española",
            "Enrique": "Voz masculina española",
            "Conchita": "Voz femenina española alternativa",
            "Lucia": "Voz femenina neutra",
        }

        selected_voice = st.selectbox(
            "Voz para respuesta:",
            list(voices.keys()),
            disabled=st.session_state.processing,
            help="Voces disponibles en español",
        )

        custom_instructions = st.text_area(
            "Instrucciones adicionales:",
            placeholder="Instrucciones específicas...",
            disabled=st.session_state.processing,
            height=80,
        )

    # Botón de procesamiento
    if uploaded_file is not None:
        if st.button(
            "🚀 Procesar Speech-to-Speech",
            type="primary",
            disabled=st.session_state.processing,
            use_container_width=True,
        ):
            st.session_state.processing = True

            # Preparar prompt
            system_prompt = (
                custom_instructions
                if custom_instructions.strip()
                else personalities[selected_personality]
            )

            # Crear copia del archivo para procesamiento
            try:
                uploaded_file.seek(0)
                file_copy = io.BytesIO(uploaded_file.read())
                file_copy.name = uploaded_file.name
            except Exception as e:
                st.error(f"Error leyendo archivo: {e}")
                st.session_state.processing = False
                st.stop()

            # Procesar
            with st.spinner("Procesando audio..."):
                transcript, response_text, response_audio = process_speech_to_speech(
                    file_copy, clients, system_prompt
                )

                if transcript and response_text and response_audio:
                    # Agregar al historial
                    # Crear copia del archivo para evitar que se cierre
                    audio_copy = io.BytesIO()
                    uploaded_file.seek(0)
                    audio_copy.write(uploaded_file.read())
                    audio_copy.seek(0)

                    st.session_state.messages.append(
                        {
                            "role": "user",
                            "audio_file": audio_copy,
                            "audio_name": uploaded_file.name,
                            "transcript": transcript,
                            "timestamp": datetime.now(),
                        }
                    )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "text": response_text,
                            "audio_data": response_audio,
                            "voice": selected_voice,
                            "timestamp": datetime.now(),
                        }
                    )

                    st.success("🎉 ¡Speech-to-Speech completado!")

                else:
                    st.error("❌ Error en el procesamiento")

            st.session_state.processing = False
            st.rerun()

    # Mostrar historial
    if st.session_state.messages:
        st.markdown("---")
        st.markdown("### 💬 Historial de Conversación")

        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f"""
                <div class="chat-message user-message">
                    <strong>🎤 Tu mensaje ({msg['timestamp'].strftime('%H:%M:%S')})</strong>
                    <br><strong>Archivo:</strong> {msg.get('audio_name', 'audio.wav')}
                    <br><em>"{msg['transcript']}"</em>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Mostrar audio del usuario
                if "audio_data" in msg and msg["audio_data"] is not None:
                    st.audio(msg["audio_data"], format="audio/wav")

                    # Botón de descarga para audio original
                    st.download_button(
                        label="💾 Descargar tu audio",
                        data=msg["audio_data"],
                        file_name=f"tu_mensaje_{msg['timestamp'].strftime('%H%M%S')}.wav",
                        mime="audio/wav",
                        key=f"download_user_{msg['timestamp'].timestamp()}",
                    )
                else:
                    st.info(
                        f"📁 Audio original: {msg.get('audio_name', 'archivo de audio')}"
                    )

            else:
                st.markdown(
                    f"""
                <div class="chat-message assistant-message">
                    <strong>🤖 IA ({msg['timestamp'].strftime('%H:%M:%S')}) - Voz: {msg['voice']}</strong>
                    <br><em>"{msg['text']}"</em>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Mostrar audio de respuesta
                if "audio_data" in msg and msg["audio_data"] is not None:
                    st.audio(msg["audio_data"], format="audio/mp3")

                    # Botón de descarga
                    st.download_button(
                        label="💾 Descargar respuesta",
                        data=msg["audio_data"],
                        file_name=f"respuesta_ia_{msg['timestamp'].strftime('%H%M%S')}.mp3",
                        mime="audio/mp3",
                        key=f"download_assistant_{msg['timestamp'].timestamp()}",
                    )

        if st.button("🗑️ Limpiar Historial"):
            st.session_state.messages = []
            st.rerun()

    # Información
    with st.expander("ℹ️ Cómo funciona este sistema"):
        st.markdown("""
        ### 🔄 Pipeline Speech-to-Speech:
        
        1. **🎵 Subida**: Tu audio se sube a S3 temporalmente
        2. **🎤 Transcripción**: AWS Transcribe convierte tu voz a texto
        3. **🧠 IA**: Claude 3.5 Sonnet genera una respuesta inteligente
        4. **🗣️ Síntesis**: AWS Polly convierte la respuesta a voz
        
        ### 📋 Servicios utilizados:
        - **AWS Transcribe**: Speech-to-Text
        - **Claude 3.5 Sonnet**: Generación de respuestas
        - **AWS Polly**: Text-to-Speech neural
        - **S3**: Almacenamiento temporal
        
        ### ⚡ Notas:
        - Los archivos temporales se eliminan automáticamente
        - Recomendado: archivos WAV de buena calidad
        - El procesamiento toma ~10-30 segundos
        """)


if __name__ == "__main__":
    main()
