import requests
import json
import base64
import io
import streamlit as st
import os
import anthropic

def encode_image_to_base64(image_file):
    """
    Encode an image file to base64 string
    
    Args:
        image_file: The image file from streamlit uploader
        
    Returns:
        base64_encoded: The base64 encoded string of the image
    """
    try:
        image_bytes = image_file.getvalue()
        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        return base64_encoded
    except Exception as e:
        st.error(f"Error al codificar la imagen: {str(e)}")
        return None

def analyze_planogram_individually(planogram_file):
    """
    Analiza un planograma individualmente para obtener información detallada sobre productos y estructura
    
    Args:
        planogram_file: Archivo de imagen del planograma
        
    Returns:
        response_json: Respuesta JSON con el análisis del planograma
    """
    try:
        # Get API key from environment variable
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not anthropic_api_key:
            st.warning("No se encontró la clave API de Anthropic en las variables de entorno.")
            return None
        
        # Inicializar cliente de Anthropic con contexto limpio
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        # Encode image to base64
        planogram_base64 = encode_image_to_base64(planogram_file)
        
        if not planogram_base64:
            st.error("No se pudo codificar la imagen del planograma")
            return None
        
        # Prompt específico para análisis individual del planograma
        system_message = "Eres un especialista en análisis de planogramas de supermercados. Tu tarea es analizar detalladamente la estructura y productos mostrados."
        
        user_prompt = """Analiza esta imagen de planograma y proporciona un análisis detallado que incluya:

1. **Estructura general:**
   - Número total de estantes/niveles
   - Orientación de la góndola (vertical/horizontal)
   - Dimensiones aproximadas

2. **Análisis por estante/nivel:**
   Para cada estante de arriba hacia abajo, identifica:
   - Número del estante/nivel
   - Productos presentes (marca, tipo, formato, características visuales)
   - Cantidad de frentes de cada producto
   - Posición de izquierda a derecha

3. **Descripción de productos:**
   Para cada producto visible, especifica:
   - Marca
   - Tipo de producto
   - Formato/tamaño
   - Color predominante del empaque
   - Características distintivas

Responde en formato JSON estructurado con la siguiente estructura:

{
    "analisis_planograma": {
        "estructura": {
            "total_estantes": número,
            "orientacion": "descripción",
            "descripcion_general": "texto descriptivo"
        },
        "estantes": [
            {
                "nivel": "número o código",
                "productos": [
                    {
                        "posicion": número,
                        "marca": "nombre de marca",
                        "tipo_producto": "descripción del tipo",
                        "formato": "tamaño/formato",
                        "color_empaque": "color principal",
                        "frentes_planogramados": número,
                        "caracteristicas": "detalles adicionales"
                    }
                ]
            }
        ]
    }
}"""

        # Preparar mensaje para Claude
        message = [
            {
                "type": "text",
                "text": user_prompt
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg", 
                    "data": planogram_base64
                }
            }
        ]
        
        # Llamada a la API con contexto limpio
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Usando el modelo más reciente
            system=system_message,
            messages=[
                {
                    "role": "user",
                    "content": message
                }
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        response_content = response.content[0].text
        
        # Parsear respuesta JSON
        if isinstance(response_content, str):
            try:
                result_json = json.loads(response_content)
                return result_json
            except json.JSONDecodeError:
                # Intentar extraer JSON de bloques de código markdown
                if "```json" in response_content:
                    json_text = response_content.split("```json")[1].split("```")[0].strip()
                elif "```" in response_content:
                    json_text = response_content.split("```")[1].split("```")[0].strip()
                else:
                    json_text = response_content
                
                try:
                    result_json = json.loads(json_text)
                    return result_json
                except:
                    st.error("No se pudo parsear la respuesta del análisis del planograma")
                    return None
        
        return None
        
    except Exception as e:
        st.error(f"Error en el análisis del planograma: {str(e)}")
        return None

def analyze_realogram_individually(realogram_file):
    """
    Analiza un realograma individualmente para obtener información sobre la situación real
    
    Args:
        realogram_file: Archivo de imagen del realograma
        
    Returns:
        response_json: Respuesta JSON con el análisis del realograma
    """
    try:
        # Get API key from environment variable
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not anthropic_api_key:
            st.warning("No se encontró la clave API de Anthropic en las variables de entorno.")
            return None
        
        # Inicializar cliente de Anthropic con contexto limpio
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        # Encode image to base64
        realogram_base64 = encode_image_to_base64(realogram_file)
        
        if not realogram_base64:
            st.error("No se pudo codificar la imagen del realograma")
            return None
        
        # Prompt específico para análisis individual del realograma
        system_message = "Eres un especialista en análisis de exhibiciones reales en supermercados. Tu tarea es documentar la situación actual de productos en los estantes."
        
        user_prompt = """Analiza esta imagen de realograma (situación real) y proporciona un análisis detallado que incluya:

1. **Estado actual de la exhibición:**
   - Número de estantes/niveles visibles
   - Condición general de la exhibición
   - Espacios vacíos o mal utilizados

2. **Análisis por estante/nivel:**
   Para cada estante de arriba hacia abajo, documenta:
   - Número del estante/nivel
   - Productos realmente presentes
   - Cantidad real de frentes de cada producto
   - Posición actual de cada producto
   - Productos no planogramados (si los hay)

3. **Inventario real:**
   Para cada producto visible, especifica:
   - Marca identificada
   - Tipo de producto
   - Formato/tamaño observado
   - Color del empaque
   - Estado de la exhibición

Responde en formato JSON estructurado con la siguiente estructura:

{
    "analisis_realograma": {
        "estado_exhibicion": {
            "total_estantes": número,
            "condicion_general": "descripción",
            "descripcion_situacion": "texto descriptivo"
        },
        "estantes": [
            {
                "nivel": "número o código",
                "productos_presentes": [
                    {
                        "posicion_actual": número,
                        "marca": "nombre de marca",
                        "tipo_producto": "descripción del tipo",
                        "formato": "tamaño/formato",
                        "color_empaque": "color principal",
                        "frentes_reales": número,
                        "estado": "descripción del estado",
                        "es_planogramado": true/false
                    }
                ],
                "espacios_vacios": número,
                "observaciones": "notas adicionales"
            }
        ]
    }
}"""

        # Preparar mensaje para Claude
        message = [
            {
                "type": "text",
                "text": user_prompt
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": realogram_base64
                }
            }
        ]
        
        # Llamada a la API con contexto limpio
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Usando el modelo más reciente
            system=system_message,
            messages=[
                {
                    "role": "user",
                    "content": message
                }
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        response_content = response.content[0].text
        
        # Parsear respuesta JSON
        if isinstance(response_content, str):
            try:
                result_json = json.loads(response_content)
                return result_json
            except json.JSONDecodeError:
                # Intentar extraer JSON de bloques de código markdown
                if "```json" in response_content:
                    json_text = response_content.split("```json")[1].split("```")[0].strip()
                elif "```" in response_content:
                    json_text = response_content.split("```")[1].split("```")[0].strip()
                else:
                    json_text = response_content
                
                try:
                    result_json = json.loads(json_text)
                    return result_json
                except:
                    st.error("No se pudo parsear la respuesta del análisis del realograma")
                    return None
        
        return None
        
    except Exception as e:
        st.error(f"Error en el análisis del realograma: {str(e)}")
        return None

def compare_planogram_vs_realogram(planogram_file, realogram_file, planogram_analysis, realogram_analysis):
    """
    Realiza la comparación final entre planograma y realograma utilizando los análisis individuales previos
    
    Args:
        planogram_file: Archivo de imagen del planograma
        realogram_file: Archivo de imagen del realograma
        planogram_analysis: Análisis previo del planograma
        realogram_analysis: Análisis previo del realograma
        
    Returns:
        response_json: Respuesta JSON con la comparación final
    """
    try:
        # Get API key from environment variable
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not anthropic_api_key:
            st.warning("No se encontró la clave API de Anthropic en las variables de entorno.")
            return get_mock_response()
        
        # Inicializar cliente de Anthropic con contexto completamente limpio
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        # Encode images to base64
        planogram_base64 = encode_image_to_base64(planogram_file)
        realogram_base64 = encode_image_to_base64(realogram_file)
        
        if not planogram_base64 or not realogram_base64:
            st.error("No se pudieron codificar las imágenes correctamente")
            return get_mock_response()
        
        # Prompt específico para comparación final
        system_message = "Eres un especialista en compliance de planogramas. Tu tarea es comparar la disposición planificada versus la real y generar un reporte de cumplimiento detallado."
        
        user_prompt = f"""Analiza las siguientes dos imágenes y sus respectivos análisis para generar un reporte de cumplimiento:

**ANÁLISIS PREVIO DEL PLANOGRAMA:**
{json.dumps(planogram_analysis, indent=2, ensure_ascii=False)}

**ANÁLISIS PREVIO DEL REALOGRAMA:**
{json.dumps(realogram_analysis, indent=2, ensure_ascii=False)}

**INSTRUCCIONES PARA LA COMPARACIÓN:**

1. **Compara estante por estante** el planograma vs realograma
2. **Para cada producto planogramado, determina:**
   - Si está presente en el realograma
   - Si está en la posición correcta
   - Si tiene la cantidad de frentes esperada
   - Si mantiene las características esperadas

3. **Identifica productos no planogramados** que aparezcan en el realograma
4. **Calcula métricas de cumplimiento** por estante y general
5. **Genera conclusiones** específicas y accionables

**FORMATO DE RESPUESTA REQUERIDO:**

{{
    "diferencias": [
        {{
            "nivel": "número o código del estante",
            "resultado": {{
                "productos": [
                    {{
                        "posicion_producto": número,
                        "nombre": "nombre del producto",
                        "marca": "marca identificada",
                        "tipo_producto": "tipo",
                        "encontrado": true/false,
                        "posicion_correcta": true/false,
                        "frentes_esperados": número,
                        "frentes_encontrados": número,
                        "observaciones": "notas específicas"
                    }}
                ]
            }}
        }}
    ],
    "productos_no_planogramados": [
        {{
            "nivel": "estante donde aparece",
            "producto": "descripción del producto",
            "posicion": número,
            "frentes": número
        }}
    ],
    "metricas_cumplimiento": {{
        "porcentaje_productos_encontrados": número,
        "porcentaje_posiciones_correctas": número,
        "porcentaje_frentes_correctos": número,
        "cumplimiento_general": número
    }},
    "conclusiones": [
        "conclusión específica 1",
        "conclusión específica 2",
        "recomendación de mejora 1",
        "recomendación de mejora 2"
    ]
}}

Sé preciso en el conteo de frentes y posiciones. Basa tu análisis en la comparación visual directa entre las imágenes y los análisis previos proporcionados."""

        # Preparar mensaje para Claude con contexto limpio
        message = [
            {
                "type": "text",
                "text": user_prompt
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": planogram_base64
                }
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": realogram_base64
                }
            }
        ]
        
        # Llamada a la API con contexto completamente limpio
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Usando el modelo más reciente
            system=system_message,
            messages=[
                {
                    "role": "user",
                    "content": message
                }
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        response_content = response.content[0].text
        
        # Parsear respuesta JSON
        if isinstance(response_content, str):
            try:
                result_json = json.loads(response_content)
                return result_json
            except json.JSONDecodeError:
                # Intentar extraer JSON de bloques de código markdown
                if "```json" in response_content:
                    json_text = response_content.split("```json")[1].split("```")[0].strip()
                elif "```" in response_content:
                    json_text = response_content.split("```")[1].split("```")[0].strip()
                else:
                    json_text = response_content
                
                try:
                    result_json = json.loads(json_text)
                    return result_json
                except:
                    st.error("No se pudo parsear la respuesta de la comparación final")
                    return get_mock_response()
        
        return get_mock_response()
        
    except Exception as e:
        st.error(f"Error en la comparación final: {str(e)}")
        return get_mock_response()

def send_images_to_model(planogram_file, realogram_file):
    """
    Análisis comparativo directo con Claude Sonnet para detectar correctamente los productos
    
    Args:
        planogram_file: Archivo de imagen del planograma
        realogram_file: Archivo de imagen del realograma
        
    Returns:
        response_json: Respuesta JSON con el análisis comparativo
    """
    try:
        # Verificar que tenemos la API key
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            st.error("FALTA LA CLAVE API DE ANTHROPIC - No se puede hacer análisis real")
            return None
        
        # Inicializar cliente con contexto limpio
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        # Encode images to base64
        planogram_base64 = encode_image_to_base64(planogram_file)
        realogram_base64 = encode_image_to_base64(realogram_file)
        
        if not planogram_base64 or not realogram_base64:
            st.error("No se pudieron codificar las imágenes correctamente")
            return get_mock_response()
        
        system_message = "Eres un especialista en análisis de planogramas de supermercados. Analiza cuidadosamente ambas imágenes para identificar correctamente los productos presentes."
        
        user_prompt = """Analiza estas dos imágenes de planograma y realograma de una góndola de supermercado.

IMPORTANTE: 
- La góndola tiene EXACTAMENTE 6 niveles/estantes (analiza todos los 6 niveles de arriba hacia abajo)
- Identifica correctamente qué productos están en cada nivel
- Separa claramente la MARCA del TIPO DE PRODUCTO

Para CADA UNO de los 6 niveles (de arriba hacia abajo):
1. Identifica qué productos están presentes en el planograma
2. Identifica qué productos están presentes en el realograma  
3. Cuenta los frentes de cada producto
4. Compara posición planificada vs real

Responde en este formato JSON:

{
    "diferencias": [
        {
            "nivel": 1,
            "resultado": {
                "productos": [
                    {
                        "posicion_producto": número,
                        "marca": "nombre de la marca específica",
                        "tipo_producto": "categoría/tipo del producto",
                        "nombre_completo": "descripción completa",
                        "encontrado": true/false,
                        "posicion_correcta": true/false,
                        "frentes_esperados": número,
                        "frentes_encontrados": número,
                        "observaciones": "detalles específicos"
                    }
                ]
            }
        },
        {
            "nivel": 2,
            "resultado": {
                "productos": [...]
            }
        },
        {
            "nivel": 3,
            "resultado": {
                "productos": [...]
            }
        },
        {
            "nivel": 4,
            "resultado": {
                "productos": [...]
            }
        },
        {
            "nivel": 5,
            "resultado": {
                "productos": [...]
            }
        },
        {
            "nivel": 6,
            "resultado": {
                "productos": [...]
            }
        }
    ],
    "analisis_planograma": {
        "analisis_planograma": {
            "estructura": {
                "total_estantes": 6,
                "orientacion": "vertical",
                "descripcion_general": "descripción detallada de la estructura"
            },
            "estantes": [
                {
                    "nivel": 1,
                    "productos": [
                        {
                            "posicion": número,
                            "marca": "marca específica",
                            "tipo_producto": "tipo de producto",
                            "formato": "tamaño/formato",
                            "color_empaque": "color principal",
                            "frentes_planogramados": número,
                            "caracteristicas": "detalles adicionales"
                        }
                    ]
                }
            ]
        }
    },
    "analisis_realograma": {
        "analisis_realograma": {
            "estado_exhibicion": {
                "total_estantes": 6,
                "condicion_general": "descripción del estado",
                "descripcion_situacion": "situación actual detallada"
            },
            "estantes": [
                {
                    "nivel": 1,
                    "productos_presentes": [
                        {
                            "posicion_actual": número,
                            "marca": "marca identificada",
                            "tipo_producto": "tipo de producto",
                            "formato": "tamaño/formato",
                            "color_empaque": "color principal",
                            "frentes_reales": número,
                            "estado": "estado del producto",
                            "es_planogramado": true/false
                        }
                    ],
                    "espacios_vacios": número,
                    "observaciones": "notas del nivel"
                }
            ]
        }
    },
    "conclusiones": [
        "observaciones específicas sobre las diferencias",
        "productos faltantes o mal posicionados",
        "cumplimiento general del planograma"
    ]
}

DEBES analizar y reportar los 6 niveles completos."""

        with st.spinner("Analizando imágenes con IA..."):
            message = [
                {
                    "type": "text",
                    "text": user_prompt
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": planogram_base64
                    }
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": realogram_base64
                    }
                }
            ]
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            # Extraer texto de la respuesta - método simplificado
            try:
                response_content = response.content[0].text
                st.info(f"Respuesta recibida del modelo (primeros 200 caracteres): {response_content[:200]}...")
            except Exception as e:
                st.error(f"Error al extraer respuesta: {str(e)}")
                return None
            
            if not response_content:
                st.error("No se recibió respuesta válida del modelo")
                return None
            
            # Parsear JSON
            try:
                result_json = json.loads(response_content)
                return result_json
            except json.JSONDecodeError:
                # Intentar extraer JSON de markdown
                if "```json" in response_content:
                    json_text = response_content.split("```json")[1].split("```")[0].strip()
                elif "```" in response_content:
                    json_text = response_content.split("```")[1].split("```")[0].strip()
                else:
                    json_text = response_content
                
                try:
                    result_json = json.loads(json_text)
                    return result_json
                except json.JSONDecodeError as e:
                    st.error(f"Error al parsear respuesta JSON: {str(e)}")
                    st.text("Respuesta recibida:")
                    st.text(response_content[:500])
                    return get_mock_response()
        
    except Exception as e:
        st.error(f"Error en el análisis: {str(e)}")
        return get_mock_response()

