import streamlit as st
import pandas as pd
import json
from utils import send_images_to_model, parse_json_response, analyze_planogram_individually, analyze_realogram_individually, compare_planogram_vs_realogram
from database import guardar_analisis, calcular_porcentaje_cumplimiento, obtener_analisis_recientes, obtener_detalle_analisis

# Configure the Streamlit page
st.set_page_config(
    page_title="Análisis de Planograma vs Realograma",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("📊 Análisis de Planograma vs Realograma")
st.markdown("Compara el planograma ideal con la imagen real del góndola para identificar diferencias y cumplimiento.")

# Create tabs for different functionalities
main_tab1, main_tab2 = st.tabs(["Análisis Individual", "Análisis Múltiple"])

with main_tab1:
    st.header("🔍 Análisis Individual")
    
    # Create two columns for file uploads
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Planograma (Imagen Ideal)")
        planogram_file = st.file_uploader(
            "Sube la imagen del planograma", 
            type=['png', 'jpg', 'jpeg'],
            key="planogram"
        )
        if planogram_file:
            st.image(planogram_file, caption="Planograma", use_column_width=True)
    
    with col2:
        st.subheader("📷 Realograma (Imagen Real)")
        realogram_file = st.file_uploader(
            "Sube la imagen del realograma", 
            type=['png', 'jpg', 'jpeg'],
            key="realogram"
        )
        if realogram_file:
            st.image(realogram_file, caption="Realograma", use_column_width=True)
    
    # Analysis button
    if st.button("🚀 Iniciar Análisis", type="primary"):
        if planogram_file is not None and realogram_file is not None:
            with st.spinner("Analizando imágenes..."):
                try:
                    # Send images to model for analysis
                    json_response = send_images_to_model(planogram_file, realogram_file)
                    
                    # Initialize parsed_data
                    parsed_data = {}
                    
                    # Verificar si se recibió una respuesta válida
                    if json_response is None:
                        st.error("No se pudo completar el análisis. Verifica que la clave API de Anthropic esté configurada correctamente.")
                    else:
                        # Parse the JSON response
                        parsed_data = parse_json_response(json_response)
                        
                        if parsed_data is None:
                            st.error("No se pudo procesar la respuesta del análisis.")
                            parsed_data = {}
                        else:
                            # Guardar el análisis en la base de datos
                            planogram_name = planogram_file.name if hasattr(planogram_file, 'name') else 'planograma.jpg'
                            realogram_name = realogram_file.name if hasattr(realogram_file, 'name') else 'realograma.jpg'
                            
                            analisis_id = guardar_analisis(planogram_name, realogram_name, json_response)
                            if analisis_id:
                                st.success(f"Análisis guardado con ID: {analisis_id}")
                    
                    # Display the results only if we have data
                    if parsed_data:
                        st.subheader("Resultados del Análisis")
                        
                        # Create tabs to show different analysis views
                        tab1, tab2, tab3, tab4 = st.tabs(["Vista Tabular", "Análisis Planograma", "Análisis Realograma", "JSON Original"])
                        
                        with tab1:
                            # Initialize an empty list to store all product data
                            all_products = []
                            
                            # Process each level safely
                            if "diferencias" in parsed_data:
                                for difference in parsed_data.get("diferencias", []):
                                    nivel = difference.get("nivel", "N/A")
                                    productos = difference.get("resultado", {}).get("productos", [])
                                    
                                    for producto in productos:
                                        # Add the level to each product record
                                        producto["nivel"] = nivel
                                        all_products.append(producto)
                            
                            # Create DataFrame from all products
                            if all_products:
                                df = pd.DataFrame(all_products)
                                
                                # Ensure required columns exist
                                required_columns = ['marca', 'tipo_producto', 'encontrado', 'posicion_correcta']
                                for col in required_columns:
                                    if col not in df.columns:
                                        df[col] = False
                                
                                # Reorder columns for better display
                                column_order = ['nivel', 'marca', 'tipo_producto', 'encontrado', 'posicion_correcta']
                                existing_columns = [col for col in column_order if col in df.columns]
                                df = df[existing_columns]
                                
                                # Function to highlight rows based on product status
                                def highlight_rows(row):
                                    if not row['encontrado']:
                                        return ['background-color: #ffcccc'] * len(row)  # Red for missing
                                    elif not row['posicion_correcta']:
                                        return ['background-color: #ffd700'] * len(row)  # Gold for wrong position  
                                    else:
                                        return ['background-color: #ccffcc'] * len(row)  # Green for correct
                                
                                # Apply styling and display
                                styled_df = df.style.apply(highlight_rows, axis=1)
                                st.dataframe(styled_df, use_container_width=True)
                                
                                # Display summary metrics
                                st.subheader("📈 Métricas de Cumplimiento")
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    found_products = df['encontrado'].sum()
                                    st.metric("Productos Encontrados", f"{found_products} ({found_products/len(df)*100:.1f}%)")
                                
                                with col2:
                                    missing_products = len(df) - found_products
                                    st.metric("Productos Faltantes", f"{missing_products} ({missing_products/len(df)*100:.1f}%)")
                                
                                with col3:
                                    correct_pos = df['posicion_correcta'].sum()
                                    st.metric("Posiciones Correctas", f"{correct_pos} ({correct_pos/len(df)*100:.1f}%)")
                                
                                # Display conclusions
                                if "conclusiones" in parsed_data:
                                    st.subheader("Conclusiones")
                                    for conclusion in parsed_data["conclusiones"]:
                                        st.markdown(f"- {conclusion}")
                            else:
                                st.warning("No se encontraron datos de productos en los resultados del análisis.")
                        
                        with tab2:
                            # Mostrar análisis individual del planograma
                            if "analisis_planograma" in parsed_data:
                                st.subheader("Análisis Detallado del Planograma")
                                planogram_data = parsed_data["analisis_planograma"]
                                
                                if isinstance(planogram_data, dict):
                                    if "estructura" in planogram_data:
                                        st.write("**Estructura detectada:**")
                                        st.write(planogram_data["estructura"])
                                    
                                    if "productos_detectados" in planogram_data:
                                        st.write("**Productos detectados:**")
                                        for producto in planogram_data["productos_detectados"]:
                                            st.write(f"• {producto}")
                                else:
                                    st.write(planogram_data)
                            else:
                                st.info("No hay análisis individual del planograma disponible.")
                        
                        with tab3:
                            # Mostrar análisis individual del realograma
                            if "analisis_realograma" in parsed_data:
                                st.subheader("Análisis Detallado del Realograma")
                                realogram_data = parsed_data["analisis_realograma"]
                                
                                if isinstance(realogram_data, dict):
                                    if "situacion_actual" in realogram_data:
                                        st.write("**Situación actual:**")
                                        st.write(realogram_data["situacion_actual"])
                                    
                                    if "productos_observados" in realogram_data:
                                        st.write("**Productos observados:**")
                                        for producto in realogram_data["productos_observados"]:
                                            st.write(f"• {producto}")
                                else:
                                    st.write(realogram_data)
                            else:
                                st.info("No hay análisis individual del realograma disponible.")
                        
                        with tab4:
                            st.subheader("JSON Response Original")
                            st.json(parsed_data)
                    
                except Exception as e:
                    st.error(f"Error durante el análisis: {str(e)}")
        else:
            st.warning("⚠️ Por favor, sube ambas imágenes (planograma y realograma) antes de iniciar el análisis.")

with main_tab2:
    st.header("📊 Análisis Múltiple")
    st.markdown("Analiza múltiples pares de imágenes de forma secuencial.")
    
    # Number of image pairs to analyze
    num_pairs = st.number_input("Número de pares de imágenes a analizar", min_value=1, max_value=10, value=2)
    
    # Initialize session state for multiple analysis
    if 'multiple_results' not in st.session_state:
        st.session_state.multiple_results = []
    
    # Create file uploaders for multiple pairs
    image_pairs = []
    for i in range(num_pairs):
        st.subheader(f"Par de Imágenes {i+1}")
        col1, col2 = st.columns(2)
        
        with col1:
            planogram = st.file_uploader(
                f"Planograma {i+1}", 
                type=['png', 'jpg', 'jpeg'],
                key=f"multi_planogram_{i}"
            )
        
        with col2:
            realogram = st.file_uploader(
                f"Realograma {i+1}", 
                type=['png', 'jpg', 'jpeg'],
                key=f"multi_realogram_{i}"
            )
        
        if planogram and realogram:
            image_pairs.append((planogram, realogram))
    
    # Process all image pairs
    if st.button("🚀 Analizar Todos los Pares", type="primary"):
        if len(image_pairs) > 0:
            st.session_state.multiple_results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, (planogram, realogram) in enumerate(image_pairs):
                status_text.text(f"Procesando par {idx + 1} de {len(image_pairs)}...")
                progress_bar.progress((idx + 1) / len(image_pairs))
                
                try:
                    # Analyze this pair
                    json_response = send_images_to_model(planogram, realogram)
                    
                    if json_response:
                        parsed_data = parse_json_response(json_response)
                        if parsed_data:
                            # Calculate compliance percentage
                            compliance = calcular_porcentaje_cumplimiento(json_response)
                            
                            result = {
                                'pair_number': idx + 1,
                                'planogram_name': planogram.name,
                                'realogram_name': realogram.name,
                                'compliance_percentage': compliance,
                                'analysis_data': parsed_data
                            }
                            st.session_state.multiple_results.append(result)
                            
                            # Save to database
                            guardar_analisis(planogram.name, realogram.name, json_response)
                        
                except Exception as e:
                    st.error(f"Error procesando par {idx + 1}: {str(e)}")
            
            status_text.text("✅ Análisis completado!")
            progress_bar.empty()
        else:
            st.warning("No hay pares de imágenes válidos para analizar.")
    
    # Display results if available
    if st.session_state.multiple_results:
        st.subheader("📈 Resultados del Análisis Múltiple")
        
        # Create summary table
        summary_data = []
        for result in st.session_state.multiple_results:
            summary_data.append({
                'Par': result['pair_number'],
                'Planograma': result['planogram_name'],
                'Realograma': result['realogram_name'],
                'Cumplimiento (%)': f"{result['compliance_percentage']:.1f}%"
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Function to highlight compliance percentages
        def highlight_compliance(val):
            if isinstance(val, str) and '%' in val:
                percentage = float(val.replace('%', ''))
                if percentage >= 80:
                    return 'background-color: #ccffcc'  # Green
                elif percentage >= 60:
                    return 'background-color: #ffd700'  # Gold
                else:
                    return 'background-color: #ffcccc'  # Red
            return ''
        
        styled_summary = summary_df.style.applymap(highlight_compliance, subset=['Cumplimiento (%)'])
        st.dataframe(styled_summary, use_container_width=True)
        
        # Show detailed results for each pair
        for result in st.session_state.multiple_results:
            with st.expander(f"Detalles Par {result['pair_number']} - {result['compliance_percentage']:.1f}% cumplimiento"):
                analysis_data = result['analysis_data']
                
                if "diferencias" in analysis_data:
                    all_products = []
                    for difference in analysis_data["diferencias"]:
                        nivel = difference.get("nivel", "N/A")
                        productos = difference.get("resultado", {}).get("productos", [])
                        
                        for producto in productos:
                            producto["nivel"] = nivel
                            all_products.append(producto)
                    
                    if all_products:
                        df = pd.DataFrame(all_products)
                        
                        # Ensure required columns exist
                        required_columns = ['marca', 'tipo_producto', 'encontrado', 'posicion_correcta']
                        for col in required_columns:
                            if col not in df.columns:
                                df[col] = False
                        
                        # Function to highlight rows
                        def highlight_row(x):
                            if not x['encontrado']:
                                return ['background-color: #ffcccc'] * len(x)
                            elif not x['posicion_correcta']:
                                return ['background-color: #ffd700'] * len(x)
                            else:
                                return ['background-color: #ccffcc'] * len(x)
                        
                        styled_df = df.style.apply(highlight_row, axis=1)
                        st.dataframe(styled_df, use_container_width=True)

# Sidebar for recent analysis
st.sidebar.header("📋 Análisis Recientes")

try:
    recent_analysis = obtener_analisis_recientes(5)
    if recent_analysis:
        for analysis in recent_analysis:
            with st.sidebar.expander(f"ID: {analysis['id']} - {analysis['fecha_analisis'].strftime('%d/%m/%Y')}"):
                st.write(f"**Planograma:** {analysis['nombre_planograma']}")
                st.write(f"**Realograma:** {analysis['nombre_realograma']}")
                
                # Calculate compliance if possible
                if analysis['respuesta_json']:
                    try:
                        compliance = calcular_porcentaje_cumplimiento(analysis['respuesta_json'])
                        st.write(f"**Cumplimiento:** {compliance:.1f}%")
                    except:
                        st.write("**Cumplimiento:** No calculado")
                
                if st.button(f"Ver detalles", key=f"detail_{analysis['id']}"):
                    # Store the selected analysis ID in session state
                    st.session_state.selected_analysis_id = analysis['id']
                    st.rerun()
    else:
        st.sidebar.info("No hay análisis recientes.")
        
except Exception as e:
    st.sidebar.error(f"Error al cargar análisis recientes: {str(e)}")

# Show detailed analysis if selected
if 'selected_analysis_id' in st.session_state:
    try:
        detail = obtener_detalle_analisis(st.session_state.selected_analysis_id)
        if detail:
            st.subheader(f"📊 Detalle del Análisis ID: {detail['id']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Fecha:** {detail['fecha_analisis']}")
                st.write(f"**Planograma:** {detail['nombre_planograma']}")
            with col2:
                st.write(f"**Realograma:** {detail['nombre_realograma']}")
                
                if detail['respuesta_json']:
                    try:
                        compliance = calcular_porcentaje_cumplimiento(detail['respuesta_json'])
                        st.write(f"**Cumplimiento:** {compliance:.1f}%")
                    except:
                        st.write("**Cumplimiento:** No calculado")
            
            if detail['respuesta_json']:
                parsed_detail = parse_json_response(detail['respuesta_json'])
                if parsed_detail and "diferencias" in parsed_detail:
                    all_products = []
                    for difference in parsed_detail["diferencias"]:
                        nivel = difference.get("nivel", "N/A")
                        productos = difference.get("resultado", {}).get("productos", [])
                        
                        for producto in productos:
                            producto["nivel"] = nivel
                            all_products.append(producto)
                    
                    if all_products:
                        df = pd.DataFrame(all_products)
                        
                        # Ensure required columns exist
                        required_columns = ['marca', 'tipo_producto', 'encontrado', 'posicion_correcta']
                        for col in required_columns:
                            if col not in df.columns:
                                df[col] = False
                        
                        # Function to highlight rows
                        def highlight_rows(row):
                            if not row['encontrado']:
                                return ['background-color: #ffcccc'] * len(row)
                            elif not row['posicion_correcta']:
                                return ['background-color: #ffd700'] * len(row)
                            else:
                                return ['background-color: #ccffcc'] * len(row)
                        
                        styled_df = df.style.apply(highlight_rows, axis=1)
                        st.dataframe(styled_df, use_container_width=True)
            
            if st.button("🔙 Cerrar detalles"):
                del st.session_state.selected_analysis_id
                st.rerun()
                
    except Exception as e:
        st.error(f"Error al cargar el detalle del análisis: {str(e)}")
        if st.button("🔙 Cerrar"):
            del st.session_state.selected_analysis_id
            st.rerun()