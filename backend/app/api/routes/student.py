from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord
from app.models.feedback import StudentFeedback
from app.models.session import Session as SessionModel
from app.models.student import Student
from app.models.user import User
from app.services.attendance import AttendanceService
from app.utils.deps import get_current_user, get_db

router = APIRouter(tags=["student"])


@router.get("/stats")
def get_student_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get statistics for the current student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    # Get attendance records
    total_sessions = (
        db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).count()
    )
    present_count = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.student_id == student.id, AttendanceRecord.status == "present")
        .count()
    )
    absent_count = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.student_id == student.id, AttendanceRecord.status == "absent")
        .count()
    )

    justified_absences = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.status == "absent",
            AttendanceRecord.justification.isnot(None),
        )
        .count()
    )

    next_session = (
        db.query(SessionModel)
        .filter(
            SessionModel.class_name == getattr(student, "class_name"),
            SessionModel.session_date >= datetime.now().date(),
        )
        .order_by(SessionModel.session_date, SessionModel.start_time)
        .first()
    )

    return {
        "attendance_rate": student.attendance_rate or 0,
        "total_sessions": total_sessions,
        "total_classes": total_sessions,
        "present_count": present_count,
        "absent_count": absent_count,
        "absences": absent_count,
        "justified_absences": justified_absences,
        "next_session": (
            f"{next_session.session_date.isoformat()} {str(next_session.start_time) if next_session.start_time else ''}".strip()
            if next_session and next_session.session_date
            else None
        ),
        "total_absence_hours": student.total_absence_hours or 0,
        "total_late_minutes": student.total_late_minutes or 0,
        "alert_level": student.alert_level or "none",
        "ai_score": student.pourcentage,  # AI attendance score from N8N Workflow 4
        "ai_explanation": student.justification,  # AI explanation from N8N
    }


@router.get("/attendance")
def get_student_attendance(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendance records for the current student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    records = (
        db.query(AttendanceRecord, SessionModel)
        .join(SessionModel, SessionModel.id == AttendanceRecord.session_id)
        .filter(AttendanceRecord.student_id == student.id)
        .order_by(AttendanceRecord.marked_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "date": s.session_date.isoformat() if s.session_date else "",
            "subject": (s.title or s.topic or "Session"),
            "status": r.status,
            "marked_at": r.marked_at.isoformat() if r.marked_at else None,
            "late_minutes": r.late_minutes or 0,
            "justification": r.justification,
            "justified": bool(r.justification),
        }
        for (r, s) in records
    ]


@router.get("/upcoming-sessions")
def get_upcoming_sessions(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upcoming sessions for the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.session_date >= datetime.now().date(),
            SessionModel.class_name == getattr(student, "class_name"),
        )
        .order_by(SessionModel.session_date, SessionModel.start_time)
        .limit(limit)
        .all()
    )

    trainer_ids = {getattr(s, "trainer_id", None) for s in sessions}
    trainer_ids.discard(None)
    trainer_map = {}
    if trainer_ids:
        rows = db.query(User.id, User.username).filter(User.id.in_(trainer_ids)).all()
        trainer_map = {r[0]: r[1] for r in rows}

    return [
        {
            "id": s.id,
            "subject": (s.title or s.topic or "Session"),
            "date": s.session_date.isoformat() if s.session_date else "",
            "time": str(s.start_time) if s.start_time else "",
            "classroom": str(getattr(s, "classroom_id", "")),
            "trainer_name": trainer_map.get(getattr(s, "trainer_id", None)),
        }
        for s in sessions
    ]


