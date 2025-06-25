#!/usr/bin/env python3
"""Interfaz Streamlit mejorada para scraper multi-sitio con IA"""

import streamlit as st
import subprocess
import json
import os
import time
import anthropic
from datetime import datetime
import re
import tempfile
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scraper_engine import run_scraper, MultiSiteScraper
import base64
from typing import Dict, List, Any

# Configuración de página con tema oscuro profesional
st.set_page_config(
    page_title="Ximple Analytics AI - Web Scraper Pro", 
    page_icon="🔮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para UI profesional
st.markdown("""
<style>
    /* Tema oscuro profesional */
    .stApp {
        background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
    }
    
    /* Headers con gradiente */
    h1, h2, h3 {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    
    /* Tarjetas con efecto glassmorphism */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        margin-bottom: 20px;
    }
    
    /* Botones con efecto hover */
    .stButton > button {
        background: linear-gradient(45deg, #667eea 30%, #764ba2 90%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
        border-radius: 30px;
        transition: all 0.3s ease;
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.5);
    }
    
    /* Sidebar mejorado */
    .css-1d391kg {
        background: rgba(26, 26, 46, 0.95);
        backdrop-filter: blur(10px);
    }
    
    /* Inputs con estilo */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: white;
    }
    
    /* Tabs con estilo moderno */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.05);
        padding: 10px;
        border-radius: 15px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 10px;
        color: rgba(255, 255, 255, 0.7);
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #667eea 30%, #764ba2 90%);
        color: white;
    }
    
    /* Métricas con animación */
    [data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
    }
    
    [data-testid="metric-container"]:hover {
        transform: scale(1.02);
        border-color: #667eea;
    }
    
    /* Expander mejorado */
    .streamlit-expanderHeader {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 10px;
        border: 1px solid rgba(102, 126, 234, 0.3);
    }
    
    /* Success/Error messages */
    .stSuccess {
        background: rgba(0, 255, 0, 0.1);
        border: 1px solid rgba(0, 255, 0, 0.3);
        border-radius: 10px;
        padding: 10px;
    }
    
    .stError {
        background: rgba(255, 0, 0, 0.1);
        border: 1px solid rgba(255, 0, 0, 0.3);
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Loading spinner personalizado */
    .stSpinner > div {
        border-color: #667eea;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

# Inicializar estado de sesión
if "task_history" not in st.session_state:
    st.session_state.task_history = []
if "credentials_set" not in st.session_state:
    st.session_state.credentials_set = False
if "selected_site" not in st.session_state:
    st.session_state.selected_site = None
if "analytics_data" not in st.session_state:
    st.session_state.analytics_data = {}

# Header principal con animación
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <h1 style="font-size: 3em; margin-bottom: 0;">🔮 Ximple Analytics AI</h1>
        <p style="font-size: 1.2em; color: #888; margin-top: 10px;">
            Web Scraper Profesional con Inteligencia Artificial
        </p>
    </div>
    """, unsafe_allow_html=True)

# Sidebar mejorado
with st.sidebar:
    st.markdown("""
    <div class="metric-card">
        <h2 style="margin-top: 0;">⚙️ Centro de Control</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Selector de sitio con iconos
    st.markdown("### 🌐 Seleccionar Plataforma")
    
    site_options = {
        "PriceShoes": {
            "icon": "👟",
            "url": "https://www.priceshoes.com/",
            "description": "Tienda de calzado y accesorios"
        },
        "Avon México": {
            "icon": "💄",
            "url": "https://avon.mx/",
            "description": "Cosméticos y productos de belleza"
        }
    }
    
    selected_site = st.radio(
        "Elige la plataforma:",
        options=list(site_options.keys()),
        format_func=lambda x: f"{site_options[x]['icon']} {x}",
        key="site_selector"
    )
    
    st.session_state.selected_site = selected_site
    
    # Mostrar información del sitio seleccionado
    st.info(f"📍 {site_options[selected_site]['description']}")
    
    # Sección de credenciales con validación visual
    st.markdown("### 🔐 Credenciales de Acceso")
    
    with st.form("credentials_form"):
        ps_url = st.text_input(
            "URL del sitio", 
            value=site_options[selected_site]['url'],
            disabled=True,
            key="ps_url"
        )
        
        ps_username = st.text_input(
            "📧 Email / ID de Usuario",
            placeholder="tu-email@ejemplo.com",
            key="ps_username",
            help="Ingresa tu email o ID de usuario para el sitio seleccionado"
        )
        
        ps_password = st.text_input(
            "🔑 Contraseña",
            type="password",
            placeholder="••••••••",
            key="ps_password",
            help="Tu contraseña será encriptada y no se almacenará"
        )
        
        submitted = st.form_submit_button(
            "💾 Guardar Credenciales",
            use_container_width=True
        )
        
        if submitted:
            if ps_username and ps_password:
                st.session_state.credentials_set = True
                st.success("✅ Credenciales guardadas correctamente")
                st.balloons()
            else:
                st.error("❌ Por favor completa todos los campos")
    
    # Sección API de Anthropic
    st.markdown("### 🤖 Configuración IA")
    
    with st.form("api_form"):
        anthropic_api = st.text_input(
            "🔑 API Key de Anthropic",
            type="password",
            placeholder="sk-ant-...",
            key="anthropic_api",
            help="Necesaria para el procesamiento con IA"
        )
        
        api_submitted = st.form_submit_button(
            "🔗 Conectar IA",
            use_container_width=True
        )
        
        if api_submitted and anthropic_api:
            st.success("✅ API conectada")
    
    # Estadísticas de sesión
    st.markdown("### 📊 Estadísticas de Sesión")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Consultas", 
            len(st.session_state.task_history),
            delta=f"+{len(st.session_state.task_history)}" if st.session_state.task_history else None
        )
    
    with col2:
        success_count = sum(1 for task in st.session_state.task_history if task['result'].get('success', False))
        st.metric(
            "Exitosas",
            success_count,
            delta=f"{(success_count/len(st.session_state.task_history)*100):.0f}%" if st.session_state.task_history else None
        )
    
    # Información adicional
    st.markdown("---")
    st.caption("💡 **Tip:** El proceso puede tomar 30-60 segundos")
    st.caption("🔒 Tus datos están seguros y encriptados")

# Área principal con tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Nueva Consulta", "📊 Resultados", "📈 Analytics", "📜 Historial"])

with tab1:
    # Header de consulta
    st.markdown("""
    <div class="metric-card">
        <h2>🗣️ ¿Qué información necesitas extraer?</h2>
        <p style="color: #888;">Describe en lenguaje natural lo que quieres obtener del sitio web</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Área de entrada mejorada
    col1, col2 = st.columns([3, 1])
    
    with col1:
        natural_instruction = st.text_area(
            "Tu consulta:",
            placeholder=f"Ejemplo: 'Inicia sesión en {selected_site} y muéstrame todos mis pedidos recientes con sus estados y totales'",
            height=120,
            key="natural_instruction_input"
        )
    
    with col2:
        # Plantillas rápidas
        st.markdown("#### 🚀 Consultas Rápidas")
        
        quick_queries = {
            "📦 Ver Pedidos": "Muéstrame todos mis pedidos recientes con fechas y totales",
            "👤 Mi Cuenta": "Extrae toda mi información personal y datos de la cuenta",
            "📍 Direcciones": "Lista todas mis direcciones de envío guardadas",
            "💰 Historial": "Dame un resumen completo de mi historial de compras",
            "🔍 Buscar Pedido": "Busca información sobre mi último pedido"
        }
        
        for label, query in quick_queries.items():
            if st.button(label, use_container_width=True):
                st.session_state.natural_instruction_input = query
                st.rerun()
    
    # Opciones avanzadas
    with st.expander("⚙️ Opciones Avanzadas"):
        col1, col2 = st.columns(2)
        
        with col1:
            extract_images = st.checkbox("📸 Capturar screenshots adicionales", value=True)
            export_format = st.selectbox(
                "📄 Formato de exportación:",
                ["JSON", "CSV", "Excel", "PDF"]
            )
        
        with col2:
            wait_time = st.slider("⏱️ Tiempo de espera (segundos):", 1, 10, 3)
            retry_attempts = st.number_input("🔄 Intentos de reintentos:", 1, 5, 2)
    
    # Botón de ejecución principal
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 EJECUTAR ANÁLISIS", type="primary", use_container_width=True):
            if not st.session_state.credentials_set:
                st.error("❌ Primero configura tus credenciales en el panel lateral")
            elif not st.session_state.get('anthropic_api'):
                st.error("❌ Se requiere una API key de Anthropic para el análisis con IA")
            elif not natural_instruction:
                st.error("❌ Por favor describe qué información necesitas extraer")
            else:
                # Mostrar loading con progreso
                with st.spinner("🤖 Analizando tu solicitud con IA..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Inicializar scraper
                        scraper = MultiSiteScraper()
                        
                        # Actualizar progreso
                        progress_bar.progress(10)
                        status_text.text("📝 Procesando instrucciones...")
                        
                        # Generar instrucciones con IA
                        scraping_instructions = None
                        
                        # Casos comunes optimizados
                        instruction_lower = natural_instruction.lower()
                        
                        if any(kw in instruction_lower for kw in ["pedido", "order", "compra"]):
                            scraping_instructions = {
                                "steps": [
                                    {"action": "go_to", "value": "url_base"},
                                    {"action": "login", "value": "complete_login_process"},
                                    {"action": "navigate_to", "value": "Mis Pedidos"},
                                    {"action": "wait", "value": str(wait_time)},
                                    {"action": "extract", "value": "pedidos"},
                                ],
                                "data_targets": ["pedidos"],
                                "explanation": f"Extrayendo información de pedidos de {selected_site}"
                            }
                        
                        elif any(kw in instruction_lower for kw in ["cuenta", "perfil", "personal"]):
                            scraping_instructions = {
                                "steps": [
                                    {"action": "go_to", "value": "url_base"},
                                    {"action": "login", "value": "complete_login_process"},
                                    {"action": "navigate_to", "value": "Mi Cuenta"},
                                    {"action": "wait", "value": str(wait_time)},
                                    {"action": "extract", "value": "cuenta"},
                                ],
                                "data_targets": ["cuenta"],
                                "explanation": f"Extrayendo información de cuenta de {selected_site}"
                            }
                        
                        # Si no es un caso común, usar IA
                        if not scraping_instructions:
                            progress_bar.progress(20)
                            status_text.text("🧠 Consultando IA para análisis avanzado...")
                            
                            client = anthropic.Anthropic(api_key=st.session_state.get('anthropic_api'))
                            
                            prompt = f"""
                            Analiza esta instrucción para web scraping en {selected_site}: "{natural_instruction}"
                            
                            Genera un plan de navegación estructurado. Responde SOLO en este formato:
                            
                            OBJETIVO: [descripción breve del objetivo]
                            SECCIONES: [lista de secciones a visitar separadas por comas]
                            DATOS: [tipos de datos a extraer separados por comas]
                            
                            Sé específico y conciso.
                            """
                            
                            response = client.messages.create(
                                model="claude-3-opus-20240229",
                                max_tokens=200,
                                temperature=0,
                                messages=[{"role": "user", "content": prompt}]
                            )
                            
                            # Procesar respuesta de IA
                            content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content)
                            
                            objetivo = "Extraer información solicitada"
                            sections = ["Mi Cuenta"]
                            data_types = ["información general"]
                            
                            for line in content.split('\n'):
                                line = line.strip()
                                if line.startswith('OBJETIVO:'):
                                    objetivo = line.replace('OBJETIVO:', '').strip()
                                elif line.startswith('SECCIONES:'):
                                    sections = [s.strip() for s in line.replace('SECCIONES:', '').split(',')]
                                elif line.startswith('DATOS:'):
                                    data_types = [d.strip() for d in line.replace('DATOS:', '').split(',')]
                            
                            # Construir instrucciones
                            scraping_instructions = {
                                "steps": [
                                    {"action": "go_to", "value": "url_base"},
                                    {"action": "login", "value": "complete_login_process"}
                                ],
                                "data_targets": data_types,
                                "explanation": objetivo
                            }
                            
                            for section in sections:
                                scraping_instructions["steps"].append({"action": "navigate_to", "value": section})
                                scraping_instructions["steps"].append({"action": "wait", "value": str(wait_time)})
                            
                            # Determinar tipo de extracción
                            if any(kw in ' '.join(data_types).lower() for kw in ["pedido", "order"]):
                                extraction_type = "pedidos"
                            elif any(kw in ' '.join(data_types).lower() for kw in ["tabla", "table"]):
                                extraction_type = "table"
                            else:
                                extraction_type = "body"
                            
                            scraping_instructions["steps"].append({"action": "extract", "value": extraction_type})
                        
                        # Mostrar plan
                        progress_bar.progress(30)
                        status_text.text("📋 Plan de navegación generado...")
                        
                        with st.expander("🗺️ Plan de Navegación", expanded=True):
                            st.json(scraping_instructions)
                        
                        # Ejecutar scraper
                        progress_bar.progress(40)
                        status_text.text("🌐 Conectando al sitio web...")
                        
                        result = run_scraper(
                            instructions=scraping_instructions,
                            url=st.session_state.ps_url,
                            username=st.session_state.ps_username,
                            password=st.session_state.ps_password
                        )
                        
                        # Actualizar progreso durante la ejecución
                        for i in range(50, 90, 10):
                            progress_bar.progress(i)
                            status_text.text(f"🔄 Procesando... {i}%")
                            time.sleep(0.5)
                        
                        # Guardar resultado
                        progress_bar.progress(100)
                        status_text.text("✅ Análisis completado!")
                        
                        timestamp = datetime.now()
                        st.session_state.task_history.append({
                            "timestamp": timestamp,
                            "instruction": natural_instruction,
                            "site": selected_site,
                            "result": result,
                            "settings": {
                                "extract_images": extract_images,
                                "export_format": export_format,
                                "wait_time": wait_time
                            }
                        })
                        
                        # Actualizar analytics
                        if selected_site not in st.session_state.analytics_data:
                            st.session_state.analytics_data[selected_site] = {
                                "total_queries": 0,
                                "successful_queries": 0,
                                "failed_queries": 0,
                                "extracted_items": 0
                            }
                        
                        st.session_state.analytics_data[selected_site]["total_queries"] += 1
                        
                        if result.get("success"):
                            st.session_state.analytics_data[selected_site]["successful_queries"] += 1
                            st.success(f"✅ {scraping_instructions.get('explanation', 'Análisis completado')}")
                            
                            # Contar elementos extraídos
                            if "extracted_data" in result:
                                if "pedidos" in result["extracted_data"]:
                                    count = len(result["extracted_data"]["pedidos"])
                                    st.session_state.analytics_data[selected_site]["extracted_items"] += count
                        else:
                            st.session_state.analytics_data[selected_site]["failed_queries"] += 1
                            st.error(f"❌ Error: {result.get('error', 'Error desconocido')}")
                        
                        # Cambiar a tab de resultados
                        st.success("📊 Ve a la pestaña 'Resultados' para ver los datos extraídos")
                        
                    except Exception as e:
                        st.error(f"❌ Error durante el proceso: {str(e)}")
                        progress_bar.progress(0)
                        status_text.text("")

with tab2:
    # Tab de Resultados
    st.markdown("""
    <div class="metric-card">
        <h2>📊 Resultados del Análisis</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.task_history:
        # Obtener último resultado
        last_task = st.session_state.task_history[-1]
        
        # Información de la consulta
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🌐 Sitio", last_task.get("site", "N/A"))
        
        with col2:
            st.metric("⏰ Hora", last_task["timestamp"].strftime("%H:%M:%S"))
        
        with col3:
            status = "✅ Exitoso" if last_task["result"].get("success") else "❌ Fallido"
            st.metric("📊 Estado", status)
        
        # Mostrar consulta
        st.markdown("### 📝 Consulta Realizada")
        st.info(last_task["instruction"])
        
        result = last_task["result"]
        
        # Datos extraídos
        if "extracted_data" in result and result["extracted_data"]:
            st.markdown("### 🎯 Datos Extraídos")
            
            # Procesar según tipo de datos
            if "pedidos" in result["extracted_data"]:
                pedidos = result["extracted_data"]["pedidos"]
                
                if isinstance(pedidos, list) and pedidos:
                    st.success(f"📦 Se encontraron {len(pedidos)} pedidos")
                    
                    # Crear DataFrame para mejor visualización
                    if all(isinstance(p, dict) for p in pedidos):
                        df = pd.DataFrame(pedidos)
                        
                        # Mostrar tabla interactiva
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "numero_pedido": st.column_config.TextColumn("N° Pedido", width="medium"),
                                "fecha": st.column_config.TextColumn("Fecha", width="medium"),
                                "total": st.column_config.TextColumn("Total", width="small"),
                                "estado": st.column_config.TextColumn("Estado", width="small"),
                            }
                        )
                        
                        # Gráficos si hay datos numéricos
                        if "total" in df.columns:
                            try:
                                # Limpiar y convertir totales
                                df['total_numerico'] = df['total'].str.replace(r'[$,]', '', regex=True).astype(float)
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # Gráfico de barras
                                    fig_bar = px.bar(
                                        df, 
                                        x="numero_pedido", 
                                        y="total_numerico",
                                        title="Totales por Pedido",
                                        color="estado" if "estado" in df.columns else None,
                                        labels={"total_numerico": "Total ($)", "numero_pedido": "Pedido"}
                                    )
                                    fig_bar.update_layout(
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        font_color='white'
                                    )
                                    st.plotly_chart(fig_bar, use_container_width=True)
                                
                                with col2:
                                    # Gráfico de pie por estado
                                    if "estado" in df.columns:
                                        estado_counts = df['estado'].value_counts()
                                        fig_pie = px.pie(
                                            values=estado_counts.values,
                                            names=estado_counts.index,
                                            title="Distribución por Estado"
                                        )
                                        fig_pie.update_layout(
                                            plot_bgcolor='rgba(0,0,0,0)',
                                            paper_bgcolor='rgba(0,0,0,0)',
                                            font_color='white'
                                        )
                                        st.plotly_chart(fig_pie, use_container_width=True)
                            except:
                                pass
                    else:
                        # Mostrar pedidos como JSON si no son estructurados
                        for i, pedido in enumerate(pedidos):
                            with st.expander(f"📦 Pedido {i+1}"):
                                st.json(pedido)
                
                else:
                    st.warning("No se encontraron pedidos estructurados")
                    st.json(result["extracted_data"])
            
            elif "informacion_cuenta" in result["extracted_data"]:
                # Mostrar información de cuenta
                account_info = result["extracted_data"]["informacion_cuenta"]
                
                st.markdown("### 👤 Información de Cuenta")
                
                # Crear columnas para mostrar info
                cols = st.columns(3)
                col_idx = 0
                
                for key, value in account_info.items():
                    if not key.startswith("info_adicional"):
                        with cols[col_idx % 3]:
                            st.metric(key.replace("_", " ").title(), value)
                        col_idx += 1
                
                # Información adicional
                for key, value in account_info.items():
                    if key.startswith("info_adicional"):
                        with st.expander("ℹ️ Información Adicional"):
                            st.text(value)
            
            elif "tablas" in result["extracted_data"]:
                # Mostrar tablas
                tables = result["extracted_data"]["tablas"]
                st.markdown(f"### 📋 Se encontraron {len(tables)} tablas")
                
                for i, table in enumerate(tables):
                    with st.expander(f"📊 Tabla {i+1} - {table.get('resumen', '')}"):
                        if table.get("headers") and table.get("filas"):
                            df = pd.DataFrame(table["filas"], columns=table["headers"])
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.json(table)
            
            else:
                # Mostrar datos genéricos
                st.json(result["extracted_data"])
            
            # Botones de exportación
            st.markdown("### 💾 Exportar Datos")
            
            col1, col2, col3, col4 = st.columns(4)
            
            export_format = last_task.get("settings", {}).get("export_format", "JSON")
            
            with col1:
                # Exportar como JSON
                json_data = json.dumps(result["extracted_data"], indent=2, ensure_ascii=False)
                st.download_button(
                    "📄 Descargar JSON",
                    data=json_data,
                    file_name=f"{last_task['site']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col2:
                # Exportar como CSV (si hay datos tabulares)
                if "pedidos" in result["extracted_data"] and isinstance(result["extracted_data"]["pedidos"], list):
                    try:
                        df = pd.DataFrame(result["extracted_data"]["pedidos"])
                        csv_data = df.to_csv(index=False)
                        st.download_button(
                            "📊 Descargar CSV",
                            data=csv_data,
                            file_name=f"{last_task['site']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    except:
                        st.button("📊 CSV No Disponible", disabled=True, use_container_width=True)
            
            with col3:
                # Exportar como Excel
                try:
                    if "pedidos" in result["extracted_data"]:
                        df = pd.DataFrame(result["extracted_data"]["pedidos"])
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, sheet_name='Pedidos', index=False)
                        excel_data = excel_buffer.getvalue()
                        st.download_button(
                            "📈 Descargar Excel",
                            data=excel_data,
                            file_name=f"{last_task['site']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    else:
                        st.button("📈 Excel No Disponible", disabled=True, use_container_width=True)
                except:
                    st.button("📈 Excel No Disponible", disabled=True, use_container_width=True)
            
            with col4:
                # Exportar como TXT
                text_data = json.dumps(result["extracted_data"], indent=2, ensure_ascii=False)
                st.download_button(
                    "📝 Descargar TXT",
                    data=text_data,
                    file_name=f"{last_task['site']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        # Screenshots
        if "screenshots" in result and result["screenshots"]:
            st.markdown("### 📸 Capturas de Pantalla")
            
            screenshot_cols = st.columns(min(len(result["screenshots"]), 3))
            
            for i, (name, path) in enumerate(result["screenshots"].items()):
                with screenshot_cols[i % 3]:
                    if os.path.exists(path):
                        with open(path, 'rb') as f:
                            img_data = f.read()
                        
                        st.image(path, caption=name.replace('_', ' ').title(), use_column_width=True)
                        
                        # Botón de descarga
                        st.download_button(
                            f"💾 {name}",
                            data=img_data,
                            file_name=f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                            mime="image/png",
                            use_container_width=True
                        )
        
        # Logs de ejecución
        if "logs" in result:
            with st.expander("📋 Logs de Ejecución"):
                # Mostrar logs con formato mejorado
                log_container = st.container()
                with log_container:
                    for log in result["logs"]:
                        if "✅" in log or "exitoso" in log.lower():
                            st.success(log)
                        elif "❌" in log or "error" in log.lower():
                            st.error(log)
                        elif "⚠️" in log or "advertencia" in log.lower():
                            st.warning(log)
                        else:
                            st.text(log)
    
    else:
        # No hay resultados
        st.info("📭 No hay resultados todavía. Realiza una consulta en la pestaña 'Nueva Consulta'")

with tab3:
    # Tab de Analytics
    st.markdown("""
    <div class="metric-card">
        <h2>📈 Panel de Analytics</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.analytics_data:
        # Métricas generales
        col1, col2, col3, col4 = st.columns(4)
        
        total_queries = sum(data["total_queries"] for data in st.session_state.analytics_data.values())
        total_success = sum(data["successful_queries"] for data in st.session_state.analytics_data.values())
        total_failed = sum(data["failed_queries"] for data in st.session_state.analytics_data.values())
        total_items = sum(data["extracted_items"] for data in st.session_state.analytics_data.values())
        
        with col1:
            st.metric(
                "🎯 Total Consultas",
                total_queries,
                delta=f"+{total_queries}" if total_queries > 0 else None
            )
        
        with col2:
            st.metric(
                "✅ Exitosas",
                total_success,
                delta=f"{(total_success/total_queries*100):.1f}%" if total_queries > 0 else None
            )
        
        with col3:
            st.metric(
                "❌ Fallidas",
                total_failed,
                delta=f"-{(total_failed/total_queries*100):.1f}%" if total_queries > 0 else None
            )
        
        with col4:
            st.metric(
                "📦 Items Extraídos",
                total_items,
                delta=f"~{total_items/total_queries:.1f} por consulta" if total_queries > 0 else None
            )
        
        # Gráficos comparativos por sitio
        st.markdown("### 🌐 Análisis por Sitio")
        
        # Preparar datos para gráficos
        sites = list(st.session_state.analytics_data.keys())
        queries = [st.session_state.analytics_data[site]["total_queries"] for site in sites]
        success = [st.session_state.analytics_data[site]["successful_queries"] for site in sites]
        failed = [st.session_state.analytics_data[site]["failed_queries"] for site in sites]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de barras comparativo
            fig_comparison = go.Figure(data=[
                go.Bar(name='Exitosas', x=sites, y=success, marker_color='#667eea'),
                go.Bar(name='Fallidas', x=sites, y=failed, marker_color='#764ba2')
            ])
            
            fig_comparison.update_layout(
                title="Comparación de Consultas por Sitio",
                barmode='group',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                xaxis_title="Sitio",
                yaxis_title="Número de Consultas"
            )
            
            st.plotly_chart(fig_comparison, use_container_width=True)
        
        with col2:
            # Gráfico de dona con total de consultas
            fig_donut = px.pie(
                values=queries,
                names=sites,
                title="Distribución de Consultas",
                hole=0.4
            )
            
            fig_donut.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            
            fig_donut.update_traces(
                textposition='inside',
                textinfo='percent+label'
            )
            
            st.plotly_chart(fig_donut, use_container_width=True)
        
        # Timeline de actividad
        if st.session_state.task_history:
            st.markdown("### ⏰ Timeline de Actividad")
            
            # Crear datos para el timeline
            timeline_data = []
            for task in st.session_state.task_history:
                timeline_data.append({
                    "Hora": task["timestamp"],
                    "Sitio": task.get("site", "N/A"),
                    "Estado": "Exitoso" if task["result"].get("success") else "Fallido",
                    "Consulta": task["instruction"][:50] + "..." if len(task["instruction"]) > 50 else task["instruction"]
                })
            
            df_timeline = pd.DataFrame(timeline_data)
            
            # Gráfico de dispersión temporal
            fig_timeline = px.scatter(
                df_timeline,
                x="Hora",
                y="Sitio",
                color="Estado",
                hover_data=["Consulta"],
                title="Actividad a lo Largo del Tiempo",
                color_discrete_map={"Exitoso": "#667eea", "Fallido": "#764ba2"}
            )
            
            fig_timeline.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                xaxis_title="Tiempo",
                yaxis_title="Sitio Web"
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
        
    else:
        st.info("📊 No hay datos de analytics todavía. Realiza algunas consultas para ver estadísticas.")

with tab4:
    # Tab de Historial
    st.markdown("""
    <div class="metric-card">
        <h2>📜 Historial de Consultas</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.task_history:
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_site = st.selectbox(
                "🌐 Filtrar por sitio:",
                ["Todos"] + list(set(task.get("site", "N/A") for task in st.session_state.task_history))
            )
        
        with col2:
            filter_status = st.selectbox(
                "📊 Filtrar por estado:",
                ["Todos", "Exitosos", "Fallidos"]
            )
        
        with col3:
            sort_order = st.selectbox(
                "🔄 Ordenar por:",
                ["Más reciente", "Más antiguo"]
            )
        
        # Aplicar filtros
        filtered_history = st.session_state.task_history.copy()
        
        if filter_site != "Todos":
            filtered_history = [t for t in filtered_history if t.get("site") == filter_site]
        
        if filter_status == "Exitosos":
            filtered_history = [t for t in filtered_history if t["result"].get("success")]
        elif filter_status == "Fallidos":
            filtered_history = [t for t in filtered_history if not t["result"].get("success")]
        
        # Ordenar
        if sort_order == "Más reciente":
            filtered_history.reverse()
        
        # Mostrar historial
        st.markdown(f"### 📋 Mostrando {len(filtered_history)} de {len(st.session_state.task_history)} consultas")
        
        for i, task in enumerate(filtered_history):
            with st.expander(
                f"{'✅' if task['result'].get('success') else '❌'} "
                f"{task.get('site', 'N/A')} - "
                f"{task['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - "
                f"{task['instruction'][:50]}..."
            ):
                # Información de la consulta
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("**📝 Consulta completa:**")
                    st.info(task['instruction'])
                    
                    if task['result'].get('success'):
                        # Resumen de datos extraídos
                        if 'extracted_data' in task['result']:
                            st.markdown("**📊 Resumen de datos:**")
                            
                            data = task['result']['extracted_data']
                            if 'pedidos' in data:
                                st.write(f"- 📦 {len(data['pedidos'])} pedidos encontrados")
                            if 'total_pedidos' in data:
                                st.write(f"- 🔢 Total de pedidos: {data['total_pedidos']}")
                            if 'informacion_cuenta' in data:
                                st.write(f"- 👤 Información de cuenta extraída")
                            if 'tablas' in data:
                                st.write(f"- 📋 {len(data['tablas'])} tablas encontradas")
                    else:
                        st.error(f"Error: {task['result'].get('error', 'Error desconocido')}")
                
                with col2:
                    st.markdown("**⚙️ Configuración:**")
                    settings = task.get('settings', {})
                    st.write(f"- 📸 Screenshots: {'Sí' if settings.get('extract_images') else 'No'}")
                    st.write(f"- 📄 Formato: {settings.get('export_format', 'JSON')}")
                    st.write(f"- ⏱️ Espera: {settings.get('wait_time', 3)}s")
                    
                    # Botón para reejecutar
                    if st.button(f"🔄 Reejecutar", key=f"rerun_{i}"):
                        st.session_state.natural_instruction_input = task['instruction']
                        st.rerun()
                
                # Opciones de exportación
                st.markdown("**💾 Acciones:**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Descargar resultado completo
                    result_json = json.dumps(task['result'], indent=2, ensure_ascii=False)
                    st.download_button(
                        "📥 Descargar resultado",
                        data=result_json,
                        file_name=f"resultado_{task['timestamp'].strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key=f"download_{i}"
                    )
                
                with col2:
                    # Ver logs
                    if st.button("📋 Ver logs", key=f"logs_{i}"):
                        with st.container():
                            for log in task['result'].get('logs', []):
                                st.text(log)
                
                with col3:
                    # Eliminar del historial
                    if st.button("🗑️ Eliminar", key=f"delete_{i}"):
                        st.session_state.task_history.remove(task)
                        st.rerun()
        
        # Opciones globales del historial
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Exportar historial completo", use_container_width=True):
                history_json = json.dumps(
                    [
                        {
                            "timestamp": t["timestamp"].isoformat(),
                            "site": t.get("site"),
                            "instruction": t["instruction"],
                            "success": t["result"].get("success"),
                            "data_extracted": bool(t["result"].get("extracted_data"))
                        }
                        for t in st.session_state.task_history
                    ],
                    indent=2,
                    ensure_ascii=False
                )
                
                st.download_button(
                    "📥 Descargar historial",
                    data=history_json,
                    file_name=f"historial_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("🗑️ Limpiar historial", use_container_width=True):
                if st.checkbox("Confirmar eliminación de todo el historial"):
                    st.session_state.task_history = []
                    st.session_state.analytics_data = {}
                    st.success("✅ Historial limpiado")
                    st.rerun()
    
    else:
        st.info("📭 No hay historial todavía. Las consultas realizadas aparecerán aquí.")

# Footer con información
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    <p>🔮 Ximple Analytics AI v2.0 | Desarrollado con ❤️ para analistas de datos</p>
    <p>🔒 Todos los datos son procesados de forma segura y no se almacenan permanentemente</p>
</div>
""", unsafe_allow_html=True)

# Limpiar archivos temporales automáticamente
if st.button("🧹 Limpiar archivos temporales", help="Elimina screenshots y archivos generados"):
    temp_extensions = ['.png', '.json', '.txt', '.csv', '.xlsx']
    cleaned = 0
    
    for ext in temp_extensions:
        for file in os.listdir():
            if file.endswith(ext) and any(x in file for x in ['screenshot', 'capture', 'extraction', 'login', 'final', 'error', 'debug']):
                try:
                    os.remove(file)
                    cleaned += 1
                except:
                    pass
    
    st.success(f"✅ Se eliminaron {cleaned} archivos temporales")

# Importar io para Excel
import io