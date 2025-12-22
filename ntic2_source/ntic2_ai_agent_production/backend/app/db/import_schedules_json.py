"""
Script pour importer les données d'emploi du temps depuis un JSON
Remplace toutes les données existantes par les nouvelles données
"""
import json
from pathlib import Path
from app.db.database import get_db_connection

# Mapping des heures vers session_num basé sur les plages horaires
# SEANCE1: 08:30 - 10:00 -> session_num = 1
# SEANCE2: 10:30 - 13:00 -> session_num = 2
# SEANCE3: 13:30 - 16:00 -> session_num = 3
# SEANCE4: 16:00 - 18:30 -> session_num = 4

def get_session_num_from_heure(heure_debut):
    """Détermine le numéro de session basé sur l'heure de début"""
    if not heure_debut:
        return None
    
    # Extraire l'heure (format HH:MM)
    try:
        hour, minute = map(int, heure_debut.split(':'))
        total_minutes = hour * 60 + minute
        
        # Mapping basé sur les plages horaires
        if 480 <= total_minutes < 600:  # 08:00 - 10:00
            return 1
        elif 600 <= total_minutes < 780:  # 10:00 - 13:00
            return 2
        elif 780 <= total_minutes < 960:  # 13:00 - 16:00
            return 3
        elif 960 <= total_minutes < 1140:  # 16:00 - 19:00
            return 4
        else:
            # Par défaut, essayer de deviner
            if total_minutes < 600:
                return 1
            elif total_minutes < 780:
                return 2
            elif total_minutes < 960:
                return 3
            else:
                return 4
    except:
        return None

def get_or_create_groupe(cur, code):
    """Récupère ou crée un groupe"""
    cur.execute("SELECT id FROM groupes WHERE code = %s", (code,))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute("INSERT INTO groupes (code) VALUES (%s) RETURNING id", (code,))
    return cur.fetchone()[0]

def get_or_create_formateur(cur, nom):
    """Récupère ou crée un formateur"""
    if not nom or nom.strip() == "":
        return None
    cur.execute("SELECT id FROM formateurs WHERE nom = %s", (nom,))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute("INSERT INTO formateurs (nom) VALUES (%s) RETURNING id", (nom,))
    return cur.fetchone()[0]

def get_or_create_module(cur, nom):
    """Récupère ou crée un module"""
    if not nom or nom.strip() == "":
        return None
    cur.execute("SELECT id FROM modules WHERE nom = %s", (nom,))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute("INSERT INTO modules (nom) VALUES (%s) RETURNING id", (nom,))
    return cur.fetchone()[0]

def get_or_create_salle(cur, code):
    """Récupère ou crée une salle"""
    if not code or code.strip() == "":
        return None
    
    # Déterminer le type de salle
    salle_type = None
    code_upper = code.upper()
    if code_upper == "TEAM":
        salle_type = "TEAM"
    elif code_upper.startswith("SP"):
        salle_type = "SP"
    elif code_upper.startswith("SC"):
        salle_type = "SC"
    elif code_upper.startswith("LABO"):
        salle_type = "LABO"
    elif code_upper == "AMPHI":
        salle_type = "AMPHI"
    elif code_upper.startswith("SEM"):
        salle_type = "SEM"
    elif code_upper == "OLMS":
        salle_type = "OLMS"
    elif code_upper == "COWORKING":
        salle_type = "COWORKING"
    
    cur.execute("SELECT id FROM salles WHERE code = %s", (code,))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute("INSERT INTO salles (code, type) VALUES (%s, %s) RETURNING id", (code, salle_type))
    return cur.fetchone()[0]

def parse_heure(heure_str):
    """Parse une chaîne d'heure "08:30 - 10:00" en (heure_debut, heure_fin)"""
    if not heure_str or "-" not in heure_str:
        return None, None
    parts = heure_str.split("-")
    if len(parts) != 2:
        return None, None
    heure_debut = parts[0].strip()
    heure_fin = parts[1].strip()
    return heure_debut, heure_fin