@router.get("/schedule")
def get_student_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get weekly schedule for the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return []

    # Get this week's sessions
    start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
    end_of_week = start_of_week + timedelta(days=7)

    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.session_date >= start_of_week.date(),
            SessionModel.session_date < end_of_week.date(),
            SessionModel.class_name == getattr(student, "class_name"),
        )
        .order_by(SessionModel.session_date, SessionModel.start_time)
        .all()
    )

    trainer_ids = {getattr(s, "trainer_id", None) for s in sessions}
    trainer_ids.discard(None)
    trainer_map = {}
    if trainer_ids:
        rows = db.query(User.id, User.username).filter(User.id.in_(trainer_ids)).all()
        trainer_map = {r[0]: r[1] for r in rows}

    return [
        {
            "id": s.id,
            "subject": (s.title or s.topic or "Session"),
            "trainer": trainer_map.get(getattr(s, "trainer_id", None)),
            "classroom": str(getattr(s, "classroom_id", "")),
            "date": s.session_date.isoformat() if s.session_date else "",
            "start_time": str(s.start_time) if s.start_time else "",
            "end_time": str(s.end_time) if s.end_time else "",
            "day": s.session_date.strftime("%A") if s.session_date else "",
            "day_of_week": int(s.session_date.isoweekday()) if s.session_date else None,
        }
        for s in sessions
    ]


@router.get("/justifications")
def get_student_justifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get justifications submitted by the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return []

    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.student_id == student.id, AttendanceRecord.justification.isnot(None)
        )
        .order_by(AttendanceRecord.marked_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "date": r.marked_at.isoformat() if r.marked_at else None,
            "justification": r.justification,
            "status": r.status,
        }
        for r in records
    ]


@router.post("/justifications")
async def submit_justification(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a justification for an absence."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit justifications")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    content_type = (request.headers.get("content-type") or "").lower()
    attendance_id = None
    justification = ""
    uploaded_file = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        attendance_id = form.get("absence_id") or form.get("attendance_id")
        justification = (form.get("reason") or form.get("justification") or "").strip()
        uploaded_file = form.get("file")
    else:
        payload = await request.json()
        attendance_id = payload.get("absence_id") or payload.get("attendance_id")
        justification = (payload.get("justification") or payload.get("reason") or "").strip()

    if not attendance_id:
        raise HTTPException(status_code=400, detail="Missing attendance_id or absence_id")

    record = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.id == attendance_id, AttendanceRecord.student_id == student.id)
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    documents_path = None
    if uploaded_file is not None and hasattr(uploaded_file, "filename"):
        storage_dir = Path("/app/storage/justifications")
        storage_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(str(uploaded_file.filename)).suffix
        safe_name = f"{student.id}_{record.id}_{uuid4().hex}{suffix}"
        file_path = storage_dir / safe_name
        with open(file_path, "wb") as f:
            content = await uploaded_file.read()
            f.write(content)
        documents_path = str(file_path)

    saved = AttendanceService.justify_absence(db, record.id, justification, documents_path)
    if not saved:
        raise HTTPException(status_code=400, detail="Failed to save justification")
    return {"status": "success", "id": record.id}


@router.get("/absences")
def get_student_absences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all absences for the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access absences")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return []

    absences = (
        db.query(AttendanceRecord, SessionModel)
        .join(SessionModel, SessionModel.id == AttendanceRecord.session_id)
        .filter(AttendanceRecord.student_id == student.id, AttendanceRecord.status == "absent")
        .order_by(AttendanceRecord.marked_at.desc())
        .limit(200)
        .all()
    )

    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "date": (session.session_date.isoformat() if session.session_date else ""),
            "subject": (session.title or session.topic or "Session"),
            "justification": r.justification,
            "hasJustification": bool(r.justification),
            "justified": bool(r.justification),
        }
        for r, session in absences
    ]


@router.get("/feedback")
def get_student_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get feedback submitted by the student."""
    # Backward-compatible alias for newer /feedbacks endpoint
    return get_feedbacks(db=db, current_user=current_user)


@router.post("/feedback")
def submit_feedback(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback."""
    # Backward-compatible alias for newer /feedbacks endpoint
    return create_feedback(payload=payload, db=db, current_user=current_user)


@router.get("/feedbacks")
def get_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all feedbacks from the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access feedbacks")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return []

    rows = (
        db.query(StudentFeedback)
        .filter(StudentFeedback.student_id == student.id)
        .order_by(StudentFeedback.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "id": f.id,
            "subject": f.subject,
            "message": f.message,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "response": f.response,
        }
        for f in rows
    ]


@router.post("/feedbacks")
def create_feedback(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new feedback."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can create feedbacks")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    subject = (payload.get("subject") or "").strip()
    message = (payload.get("message") or "").strip()
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Missing subject or message")

    fb = StudentFeedback(student_id=student.id, subject=subject, message=message)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return {"status": "success", "id": fb.id}


