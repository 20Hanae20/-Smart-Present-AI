import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pathlib import Path

# Charger les variables d'environnement depuis .env à la racine du projet
# (au cas où ce module serait importé directement sans passer par main.py)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

def get_db_connection():
    # Utiliser localhost pour l'exécution locale, "postgres" pour Docker
    db_host = os.environ.get("POSTGRES_HOST", "postgres")
    
    # Détection simplifiée de l'environnement
    if db_host == "postgres":
        try:
            import socket
            socket.gethostbyname("postgres")
        except socket.gaierror:
            db_host = "localhost"
    
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    password = os.environ.get("POSTGRES_PASSWORD", "ntic")
    
    try:
        # Tenter la connexion
        conn = psycopg2.connect(
            host=db_host,
            port=port,
            database=os.environ.get("POSTGRES_DB", "ntic2"),
            user=os.environ.get("POSTGRES_USER", "ntic"),
            password=password,
            connect_timeout=3
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        # En cas d'échec, on ne crash pas l'application entière
        try:
            error_msg = str(e)
        except UnicodeDecodeError:
            # Gestion spécifique pour Windows où les messages d'erreur système 
            # peuvent utiliser un encodage non-UTF8 (CP1252) avec des accents
            error_msg = "Erreur de connexion (problème d'encodage du message d'erreur Windows)"
            
        print(f"⚠️ DATABASE WARNING: {error_msg}. Utilisation du mode sans base de données.")
        return None

def query_db(query, args=(), one=False):
    """Exécute une requête SQL avec résilience intégrée"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return None if one else []
            
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, args)
        
        # Pour les SELECT, on récupère les données
        if query.strip().upper().startswith("SELECT"):
            rv = cur.fetchall()
            result = (rv[0] if rv else None) if one else rv
        else:
            # Pour INSERT/UPDATE, on valide
            conn.commit()
            result = True
            
        cur.close()
        conn.close()
        return result
    except Exception as e:
        if conn:
            try: conn.close()
            except: pass
        print(f"❌ Erreur lors de l'exécution de la requête: {e}")
        return None if one else []
