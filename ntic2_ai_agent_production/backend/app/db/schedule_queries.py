"""
Module pour interroger les emplois du temps
"""
import logging
from app.db.database import query_db, get_db_connection
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_schedule_by_groupe(groupe_code: str) -> List[Dict]:
    """Récupère l'emploi du temps d'un groupe"""
    try:
        result = query_db("""
            SELECT * FROM vue_emploi_temps 
            WHERE groupe_code = %s 
            ORDER BY 
                CASE jour
                    WHEN 'Lundi' THEN 1
                    WHEN 'Mardi' THEN 2
                    WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4
                    WHEN 'Vendredi' THEN 5
                    WHEN 'Samedi' THEN 6
                END,
                session_num
        """, (groupe_code,))
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération de l'emploi du temps pour {groupe_code}: {e}")
        return []

def get_schedule_by_formateur(formateur_nom: str) -> List[Dict]:
    """Récupère l'emploi du temps d'un formateur"""
    try:
        result = query_db("""
            SELECT * FROM vue_emploi_temps 
            WHERE formateur_nom = %s 
            ORDER BY 
                CASE jour
                    WHEN 'Lundi' THEN 1
                    WHEN 'Mardi' THEN 2
                    WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4
                    WHEN 'Vendredi' THEN 5
                    WHEN 'Samedi' THEN 6
                END,
                session_num
        """, (formateur_nom,))
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération de l'emploi du temps pour {formateur_nom}: {e}")
        return []

def get_schedule_by_salle(salle_code: str) -> List[Dict]:
    """Récupère l'emploi du temps d'une salle"""
    try:
        result = query_db("""
            SELECT * FROM vue_emploi_temps 
            WHERE salle_code = %s 
            ORDER BY 
                CASE jour
                    WHEN 'Lundi' THEN 1
                    WHEN 'Mardi' THEN 2
                    WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4
                    WHEN 'Vendredi' THEN 5
                    WHEN 'Samedi' THEN 6
                END,
                session_num
        """, (salle_code,))
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération de l'emploi du temps pour la salle {salle_code}: {e}")
        return []

def get_schedule_by_module(module_nom: str) -> List[Dict]:
    """Récupère l'emploi du temps d'un module"""
    try:
        result = query_db("""
            SELECT * FROM vue_emploi_temps 
            WHERE module_nom LIKE %s 
            ORDER BY 
                CASE jour
                    WHEN 'Lundi' THEN 1
                    WHEN 'Mardi' THEN 2
                    WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4
                    WHEN 'Vendredi' THEN 5
                    WHEN 'Samedi' THEN 6
                END,
                session_num
        """, (f'%{module_nom}%',))
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération de l'emploi du temps pour le module {module_nom}: {e}")
        return []

def get_schedule_by_jour(jour: str) -> List[Dict]:
    """Récupère l'emploi du temps d'un jour"""
    try:
        result = query_db("""
            SELECT * FROM vue_emploi_temps 
            WHERE jour = %s 
            ORDER BY session_num, groupe_code
        """, (jour,))
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération de l'emploi du temps pour {jour}: {e}")
        return []

def get_schedule_by_jour_and_session(jour: str, session_num: int) -> List[Dict]:
    """Récupère l'emploi du temps pour un jour et une session spécifiques"""
    try:
        result = query_db("""
            SELECT * FROM vue_emploi_temps 
            WHERE jour = %s AND session_num = %s
            ORDER BY groupe_code
        """, (jour, session_num))
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération de l'emploi du temps pour {jour} session {session_num}: {e}")
        return []

