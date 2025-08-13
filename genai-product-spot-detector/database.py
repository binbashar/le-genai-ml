import os
import json
import psycopg2
import psycopg2.extras
from sqlalchemy import create_engine, text
from datetime import datetime

# Conexión a la base de datos
def get_db_connection():
    """
    Establece una conexión con la base de datos PostgreSQL
    
    Returns:
        conn: Objeto de conexión a la base de datos
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT")
        )
        return conn
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

def get_sqlalchemy_engine():
    """
    Crea un motor SQLAlchemy para la conexión a la base de datos
    
    Returns:
        engine: Objeto de motor SQLAlchemy
    """
    try:
        db_url = os.getenv("DATABASE_URL")
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        print(f"Error al crear el motor SQLAlchemy: {e}")
        return None

def guardar_analisis(nombre_planograma, nombre_realograma, json_respuesta):
    """
    Guarda los resultados del análisis en la base de datos
    
    Args:
        nombre_planograma: Nombre del archivo de planograma
        nombre_realograma: Nombre del archivo de realograma
        json_respuesta: Respuesta JSON del análisis
    
    Returns:
        id_analisis: ID del análisis guardado o None si hubo un error
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        # Calcular el porcentaje de cumplimiento
        porcentaje_cumplimiento = calcular_porcentaje_cumplimiento(json_respuesta)
        
        # Convertir la respuesta JSON a string si es un diccionario
        if isinstance(json_respuesta, dict):
            json_respuesta = json.dumps(json_respuesta)
            
        # Crear el cursor y ejecutar la inserción
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO analisis 
            (nombre_planograma, nombre_realograma, json_respuesta, porcentaje_cumplimiento)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (nombre_planograma, nombre_realograma, json_respuesta, porcentaje_cumplimiento)
        )
        
        id_analisis = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return id_analisis
    except Exception as e:
        print(f"Error al guardar el análisis: {e}")
        if conn:
            conn.close()
        return None

def calcular_porcentaje_cumplimiento(json_respuesta):
    """
    Calcula el porcentaje de cumplimiento basado en los productos encontrados y en posición correcta
    
    Args:
        json_respuesta: Respuesta JSON del análisis
    
    Returns:
        porcentaje: Porcentaje de cumplimiento calculado
    """
    if isinstance(json_respuesta, str):
        try:
            json_respuesta = json.loads(json_respuesta)
        except:
            return 0.0
    
    total_productos = 0
    productos_cumplidos = 0
    
    # Recorrer todas las diferencias y sus productos
    for diferencia in json_respuesta.get("diferencias", []):
        productos = diferencia.get("resultado", {}).get("productos", [])
        
        for producto in productos:
            total_productos += 1
            if producto.get("encontrado", False) and producto.get("posicion_correcta", False):
                # Si el producto fue encontrado y está en la posición correcta
                frentes_esperados = producto.get("frentes_esperados", 0)
                frentes_encontrados = producto.get("frentes_encontrados", 0)
                
                # Si tiene al menos el 80% de los frentes esperados, lo consideramos como cumplido
                if frentes_esperados > 0 and frentes_encontrados >= 0.8 * frentes_esperados:
                    productos_cumplidos += 1
    
    # Calcular el porcentaje
    if total_productos > 0:
        porcentaje = (productos_cumplidos / total_productos) * 100
    else:
        porcentaje = 0.0
        
    return round(porcentaje, 2)

def obtener_analisis_recientes(limit=5):
    """
    Obtiene los análisis más recientes de la base de datos
    
    Args:
        limit: Número máximo de análisis a retornar
    
    Returns:
        analisis: Lista de análisis recientes
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        # Crear el cursor y ejecutar la consulta
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT id, fecha_analisis, nombre_planograma, nombre_realograma, porcentaje_cumplimiento
            FROM analisis
            ORDER BY fecha_analisis DESC
            LIMIT %s
            """,
            (limit,)
        )
        
        analisis = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convertir los resultados a una lista de diccionarios
        resultados = []
        for a in analisis:
            resultados.append(dict(a))
            
        return resultados
    except Exception as e:
        print(f"Error al obtener los análisis recientes: {e}")
        if conn:
            conn.close()
        return []

def obtener_detalle_analisis(id_analisis):
    """
    Obtiene los detalles de un análisis específico
    
    Args:
        id_analisis: ID del análisis a obtener
    
    Returns:
        detalle: Diccionario con los detalles del análisis o None si no existe
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        # Crear el cursor y ejecutar la consulta
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            """
            SELECT id, fecha_analisis, nombre_planograma, nombre_realograma, 
                   json_respuesta, porcentaje_cumplimiento
            FROM analisis
            WHERE id = %s
            """,
            (id_analisis,)
        )
        
        analisis = cur.fetchone()
        cur.close()
        conn.close()
        
        if analisis:
            # Convertir a diccionario y parsear el JSON
            resultado = dict(analisis)
            if isinstance(resultado['json_respuesta'], str):
                try:
                    resultado['json_respuesta'] = json.loads(resultado['json_respuesta'])
                except:
                    pass
            return resultado
        
        return None
    except Exception as e:
        print(f"Error al obtener los detalles del análisis: {e}")
        if conn:
            conn.close()
        return None