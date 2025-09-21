# utils/rekognition_client.py
import os
import json
import base64
import boto3
from typing import Dict, Any, List, Tuple
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
import numpy as np
from PIL import Image
import io

class RekognitionClient:
    """
    Cliente para AWS Rekognition que detecta productos, espacios vacíos
    y analiza cumplimiento de planogramas
    """
    
    def __init__(self, region: str = "us-east-1"):
        """
        Inicializa el cliente de Rekognition
        """
        if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
            raise ValueError("AWS credentials not found in env. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        
        cfg = Config(
            region_name=region,
            signature_version='v4',
            retries={'max_attempts': 3, 'mode': 'standard'}
        )
        
        try:
            self.client = boto3.client(
                'rekognition',
                region_name=region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=os.getenv("AWS_SESSION_TOKEN", None),
                config=cfg
            )
        except NoCredentialsError:
            raise ValueError("AWS credentials are invalid or not properly configured")
    
    def detect_objects_and_text(
        self,
        planogram_b64: str,
        realogram_b64: str,
        confidence_threshold: int = 80
    ) -> Dict[str, Any]:
        """
        Detecta objetos y texto en ambas imágenes
        """
        result = {
            'planogram_objects': [],
            'planogram_text': [],
            'realogram_objects': [],
            'realogram_text': [],
            'empty_spaces_count': 0,
            'total_labels': 0,
            'total_text': 0
        }
        
        try:
            # Detectar objetos en planograma
            planogram_labels = self._detect_labels(planogram_b64, confidence_threshold)
            result['planogram_objects'] = planogram_labels
            
            # Detectar objetos en realograma
            realogram_labels = self._detect_labels(realogram_b64, confidence_threshold)
            result['realogram_objects'] = realogram_labels
            
            # Detectar texto en planograma
            planogram_text = self._detect_text(planogram_b64, confidence_threshold)
            result['planogram_text'] = planogram_text
            
            # Detectar texto en realograma
            realogram_text = self._detect_text(realogram_b64, confidence_threshold)
            result['realogram_text'] = realogram_text
            
            # Calcular métricas
            result['total_labels'] = len(planogram_labels) + len(realogram_labels)
            result['total_text'] = len(planogram_text) + len(realogram_text)
            
            # Detectar espacios vacíos
            empty_spaces = self._detect_empty_spaces(realogram_b64, realogram_labels)
            result['empty_spaces'] = empty_spaces
            result['empty_spaces_count'] = len(empty_spaces)
            
        except Exception as e:
            print(f"Error in Rekognition detection: {str(e)}")
            
        return result
    
    def _detect_labels(self, image_b64: str, min_confidence: int = 80) -> List[Dict]:
        """
        Detecta etiquetas/objetos en una imagen
        """
        try:
            response = self.client.detect_labels(
                Image={'Bytes': base64.b64decode(image_b64)},
                MinConfidence=min_confidence,
                MaxLabels=100
            )
            
            # Filtrar etiquetas relevantes para productos
            relevant_categories = [
                'Bottle', 'Can', 'Package', 'Box', 'Container',
                'Product', 'Beverage', 'Food', 'Snack', 'Cosmetics',
                'Cleaning Product', 'Aerosol', 'Spray', 'Wipes'
            ]
            
            labels = []
            for label in response.get('Labels', []):
                # Incluir si es una categoría relevante o tiene alta confianza
                if (label['Name'] in relevant_categories or 
                    label['Confidence'] > 90 or
                    any(parent['Name'] in relevant_categories for parent in label.get('Parents', []))):
                    
                    label_info = {
                        'Name': label['Name'],
                        'Confidence': label['Confidence'],
                        'Instances': []
                    }
                    
                    # Agregar información de instancias (ubicaciones)
                    for instance in label.get('Instances', []):
                        bbox = instance.get('BoundingBox', {})
                        if bbox:
                            label_info['Instances'].append({
                                'BoundingBox': bbox,
                                'Confidence': instance.get('Confidence', 0)
                            })
                    
                    labels.append(label_info)
            
            return labels
            
        except Exception as e:
            print(f"Error detecting labels: {str(e)}")
            return []
    
    def _detect_text(self, image_b64: str, min_confidence: int = 80) -> List[Dict]:
        """
        Detecta texto en una imagen (nombres de productos, marcas)
        """
        try:
            response = self.client.detect_text(
                Image={'Bytes': base64.b64decode(image_b64)},
                Filters={'MinConfidence': min_confidence}
            )
            
            text_detections = []
            for text_detection in response.get('TextDetections', []):
                # Solo incluir texto de líneas completas o palabras, no caracteres individuales
                if text_detection['Type'] in ['LINE', 'WORD'] and text_detection['Confidence'] > min_confidence:
                    text_info = {
                        'Text': text_detection['DetectedText'],
                        'Type': text_detection['Type'],
                        'Confidence': text_detection['Confidence'],
                        'BoundingBox': text_detection.get('Geometry', {}).get('BoundingBox', {})
                    }
                    text_detections.append(text_info)
            
            return text_detections
            
        except Exception as e:
            print(f"Error detecting text: {str(e)}")
            return []
    
    def _detect_empty_spaces(self, image_b64: str, detected_objects: List[Dict]) -> List[Dict]:
        """
        Detecta espacios vacíos en la góndola analizando las áreas sin productos
        """
        empty_spaces = []
        
        try:
            # Convertir imagen a numpy array para análisis
            image = Image.open(io.BytesIO(base64.b64decode(image_b64)))
            img_width, img_height = image.size
            
            # Crear mapa de ocupación
            occupation_map = np.zeros((img_height, img_width), dtype=bool)
            
            # Marcar áreas ocupadas por objetos detectados
            for obj in detected_objects:
                for instance in obj.get('Instances', []):
                    bbox = instance.get('BoundingBox', {})
                    if bbox:
                        left = int(bbox.get('Left', 0) * img_width)
                        top = int(bbox.get('Top', 0) * img_height)
                        width = int(bbox.get('Width', 0) * img_width)
                        height = int(bbox.get('Height', 0) * img_height)
                        
                        # Marcar área como ocupada
                        occupation_map[top:top+height, left:left+width] = True
            
            # Dividir imagen en grid para análisis de vacíos
            grid_rows = 6  # Aproximadamente 6 niveles de estantes
            grid_cols = 12  # Dividir horizontalmente en 12 secciones
            
            cell_height = img_height // grid_rows
            cell_width = img_width // grid_cols
            
            for row in range(grid_rows):
                for col in range(grid_cols):
                    # Calcular área de la celda
                    top = row * cell_height
                    bottom = min((row + 1) * cell_height, img_height)
                    left = col * cell_width
                    right = min((col + 1) * cell_width, img_width)
                    
                    # Verificar ocupación de la celda
                    cell_occupation = occupation_map[top:bottom, left:right]
                    occupation_percentage = np.mean(cell_occupation)
                    
                    # Si menos del 20% está ocupado, considerar como espacio vacío
                    if occupation_percentage < 0.2:
                        empty_spaces.append({
                            'nivel': row + 1,
                            'posicion': col + 1,
                            'ocupacion_porcentaje': float(occupation_percentage * 100),
                            'coordenadas': {
                                'top': top / img_height,
                                'left': left / img_width,
                                'width': (right - left) / img_width,
                                'height': (bottom - top) / img_height
                            }
                        })
            
        except Exception as e:
            print(f"Error detecting empty spaces: {str(e)}")
        
        return empty_spaces
    
    def analyze_planogram_compliance(
        self,
        planogram_b64: str,
        realogram_b64: str,
        json_structure: Dict,
        confidence_threshold: int = 80,
        detect_text: bool = True,
        detect_labels: bool = True
    ) -> Dict[str, Any]:
        """
        Analiza el cumplimiento del planograma usando Rekognition
        """
        try:
            # Detectar objetos y texto
            detection_result = self.detect_objects_and_text(
                planogram_b64,
                realogram_b64,
                confidence_threshold
            )
            
            # Procesar estructura JSON con datos de Rekognition
            result = self._process_with_rekognition_data(
                json_structure,
                detection_result
            )
            
            # Agregar datos de Rekognition al resultado
            result['rekognition_data'] = detection_result
            
            return result
            
        except Exception as e:
            return {
                "error": f"Error en análisis Rekognition: {str(e)}",
                "diferencias": json_structure.get("diferencias", []),
                "conclusiones": [f"Error en el análisis: {str(e)}"]
            }
    
    def _process_with_rekognition_data(
        self,
        json_structure: Dict,
        rekognition_data: Dict
    ) -> Dict[str, Any]:
        """
        Procesa la estructura JSON usando los datos de Rekognition
        """
        result = {
            "diferencias": [],
            "conclusiones": []
        }
        
        # Mapear productos detectados por texto
        planogram_products = self._extract_product_names(rekognition_data['planogram_text'])
        realogram_products = self._extract_product_names(rekognition_data['realogram_text'])
        
        # Procesar cada nivel
        for nivel_data in json_structure.get("diferencias", []):
            nivel = nivel_data.get("nivel")
            productos_resultado = []
            
            for producto in nivel_data.get("resultado", {}).get("productos", []):
                nombre = producto.get("nombre", "")
                
                # Buscar producto en detecciones de Rekognition
                encontrado = self._find_product_in_detections(nombre, realogram_products)
                
                # Determinar posición (simplificado)
                posicion_correcta = encontrado  # Simplificación: si está, asumimos posición correcta
                
                # Estimar frentes (basado en instancias detectadas)
                frentes_encontrados = self._estimate_fronts(nombre, rekognition_data['realogram_objects'])
                
                productos_resultado.append({
                    "posicion_producto": producto.get("posicion_producto"),
                    "nombre": nombre,
                    "encontrado": encontrado,
                    "posicion_correcta": posicion_correcta,
                    "frentes_esperados": producto.get("frentes_esperados", 0),
                    "frentes_encontrados": frentes_encontrados
                })
            
            result["diferencias"].append({
                "nivel": nivel,
                "resultado": {"productos": productos_resultado}
            })
        
        # Generar conclusiones
        total_productos = sum(
            len(n.get("resultado", {}).get("productos", []))
            for n in result["diferencias"]
        )
        
        productos_encontrados = sum(
            sum(1 for p in n.get("resultado", {}).get("productos", []) if p.get("encontrado"))
            for n in result["diferencias"]
        )
        
        if rekognition_data['empty_spaces_count'] > 0:
            result["conclusiones"].append(
                f"Se detectaron {rekognition_data['empty_spaces_count']} espacios vacíos en la góndola"
            )
        
        if productos_encontrados < total_productos:
            result["conclusiones"].append(
                f"Se encontraron {productos_encontrados} de {total_productos} productos esperados"
            )
        
        if rekognition_data['total_text'] > 0:
            result["conclusiones"].append(
                f"Se detectaron {rekognition_data['total_text']} textos/marcas en las imágenes"
            )
        
        cumplimiento = (productos_encontrados / total_productos * 100) if total_productos > 0 else 0
        result["conclusiones"].append(f"Cumplimiento estimado por Rekognition: {cumplimiento:.1f}%")
        
        return result
    
    def _extract_product_names(self, text_detections: List[Dict]) -> List[str]:
        """
        Extrae nombres de productos de las detecciones de texto
        """
        product_names = []
        for text in text_detections:
            if text['Type'] == 'LINE':
                product_names.append(text['Text'].lower())
        return product_names
    
    def _find_product_in_detections(self, product_name: str, detected_products: List[str]) -> bool:
        """
        Busca un producto en las detecciones
        """
        product_lower = product_name.lower()
        
        # Extraer palabras clave del nombre del producto
        keywords = [word for word in product_lower.split() if len(word) > 3]
        
        for detected in detected_products:
            # Verificar si alguna palabra clave está en el producto detectado
            if any(keyword in detected for keyword in keywords):
                return True
        
        return False
    
    def _estimate_fronts(self, product_name: str, detected_objects: List[Dict]) -> int:
        """
        Estima el número de frentes basado en objetos detectados
        """
        # Buscar objetos que puedan corresponder al producto
        relevant_types = ['Bottle', 'Can', 'Package', 'Box', 'Container', 'Aerosol', 'Spray']
        
        count = 0
        for obj in detected_objects:
            if obj['Name'] in relevant_types:
                # Contar instancias como frentes
                count += len(obj.get('Instances', []))
        
        # Si no hay instancias específicas, usar un valor por defecto
        return max(count, 1) if count > 0 else 0
    
    def compare_shelf_occupancy(
        self,
        planogram_b64: str,
        realogram_b64: str
    ) -> Dict[str, Any]:
        """
        Compara la ocupación de estantes entre planograma y realograma
        """
        try:
            # Detectar objetos en ambas imágenes
            plan_objects = self._detect_labels(planogram_b64)
            real_objects = self._detect_labels(realogram_b64)
            
            # Calcular ocupación por niveles
            plan_occupation = self._calculate_shelf_occupation(planogram_b64, plan_objects)
            real_occupation = self._calculate_shelf_occupation(realogram_b64, real_objects)
            
            # Comparar ocupaciones
            comparison = {
                'planogram_occupation': plan_occupation,
                'realogram_occupation': real_occupation,
                'differences': []
            }
            
            for level in range(1, 7):  # Asumiendo 6 niveles
                plan_occ = plan_occupation.get(level, 0)
                real_occ = real_occupation.get(level, 0)
                
                if abs(plan_occ - real_occ) > 20:  # Diferencia significativa > 20%
                    comparison['differences'].append({
                        'nivel': level,
                        'planogram_ocupacion': plan_occ,
                        'realogram_ocupacion': real_occ,
                        'diferencia': real_occ - plan_occ
                    })
            
            return comparison
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_shelf_occupation(self, image_b64: str, detected_objects: List[Dict]) -> Dict[int, float]:
        """
        Calcula el porcentaje de ocupación por nivel de estante
        """
        occupation = {}
        
        try:
            # Convertir imagen para obtener dimensiones
            image = Image.open(io.BytesIO(base64.b64decode(image_b64)))
            img_height = image.size[1]
            
            # Dividir en 6 niveles
            level_height = img_height / 6
            
            for level in range(1, 7):
                level_top = (level - 1) * level_height / img_height
                level_bottom = level * level_height / img_height
                
                # Contar objetos en este nivel
                objects_in_level = 0
                for obj in detected_objects:
                    for instance in obj.get('Instances', []):
                        bbox = instance.get('BoundingBox', {})
                        if bbox:
                            obj_center_y = bbox.get('Top', 0) + bbox.get('Height', 0) / 2
                            if level_top <= obj_center_y <= level_bottom:
                                objects_in_level += 1
                
                # Estimar ocupación (simplificado)
                occupation[level] = min(objects_in_level * 10, 100)  # Cada objeto ~10% de ocupación
            
        except Exception as e:
            print(f"Error calculating occupation: {str(e)}")
        
        return occupation