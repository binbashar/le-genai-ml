import base64
from PIL import Image
import io
from typing import Dict, Any, List

def process_images(image_file) -> str:
    """Convert uploaded image to base64 with optimization"""
    # Read image
    image = Image.open(image_file)
    
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize if too large (max 2048x2048) while maintaining aspect ratio
    max_size = (2048, 2048)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Enhance image quality for better AI detection
    # Adjust contrast and brightness if needed
    from PIL import ImageEnhance
    
    # Enhance contrast slightly for better product detection
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.1)  # Slight contrast boost
    
    # Enhance sharpness for better text reading
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.2)  # Slight sharpness boost
    
    # Convert to base64 with high quality
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95, optimize=True)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

def calculate_metrics(result: Dict) -> Dict[str, Any]:
    """Calculate comprehensive compliance metrics from analysis result"""
    metrics = {
        "total": 0,
        "found": 0,
        "correct_position": 0,
        "wrong_position": 0,
        "missing": 0,
        "total_frentes_expected": 0,
        "total_frentes_found": 0,
        "recall": 0.0,
        "precision": 0.0,
        "position_accuracy": 0.0,
        "frentes_accuracy": 0.0,
        "overall_compliance": 0.0,
        "levels_analyzed": 0,
        "products_with_frente_issues": 0
    }
    
    if 'diferencias' not in result:
        return metrics
    
    metrics['levels_analyzed'] = len(result['diferencias'])
    
    for nivel in result['diferencias']:
        if 'resultado' in nivel and 'productos' in nivel['resultado']:
            for producto in nivel['resultado']['productos']:
                metrics['total'] += 1
                
                # Check if product was found
                if producto.get('encontrado', False):
                    metrics['found'] += 1
                    
                    # Check position
                    if producto.get('posicion_correcta', False):
                        metrics['correct_position'] += 1
                    else:
                        metrics['wrong_position'] += 1
                else:
                    metrics['missing'] += 1
                
                # Count frentes
                frentes_expected = producto.get('frentes_esperados', 0)
                frentes_found = producto.get('frentes_encontrados', 0)
                
                metrics['total_frentes_expected'] += frentes_expected
                metrics['total_frentes_found'] += frentes_found if frentes_found else 0
                
                # Check frente issues
                if frentes_expected != frentes_found and producto.get('encontrado', False):
                    metrics['products_with_frente_issues'] += 1
    
    # Calculate percentages
    if metrics['total'] > 0:
        metrics['recall'] = metrics['found'] / metrics['total']
        metrics['precision'] = metrics['correct_position'] / metrics['total']
        metrics['position_accuracy'] = metrics['correct_position'] / metrics['found'] if metrics['found'] > 0 else 0
        
        # Calculate overall compliance score (weighted average)
        found_weight = 0.4  # 40% weight for finding products
        position_weight = 0.4  # 40% weight for correct position
        frentes_weight = 0.2  # 20% weight for correct frentes
        
        found_score = metrics['recall'] * found_weight
        position_score = metrics['precision'] * position_weight
        
        if metrics['total_frentes_expected'] > 0:
            frentes_score = min(1.0, metrics['total_frentes_found'] / metrics['total_frentes_expected']) * frentes_weight
            metrics['frentes_accuracy'] = metrics['total_frentes_found'] / metrics['total_frentes_expected']
        else:
            frentes_score = frentes_weight  # Full score if no frentes to check
            metrics['frentes_accuracy'] = 1.0
        
        metrics['overall_compliance'] = found_score + position_score + frentes_score
    
    return metrics

def analyze_differences(result: Dict, expected: Dict = None) -> List[Dict]:
    """Analyze differences between planogram and realogram in detail"""
    analysis = []
    
    if 'diferencias' not in result:
        return analysis
    
    for nivel in result['diferencias']:
        nivel_analysis = {
            'nivel': nivel.get('nivel', 'Unknown'),
            'total_products': 0,
            'found': 0,
            'correct_position': 0,
            'missing_products': [],
            'wrong_position_products': [],
            'frentes_issues': [],
            'status': '✅ OK'
        }
        
        if 'resultado' in nivel and 'productos' in nivel['resultado']:
            productos = nivel['resultado']['productos']
            nivel_analysis['total_products'] = len(productos)
            
            for producto in productos:
                nombre = producto.get('nombre', 'Sin nombre')
                posicion = producto.get('posicion_producto', 0)
                
                # Check if found
                if producto.get('encontrado', False):
                    nivel_analysis['found'] += 1
                    
                    # Check position
                    if producto.get('posicion_correcta', False):
                        nivel_analysis['correct_position'] += 1
                    else:
                        nivel_analysis['wrong_position_products'].append(
                            f"{nombre} (posición {posicion})"
                        )
                else:
                    nivel_analysis['missing_products'].append(nombre)
                
                # Check frentes
                frentes_esperados = producto.get('frentes_esperados', 0)
                frentes_encontrados = producto.get('frentes_encontrados', 0)
                
                if frentes_esperados != frentes_encontrados and producto.get('encontrado', False):
                    nivel_analysis['frentes_issues'].append(
                        f"{nombre}: {frentes_encontrados}/{frentes_esperados} frentes"
                    )
            
            # Determine status
            if nivel_analysis['missing_products']:
                nivel_analysis['status'] = '❌ Productos faltantes'
            elif nivel_analysis['wrong_position_products']:
                nivel_analysis['status'] = '⚠️ Productos mal posicionados'
            elif nivel_analysis['frentes_issues']:
                nivel_analysis['status'] = '📊 Diferencias en frentes'
            else:
                nivel_analysis['status'] = '✅ Completo'
        
        analysis.append(nivel_analysis)
    
    return analysis