def search_schedules(groupe_code: Optional[str] = None, 
                     formateur_nom: Optional[str] = None,
                     module_nom: Optional[str] = None,
                     salle_code: Optional[str] = None,
                     jour: Optional[str] = None) -> List[Dict]:
    """Recherche avancée dans les emplois du temps"""
    try:
        conditions = []
        params = []
        
        if groupe_code:
            conditions.append("groupe_code = %s")
            params.append(groupe_code)
        if formateur_nom:
            conditions.append("formateur_nom = %s")
            params.append(formateur_nom)
        if module_nom:
            conditions.append("module_nom LIKE %s")
            params.append(f'%{module_nom}%')
        if salle_code:
            conditions.append("salle_code = %s")
            params.append(salle_code)
        if jour:
            conditions.append("jour = %s")
            params.append(jour)
        
        if not conditions:
            return []
        
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT * FROM vue_emploi_temps 
            WHERE {where_clause}
            ORDER BY 
                CASE jour
                    WHEN 'Lundi' THEN 1
                    WHEN 'Mardi' THEN 2
                    WHEN 'Mercredi' THEN 3
                    WHEN 'Jeudi' THEN 4
                    WHEN 'Vendredi' THEN 5
                    WHEN 'Samedi' THEN 6
                END,
                session_num
        """
        
        result = query_db(query, tuple(params))
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la recherche d'emplois du temps: {e}")
        return []

def get_all_groupes() -> List[Dict]:
    """Récupère tous les groupes"""
    try:
        result = query_db("SELECT code, description FROM groupes ORDER BY code")
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération des groupes: {e}")
        return []

def get_all_formateurs() -> List[Dict]:
    """Récupère tous les formateurs"""
    try:
        result = query_db("SELECT nom FROM formateurs ORDER BY nom")
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération des formateurs: {e}")
        return []

def get_all_modules() -> List[Dict]:
    """Récupère tous les modules"""
    try:
        result = query_db("SELECT DISTINCT nom FROM modules ORDER BY nom")
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération des modules: {e}")
        return []

def get_all_salles() -> List[Dict]:
    """Récupère toutes les salles"""
    try:
        result = query_db("SELECT code, type, description FROM salles ORDER BY code")
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération des salles: {e}")
        return []

def get_conflicts() -> List[Dict]:
    """Détecte les conflits d'emploi du temps (même salle, même jour, même session)"""
    try:
        result = query_db("""
            SELECT 
                jour,
                session_num,
                salle_code,
                COUNT(*) as nb_conflicts,
                STRING_AGG(groupe_code, ', ') as groupes
            FROM vue_emploi_temps
            WHERE salle_code IS NOT NULL
            GROUP BY jour, session_num, salle_code
            HAVING COUNT(*) > 1
            ORDER BY jour, session_num
        """)
        return result if result else []
    except Exception as e:
        logger.warning(f"Erreur lors de la détection des conflits: {e}")
        return []

def format_schedule_response(schedules: List[Dict]) -> str:
    """Formate une réponse lisible à partir des résultats de requête"""
    if not schedules:
        return "Aucun résultat trouvé."
    
    # Grouper par jour et session pour un affichage plus organisé
    result = []
    current_day = None
    current_session = None
    
    for s in schedules:
        jour = s.get('jour', 'N/A')
        session_num = s.get('session_num', 0)
        heure_debut = s.get('heure_debut', '')
        heure_fin = s.get('heure_fin', '')
        formateur = s.get('formateur_nom', 'N/A')
        module = s.get('module_nom', 'N/A')
        salle = s.get('salle_code', 'N/A')
        notes = s.get('notes', '')
        groupe = s.get('groupe_code', 'N/A')
        
        # Si c'est un nouveau jour, ajouter un séparateur
        if jour != current_day:
            if current_day is not None:
                result.append("")  # Ligne vide entre les jours
            result.append(f"### 📅 {jour}")
            current_day = jour
            current_session = None
        
        # Si c'est une nouvelle session, ajouter l'en-tête de session
        if session_num != current_session:
            heure_str = f"{heure_debut} - {heure_fin}" if heure_debut and heure_fin else f"Séance {session_num}"
            result.append(f"\n**🕐 {heure_str}**")
            current_session = session_num
        
        # Ajouter les détails de la session (toujours afficher formateur, module et salle)
        # Format plus structuré et lisible
        session_details = []
        
        # Formateur (professeur)
        if formateur and formateur != 'N/A':
            session_details.append(f"  👤 **Formateur (Professeur):** {formateur}")
        else:
            session_details.append(f"  👤 **Formateur (Professeur):** Non spécifié")
        
        # Module (cours)
        if module and module != 'N/A':
            session_details.append(f"  📚 **Module (Cours):** {module}")
        else:
            session_details.append(f"  📚 **Module (Cours):** Non spécifié")
        
        # Salle
        if salle and salle != 'N/A':
            salle_str = f"  🏢 **Salle:** {salle}"
            if notes:
                salle_str += f" ({notes})"
            session_details.append(salle_str)
        else:
            session_details.append(f"  🏢 **Salle:** Non spécifiée")
        
        # Ajouter les détails avec un format plus lisible (une ligne par détail)
        result.append("\n".join(session_details))
    
    return "\n".join(result)