def import_schedules_from_json(json_data):
    """
    Importe les données d'emploi du temps depuis un dictionnaire JSON
    
    Args:
        json_data: Dictionnaire avec les données JSON
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except Exception as e:
        print(f"[ERROR] Erreur de connexion a PostgreSQL: {e}")
        raise
        # Créer les tables si elles n'existent pas
        schema_path = Path(__file__).parent / 'schedule_schema.sql'
        if schema_path.exists():
            # Essayer différents encodages pour le fichier SQL
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            schema_sql = None
            for encoding in encodings:
                try:
                    with open(schema_path, 'r', encoding=encoding) as f:
                        schema_sql = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            if schema_sql is None:
                # Dernier recours : lire en mode binaire et décoder avec errors='ignore'
                with open(schema_path, 'rb') as f:
                    schema_sql = f.read().decode('utf-8', errors='ignore')
                for command in schema_sql.split(';'):
                    command = command.strip()
                    if command:
                        try:
                            cur.execute(command)
                        except Exception as e:
                            if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                                print(f"Warning: {e}")
        
        # Vider les tables existantes pour réinsérer
        print("Vidage des tables existantes...")
        cur.execute("TRUNCATE TABLE sessions_cours CASCADE")
        cur.execute("TRUNCATE TABLE groupes CASCADE")
        cur.execute("TRUNCATE TABLE formateurs CASCADE")
        cur.execute("TRUNCATE TABLE modules CASCADE")
        cur.execute("TRUNCATE TABLE salles CASCADE")
        
        print("Insertion des nouvelles données...")
        
        # Extraire les données
        groupes_data = json_data.get("groupes", [])
        jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
        
        total_sessions = 0
        
        # Parcourir chaque groupe
        for groupe_data in groupes_data:
            groupe_code = groupe_data.get("groupe", "")
            filiere = groupe_data.get("filiere", "")
            if not groupe_code:
                continue
            
            print(f"  Traitement du groupe: {groupe_code} (Filière: {filiere})")
            groupe_id = get_or_create_groupe(cur, groupe_code)
            
            # Mettre à jour la description du groupe avec la filière si disponible
            if filiere:
                cur.execute("UPDATE groupes SET description = %s WHERE id = %s", (f"Filière: {filiere}", groupe_id))
            
            # Nouveau format : "cours" au lieu de "emploi_du_temps"
            cours_list = groupe_data.get("cours", [])
            if not cours_list:
                # Ancien format : "emploi_du_temps" avec jours spécifiques
                emploi_du_temps = groupe_data.get("emploi_du_temps", [])
                if emploi_du_temps:
                    # Traiter l'ancien format
                    for session_data in emploi_du_temps:
                        jour = session_data.get("jour", "")
                        seance = session_data.get("seance", "")
                        heure = session_data.get("heure", "")
                        module = session_data.get("module", "")
                        formateur = session_data.get("formateur", "")
                        salle = session_data.get("salle", "")
                        
                        # Parser l'heure
                        heure_debut, heure_fin = parse_heure(heure)
                        if not heure_debut or not heure_fin:
                            continue
                        
                        # Déterminer le numéro de session basé sur l'heure de début
                        session_num = get_session_num_from_heure(heure_debut)
                        if not session_num:
                            continue
                        
                        # Récupérer ou créer les entités
                        formateur_id = get_or_create_formateur(cur, formateur) if formateur else None
                        module_id = get_or_create_module(cur, module) if module else None
                        salle_id = get_or_create_salle(cur, salle) if salle else None
                        
                        # Insérer la session
                        cur.execute("""
                            INSERT INTO sessions_cours 
                            (groupe_id, formateur_id, module_id, salle_id, jour, session_num, heure_debut, heure_fin)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (groupe_id, formateur_id, module_id, salle_id, jour, session_num, heure_debut, heure_fin))
                        
                        total_sessions += 1
                continue
            
            # Nouveau format : chaque cours est assigné à tous les jours de la semaine
            for cours in cours_list:
                module = cours.get("module", "")
                formateur = cours.get("formateur", "")
                salle = cours.get("salle", "")
                heure = cours.get("heure", "")
                
                # Parser l'heure
                heure_debut, heure_fin = parse_heure(heure)
                if not heure_debut or not heure_fin:
                    print(f"    [WARN] Impossible de parser l'heure: {heure}, ignoree")
                    continue
                
                # Déterminer le numéro de session basé sur l'heure de début
                session_num = get_session_num_from_heure(heure_debut)
                if not session_num:
                    print(f"    [WARN] Impossible de determiner la session pour {heure_debut}, ignoree")
                    continue
                
                # Récupérer ou créer les entités
                formateur_id = get_or_create_formateur(cur, formateur) if formateur else None
                module_id = get_or_create_module(cur, module) if module else None
                salle_id = get_or_create_salle(cur, salle) if salle else None
                
                # Assigner ce cours à chaque jour de la semaine
                for jour in jours_semaine:
                    # Insérer la session pour chaque jour
                    cur.execute("""
                        INSERT INTO sessions_cours 
                        (groupe_id, formateur_id, module_id, salle_id, jour, session_num, heure_debut, heure_fin)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (groupe_id, formateur_id, module_id, salle_id, jour, session_num, heure_debut, heure_fin))
                    
                    total_sessions += 1
        
        conn.commit()
        print(f"\n[SUCCESS] {total_sessions} sessions inserees avec succes!")
        
        # Afficher les statistiques
        cur.execute("SELECT COUNT(*) FROM groupes")
        nb_groupes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sessions_cours")
        nb_sessions = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM formateurs")
        nb_formateurs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM modules")
        nb_modules = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM salles")
        nb_salles = cur.fetchone()[0]
        
        print(f"\n[STATS] Statistiques:")
        print(f"  - Groupes: {nb_groupes}")
        print(f"  - Sessions: {nb_sessions}")
        print(f"  - Formateurs: {nb_formateurs}")
        print(f"  - Modules: {nb_modules}")
        print(f"  - Salles: {nb_salles}")
        
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        import traceback
        print(f"[ERROR] Erreur lors de l'importation: {e}")
        print(f"Details: {traceback.format_exc()}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    # Charger depuis le fichier JSON si disponible, sinon utiliser les données inline
    json_file = Path(__file__).parent / 'schedules_data.json'
    if json_file.exists():
        print(f"[INFO] Chargement des donnees depuis: {json_file}")
        # Essayer différents encodages
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        json_data = None
        for encoding in encodings:
            try:
                with open(json_file, 'r', encoding=encoding) as f:
                    json_data = json.load(f)
                print(f"[OK] Fichier charge avec l'encodage: {encoding}")
                break
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                continue
        
        if json_data is None:
            raise Exception("Impossible de décoder le fichier JSON avec les encodages testés")
    else:
        print("⚠️ Fichier schedules_data.json non trouvé, utilisation des données inline")
        # Données JSON par défaut (fallback)
        json_data = {
            "date": "2025-12-22",
            "jours": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"],
            "seances_definitions": {
                "SEANCE1": "08:30 - 10:00",
                "SEANCE2": "10:30 - 13:00",
                "SEANCE3": "13:30 - 16:00",
                "SEANCE4": "16:00 - 18:30"
            },
            "groupes": []
        }
    
    try:
        import_schedules_from_json(json_data)
        print("\n[SUCCESS] Importation terminee avec succes!")
    except Exception as e:
        print(f"\n[ERROR] Erreur lors de l'importation: {e}")
        print("\n[INFO] Assurez-vous que PostgreSQL est demarre:")
        print("   - Local: Demarrez PostgreSQL")
        print("   - Docker: docker-compose up -d postgres")
        sys.exit(1)