def validate_product_match(product_name: str, found_name: str) -> bool:
    """Validate if two product names match (accounting for variations)"""
    # Normalize names for comparison
    name1 = product_name.lower().strip()
    name2 = found_name.lower().strip()
    
    # Exact match
    if name1 == name2:
        return True
    
    # Check if one contains the other (for partial matches)
    if name1 in name2 or name2 in name1:
        return True
    
    # Check for common variations
    # Remove common size variations
    sizes = ['500ml', '1l', '1.5l', '2l', '330ml', '355ml', '473ml', '750ml']
    for size in sizes:
        name1 = name1.replace(size, '')
        name2 = name2.replace(size, '')
    
    # Remove common words
    common_words = ['cerveza', 'beer', 'lata', 'botella', 'can', 'bottle']
    for word in common_words:
        name1 = name1.replace(word, '')
        name2 = name2.replace(word, '')
    
    # Check again after normalization
    name1 = ' '.join(name1.split())  # Normalize spaces
    name2 = ' '.join(name2.split())
    
    if name1 == name2:
        return True
    
    # Calculate similarity (simple approach)
    words1 = set(name1.split())
    words2 = set(name2.split())
    
    if words1 and words2:
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        similarity = len(intersection) / len(union)
        
        # If more than 70% similar, consider it a match
        if similarity > 0.7:
            return True
    
    return False

def generate_compliance_report(result: Dict, metrics: Dict) -> str:
    """Generate a text compliance report"""
    report = []
    report.append("=" * 50)
    report.append("REPORTE DE CUMPLIMIENTO DE PLANOGRAMA")
    report.append("=" * 50)
    report.append("")
    
    # Overall metrics
    report.append("MÉTRICAS GENERALES:")
    report.append(f"• Cumplimiento General: {metrics['overall_compliance']:.1%}")
    report.append(f"• Productos Encontrados: {metrics['found']}/{metrics['total']} ({metrics['recall']:.1%})")
    report.append(f"• Posiciones Correctas: {metrics['correct_position']}/{metrics['total']} ({metrics['precision']:.1%})")
    report.append(f"• Precisión de Frentes: {metrics['frentes_accuracy']:.1%}")
    report.append("")
    
    # Issues summary
    if metrics['missing'] > 0:
        report.append(f"⚠️ PRODUCTOS FALTANTES: {metrics['missing']}")
    if metrics['wrong_position'] > 0:
        report.append(f"⚠️ PRODUCTOS MAL POSICIONADOS: {metrics['wrong_position']}")
    if metrics['products_with_frente_issues'] > 0:
        report.append(f"⚠️ PRODUCTOS CON DIFERENCIAS EN FRENTES: {metrics['products_with_frente_issues']}")
    report.append("")
    
    # Detailed analysis by level
    if 'diferencias' in result:
        report.append("ANÁLISIS POR NIVEL:")
        report.append("-" * 30)
        
        for nivel in result['diferencias']:
            nivel_id = nivel.get('nivel', 'Unknown')
            report.append(f"\nNivel {nivel_id}:")
            
            if 'resultado' in nivel and 'productos' in nivel['resultado']:
                for producto in nivel['resultado']['productos']:
                    nombre = producto.get('nombre', 'Sin nombre')
                    encontrado = "✓" if producto.get('encontrado', False) else "✗"
                    posicion = "✓" if producto.get('posicion_correcta', False) else "✗"
                    frentes = f"{producto.get('frentes_encontrados', 0)}/{producto.get('frentes_esperados', 0)}"
                    
                    report.append(f"  • {nombre}")
                    report.append(f"    Encontrado: {encontrado} | Posición: {posicion} | Frentes: {frentes}")
    
    # Conclusions
    if 'conclusiones' in result and result['conclusiones']:
        report.append("")
        report.append("CONCLUSIONES:")
        report.append("-" * 30)
        for i, conclusion in enumerate(result['conclusiones'], 1):
            report.append(f"{i}. {conclusion}")
    
    report.append("")
    report.append("=" * 50)
    
    return "\n".join(report)