@router.get("/calendar")
def get_student_calendar(
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get calendar events for the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access calendar")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return []

    q = db.query(SessionModel).filter(SessionModel.class_name == getattr(student, "class_name"))

    if month and year:
        # Simple month filter; assumes session_date is a date.
        start = datetime(year, month, 1).date()
        end = (
            datetime(year + 1, 1, 1).date()
            if month == 12
            else datetime(year, month + 1, 1).date()
        )
        q = q.filter(SessionModel.session_date >= start, SessionModel.session_date < end)
    else:
        q = q.filter(SessionModel.session_date >= datetime.now().date())

    sessions = q.order_by(SessionModel.session_date.asc(), SessionModel.start_time.asc()).limit(200).all()

    trainer_ids = {getattr(s, "trainer_id", None) for s in sessions}
    trainer_ids.discard(None)
    trainer_map = {}
    if trainer_ids:
        rows = db.query(User.id, User.username).filter(User.id.in_(trainer_ids)).all()
        trainer_map = {r[0]: r[1] for r in rows}

    events = []
    for s in sessions:
        session_type = (s.session_type or "").lower()
        event_type = "exam" if "exam" in session_type else "class"
        trainer_name = trainer_map.get(getattr(s, "trainer_id", None))
        events.append(
            {
                "id": s.id,
                "title": s.title or s.topic or "Session",
                "date": s.session_date.isoformat() if s.session_date else "",
                "time": str(s.start_time)[:5] if s.start_time else "",
                "location": str(getattr(s, "classroom_id", "")),
                "type": event_type,
                "description": f"Cours avec {trainer_name}" if trainer_name and event_type == "class" else None,
            }
        )

    return events


@router.get("/profile")
def get_student_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get student profile information."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access profile")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email,
        "phone": student.phone,
        "student_code": student.student_code,
        "class_name": getattr(student, "class_name"),
        "attendance_rate": student.attendance_rate,
        "profile_photo_path": student.profile_photo_path,
    }


@router.put("/profile")
def update_student_profile(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update student profile."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can update profile")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    if "phone" in payload:
        student.phone = payload["phone"]
    if "email" in payload:
        student.email = payload["email"]
    if "first_name" in payload:
        student.first_name = payload["first_name"]
    if "last_name" in payload:
        student.last_name = payload["last_name"]
    if "full_name" in payload and isinstance(payload.get("full_name"), str):
        full_name = payload.get("full_name", "").strip()
        if full_name:
            parts = full_name.split()
            student.first_name = parts[0]
            if len(parts) > 1:
                student.last_name = " ".join(parts[1:])

    db.commit()
    return {"status": "success"}


@router.post("/profile/password")
def change_password(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change student password."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can change password")

    from app.services.auth import get_password_hash

    new_password = payload.get("new_password")
    if not new_password:
        raise HTTPException(status_code=400, detail="New password required")

    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    return {"status": "success"}


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload student avatar."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can upload avatar")

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    # Save file
    storage_dir = Path("/app/storage/avatars")
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{student.id}_{file.filename}"

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    student.profile_photo_path = str(file_path)
    db.commit()
    return {"status": "success", "path": str(file_path)}


@router.get("/notifications")
def get_student_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notifications for the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access notifications")

    from app.models.notification import Notification

    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can update notifications")

    from app.models.notification import Notification

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read = True
    db.commit()
    return {"status": "success"}


@router.delete("/notifications/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can delete notifications")

    from app.models.notification import Notification

    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notification)
    db.commit()
    return {"status": "success"}


@router.get("/notification-preferences")
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notification preferences for the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access preferences")

    from app.models.notification_preferences import NotificationPreferences

    prefs = (
        db.query(NotificationPreferences)
        .filter(NotificationPreferences.user_id == current_user.id)
        .first()
    )

    if not prefs:
        prefs = NotificationPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return {
        "system": prefs.system,
        "justification": prefs.justification,
        "schedule": prefs.schedule,
        "message": prefs.message,
        "email": prefs.email,
        "push": prefs.push,
    }


