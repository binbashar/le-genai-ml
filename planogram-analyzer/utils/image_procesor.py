import base64
from PIL import Image
import io
from typing import Dict, Any

def process_images(image_file) -> str:
    """Convert uploaded image to base64"""
    # Read image
    image = Image.open(image_file)
    
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize if too large (max 2048x2048)
    max_size = (2048, 2048)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Convert to base64
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

def calculate_metrics(result: Dict) -> Dict[str, Any]:
    """Calculate compliance metrics from analysis result"""
    metrics = {
        "total": 0,
        "found": 0,
        "correct_position": 0,
        "missing": 0,
        "recall": 0.0,
        "precision": 0.0
    }
    
    if 'diferencias' not in result:
        return metrics
    
    for nivel in result['diferencias']:
        if 'resultado' in nivel and 'productos' in nivel['resultado']:
            for producto in nivel['resultado']['productos']:
                metrics['total'] += 1
                
                if producto.get('encontrado', False):
                    metrics['found'] += 1
                    
                if producto.get('posicion_correcta', False):
                    metrics['correct_position'] += 1
                    
                if not producto.get('encontrado', False):
                    metrics['missing'] += 1
    
    # Calculate recall and precision
    if metrics['total'] > 0:
        metrics['recall'] = metrics['found'] / metrics['total']
        metrics['precision'] = metrics['correct_position'] / metrics['total'] if metrics['total'] > 0 else 0
    
    return metrics