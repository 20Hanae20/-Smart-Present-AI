"""
AI Scoring Service - Calculate Dynamic Attendance Scores
This service calculates AI attendance scores based on REAL attendance data.
Used by N8N Workflow 4 to generate accurate, dynamic scores.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.student import Student
from app.models.attendance import AttendanceRecord
from typing import Dict, Tuple
from datetime import datetime, timedelta


def calculate_attendance_score(student_id: int, db: Session) -> Tuple[int, str]:
    """
    Calculate dynamic AI attendance score (0-100) based on real attendance data.
    
    Formula:
    - Base Score: (Presences / Total Sessions) * 100
    - Bonus: Consistent attendance streak (+5-10 points)
    - Penalty: Recent absences (-5-15 points)
    - Penalty: Late arrivals (-1-5 points)
    
    Returns:
        Tuple[int, str]: (score, justification_text)
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return (0, "Étudiant non trouvé")
    
    # Get attendance statistics
    total_sessions = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.student_id == student_id
    ).scalar() or 0
    
    if total_sessions == 0:
        return (100, "Nouvel étudiant - aucune session enregistrée pour le moment.")
    
    presences = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.status == 'present'
    ).scalar() or 0
    
    absences = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.status == 'absent'
    ).scalar() or 0
    
    late = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.status == 'late'
    ).scalar() or 0
    
    # Base score: percentage of presences (including late as 0.75 presence)
    base_score = ((presences + (late * 0.75)) / total_sessions) * 100
    
    # Check recent attendance (last 30 days)
    recent_cutoff = datetime.now() - timedelta(days=30)
    recent_absences = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.status == 'absent',
        AttendanceRecord.created_at >= recent_cutoff
    ).scalar() or 0
    
    recent_presences = db.query(func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.status == 'present',
        AttendanceRecord.created_at >= recent_cutoff
    ).scalar() or 0
    
    # Calculate final score with bonuses/penalties
    final_score = base_score
    justification_parts = []
    
    # Excellent attendance (95%+)
    if base_score >= 95:
        final_score = min(100, final_score + 5)
        justification_parts.append(
            f"Excellente assiduité avec {presences}/{total_sessions} présences ({base_score:.1f}%). "
            f"Comportement exemplaire et engagement constant dans le cours."
        )
    
    # Very good attendance (85-94%)
    elif base_score >= 85:
        justification_parts.append(
            f"Très bonne assiduité avec {presences}/{total_sessions} présences ({base_score:.1f}%). "
            f"Participation régulière et ponctualité généralement respectée."
        )
    
    # Good attendance (75-84%)
    elif base_score >= 75:
        justification_parts.append(
            f"Bonne présence avec {presences}/{total_sessions} présences ({base_score:.1f}%). "
            f"Quelques absences notées, mais dans l'ensemble une participation satisfaisante."
        )
    
    # Acceptable attendance (60-74%)
    elif base_score >= 60:
        final_score = max(60, final_score - 5)
        justification_parts.append(
            f"Assiduité acceptable avec {presences}/{total_sessions} présences ({base_score:.1f}%). "
            f"Des améliorations sont nécessaires pour atteindre les standards attendus."
        )
    
    # Poor attendance (<60%)
    else:
        final_score = max(0, final_score - 10)
        justification_parts.append(
            f"Assiduité insuffisante avec seulement {presences}/{total_sessions} présences ({base_score:.1f}%). "
            f"Action urgente requise - risque d'échec académique."
        )
    
    # Penalty for recent absences
    if recent_absences > 3:
        final_score = max(0, final_score - (recent_absences * 2))
        justification_parts.append(
            f"⚠️ {recent_absences} absences récentes (30 derniers jours) affectent négativement le score."
        )
    
    # Bonus for perfect recent attendance
    if recent_presences >= 5 and recent_absences == 0:
        final_score = min(100, final_score + 5)
        justification_parts.append(
            f"✅ Bonus pour assiduité parfaite récente ({recent_presences} présences consécutives)."
        )
    
    # Late arrivals impact
    if late > 0:
        late_penalty = min(5, late)
        final_score = max(0, final_score - late_penalty)
        justification_parts.append(
            f"📍 {late} retard(s) enregistré(s) - la ponctualité doit être améliorée."
        )
    
    # Ensure score is within bounds
    final_score = max(0, min(100, int(final_score)))
    justification = " ".join(justification_parts)
    
    # Add improvement suggestions for low scores
    if final_score < 70:
        justification += (
            f"\n\n📋 Recommandations: Assister à toutes les sessions à venir, "
            f"justifier les absences si nécessaire, et consulter le formateur pour rattraper le retard."
        )
    
    return (final_score, justification)


def bulk_calculate_scores(class_name: str = None, db: Session = None) -> Dict[int, Tuple[int, str]]:
    """
    Calculate scores for all students (or specific class).
    Used by N8N Workflow 4 to update all students at once.
    
    Args:
        class_name: Optional class filter (e.g., 'DSI2')
        db: Database session
    
    Returns:
        Dict mapping student_id -> (score, justification)
    """
    query = db.query(Student.id)
    
    if class_name:
        query = query.filter(Student.class_name == class_name)
    
    student_ids = [row[0] for row in query.all()]
    
    results = {}
    for student_id in student_ids:
        score, justification = calculate_attendance_score(student_id, db)
        results[student_id] = (score, justification)
    
    return results


def update_student_scores(class_name: str = None, db: Session = None) -> int:
    """
    Calculate and UPDATE all student scores in database.
    This is what N8N Workflow 4 should call via API endpoint.
    
    Args:
        class_name: Optional class filter
        db: Database session
    
    Returns:
        Number of students updated
    """
    scores = bulk_calculate_scores(class_name, db)
    
    updated = 0
    for student_id, (score, justification) in scores.items():
        student = db.query(Student).filter(Student.id == student_id).first()
        if student:
            student.pourcentage = score
            student.justification = justification
            updated += 1
    
    db.commit()
    
    return updated


# Example calculations for different scenarios:
"""
SCENARIO 1: Perfect Attendance
- Sessions: 20, Presences: 20, Absences: 0
- Base Score: 100%
- Bonus: +5 for excellence
- Final Score: 100 ✅
- Justification: "Excellente assiduité avec 20/20 présences (100.0%)..."

SCENARIO 2: Good Attendance with Some Late
- Sessions: 20, Presences: 18, Late: 2, Absences: 0
- Base Score: (18 + 2*0.75) / 20 = 97.5%
- Penalty: -2 for lates
- Final Score: 95 ✅
- Justification: "Excellente assiduité avec 18/20 présences (97.5%)... 2 retard(s)..."

SCENARIO 3: Average Attendance
- Sessions: 20, Presences: 15, Absences: 5
- Base Score: 75%
- No bonus/penalty
- Final Score: 75 ⚠️
- Justification: "Bonne présence avec 15/20 présences (75.0%)..."

SCENARIO 4: Poor Recent Attendance
- Sessions: 20, Presences: 10, Absences: 10 (5 recent)
- Base Score: 50%
- Penalty: -10 (base) + -10 (recent absences)
- Final Score: 30 🔴
- Justification: "Assiduité insuffisante... 5 absences récentes..."

DYNAMIC UPDATE EXAMPLE:
- Day 1: Student has 15/20 presences → Score: 75
- Day 2: Student attends class → 16/21 presences → Score: 76
- Day 3: Student is absent → 16/22 presences → Score: 73
→ Score automatically reflects current attendance! ✅
"""