@router.get("/active-sessions-for-checkin")
def get_active_sessions_for_checkin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get active sessions available for student check-in (filtered by student's class)."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")

    # Get student record to find their class
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    # Get sessions that match the student's class and are active for attendance
    from app.models.smart_attendance import AttendanceSession
    from app.models.trainer import Trainer
    
    active_sessions = (
        db.query(
            SessionModel.id,
            SessionModel.title,
            SessionModel.class_name,
            SessionModel.session_date,
            SessionModel.start_time,
            SessionModel.end_time,
            SessionModel.trainer_id,
        )
        .join(AttendanceSession, SessionModel.id == AttendanceSession.session_id)
        .filter(
            SessionModel.class_name == getattr(student, "class_name"),  # Only sessions for their class
            AttendanceSession.is_active == True,
        )
        .all()
    )
    
    # Get trainer names (prefer trainer profile; fall back to user name if needed)
    trainer_names = {}
    for session_record in active_sessions:
        if session_record.trainer_id:
            trainer = db.query(Trainer).filter(Trainer.id == session_record.trainer_id).first()
            if trainer:
                # Use trainer profile fields if available, otherwise fall back to linked user name
                if trainer.first_name or trainer.last_name:
                    trainer_names[session_record.trainer_id] = " ".join(
                        part for part in [trainer.first_name, trainer.last_name] if part
                    ).strip()
                else:
                    from app.models.user import User as UserModel

                    user = db.query(UserModel).filter(UserModel.id == trainer.user_id).first()
                    trainer_names[session_record.trainer_id] = user.name if user else "Unknown"
            else:
                # Try to get from User directly if trainer_id is actually a user_id
                from app.models.user import User as UserModel

                user = db.query(UserModel).filter(UserModel.id == session_record.trainer_id).first()
                trainer_names[session_record.trainer_id] = user.name if user else "Unknown"

    return [
        {
            "id": s.id,
            "title": s.title,
            "class_name": s.class_name,
            "date": s.session_date.isoformat() if isinstance(s.session_date, datetime) else str(s.session_date),
            "start_time": str(s.start_time),
            "end_time": str(s.end_time),
            "trainer_name": trainer_names.get(s.trainer_id, "Unknown"),
            "is_attendance_active": True,
        }
        for s in active_sessions
    ]


@router.post("/submit-checkin")
async def submit_facial_checkin(
    session_id: int = Query(...),
    photo: UploadFile = File(...),
    latitude: float = Query(None),
    longitude: float = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit facial recognition check-in for a session."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit check-in")

    # Verify session exists and is active
    from app.models.smart_attendance import AttendanceSession
    
    attendance_session = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.session_id == session_id,
            AttendanceSession.is_active == True,
        )
        .first()
    )

    if not attendance_session:
        raise HTTPException(status_code=404, detail="Session not active or not found")

    # Verify student is in the correct class for this session
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if student.class_name != session.class_name:
        raise HTTPException(status_code=403, detail="You are not in the correct class for this session")

    try:
        # Process facial recognition check-in
        from app.services.self_checkin import SelfCheckinService
        
        service = SelfCheckinService()
        
        # Read photo file
        photo_bytes = await photo.read()
        
        result = service.process_facial_checkin(
            photo_data=photo_bytes,
            student_id=student.id,
            session_id=session_id,
            latitude=latitude,
            longitude=longitude,
            db=db,
        )

        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/notification-preferences")
def update_notification_preferences(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update notification preferences for the student."""
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can update preferences")

    from app.models.notification_preferences import NotificationPreferences

    prefs = (
        db.query(NotificationPreferences)
        .filter(NotificationPreferences.user_id == current_user.id)
        .first()
    )
    if not prefs:
        prefs = NotificationPreferences(user_id=current_user.id)
        db.add(prefs)

    # Only update known keys; ignore extras.
    for key in ["system", "justification", "schedule", "message", "email", "push"]:
        if key in payload:
            setattr(prefs, key, bool(payload[key]))

    db.commit()
    db.refresh(prefs)
    return {
        "system": prefs.system,
        "justification": prefs.justification,
        "schedule": prefs.schedule,
        "message": prefs.message,
        "email": prefs.email,
        "push": prefs.push,
    }