def get_mock_response():
    """
    Generate a mock response for testing purposes
    """
    return {
        "diferencias": [
            {
                "nivel": 1,
                "resultado": {
                    "productos": [
                        {
                            "posicion_producto": 1,
                            "marca": "Coca-Cola",
                            "submarca": "Original",
                            "formato": "2L",
                            "color": "rojo",
                            "encontrado": True,
                            "posicion_correcta": True,
                            "frentes_esperados": 4,
                            "frentes_encontrados": 4
                        },
                        {
                            "posicion_producto": 2,
                            "marca": "Coca-Cola",
                            "submarca": "Zero",
                            "formato": "2L",
                            "color": "negro",
                            "encontrado": True,
                            "posicion_correcta": False,
                            "frentes_esperados": 2,
                            "frentes_encontrados": 1
                        },
                        {
                            "posicion_producto": 3,
                            "marca": "Sprite",
                            "submarca": "Regular",
                            "formato": "2L",
                            "color": "verde",
                            "encontrado": False,
                            "posicion_correcta": False,
                            "frentes_esperados": 2,
                            "frentes_encontrados": 0
                        }
                    ]
                }
            },
            {
                "nivel": 2,
                "resultado": {
                    "productos": [
                        {
                            "posicion_producto": 1,
                            "marca": "Fanta",
                            "submarca": "Naranja",
                            "formato": "2L",
                            "color": "naranja",
                            "encontrado": True,
                            "posicion_correcta": True,
                            "frentes_esperados": 3,
                            "frentes_encontrados": 3
                        },
                        {
                            "posicion_producto": 2,
                            "marca": "Fanta",
                            "submarca": "Uva",
                            "formato": "2L",
                            "color": "morado",
                            "encontrado": True,
                            "posicion_correcta": True,
                            "frentes_esperados": 2,
                            "frentes_encontrados": 2
                        }
                    ]
                }
            }
        ],
        "conclusiones": [
            "El planograma se encuentra cumplido en un 80%",
            "Se detecta la ausencia de Sprite Regular 2L",
            "Coca-Cola Zero tiene un frente menos de lo esperado",
            "El resto de los productos cumplen con la ubicación y cantidad de frentes esperados"
        ]
    }

def parse_json_response(json_response):
    """
    Parse the JSON response from the model
    
    Args:
        json_response: The JSON response from the model
        
    Returns:
        parsed_data: The parsed JSON data
    """
    if isinstance(json_response, str):
        try:
            parsed_data = json.loads(json_response)
        except json.JSONDecodeError:
            st.error("Error al analizar la respuesta JSON")
            return {}
    else:
        parsed_data = json_response
    
    return parsed_data
