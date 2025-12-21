from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord
from app.models.session import Session as SessionModel
from app.models.student import Student
from app.models.trainer import Trainer
from app.models.user import User
from app.models.smart_attendance import AttendanceSession
from app.utils.deps import get_current_user, get_db

router = APIRouter(tags=["trainer"])


def _trainer_ids(db: Session, current_user: User) -> list[int]:
    """Return IDs that may be stored in sessions.trainer_id for this trainer.

    sessions.trainer_id is intended to reference users.id, but some records may store trainers.id.
    """
    ids: set[int] = {int(current_user.id)}
    try:
        tr = db.query(Trainer).filter(Trainer.user_id == current_user.id).first()
        if tr:
            ids.add(int(tr.id))
    except Exception:
        pass
    return list(ids)


@router.get("/stats")
def get_trainer_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get statistics for the current trainer."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access this endpoint")

    trainer_ids = _trainer_ids(db, current_user)

    # Find trainer's sessions
    total_sessions = (
        db.query(SessionModel).filter(SessionModel.trainer_id.in_(trainer_ids)).count()
    )

    # Count this week's sessions
    start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
    this_week = (
        db.query(SessionModel)
        .filter(
            SessionModel.trainer_id.in_(trainer_ids),
            SessionModel.session_date >= start_of_week.date(),
        )
        .count()
    )

    # Approximate total students (unique from attendance records)
    total_students = (
        db.query(func.count(func.distinct(AttendanceRecord.student_id)))
        .join(SessionModel, SessionModel.id == AttendanceRecord.session_id)
        .filter(SessionModel.trainer_id.in_(trainer_ids))
        .scalar()
        or 0
    )

    # Calculate average attendance rate
    attendance_records = (
        db.query(AttendanceRecord)
        .join(SessionModel, SessionModel.id == AttendanceRecord.session_id)
        .filter(SessionModel.trainer_id.in_(trainer_ids))
        .all()
    )
    total_records = len(attendance_records)
    present_count = sum(1 for r in attendance_records if r.status == "present")
    attendance_rate = (present_count / total_records * 100) if total_records > 0 else 0

    return {
        "total_sessions": total_sessions,
        "this_week_sessions": this_week,
        "total_students": total_students,
        "attendance_rate": round(attendance_rate, 2),
    }


@router.get("/upcoming-sessions")
def get_upcoming_sessions(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upcoming sessions for the trainer."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access this endpoint")

    trainer_ids = _trainer_ids(db, current_user)

    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.trainer_id.in_(trainer_ids),
            SessionModel.session_date >= datetime.now().date(),
        )
        .order_by(SessionModel.session_date, SessionModel.start_time)
        .limit(limit)
        .all()
    )

    result = []
    for s in sessions:
        # Count students for this session's classroom (approximation)
        student_count = (
            db.query(Student).filter(Student.class_name == getattr(s, "class_name", "")).count()
        )
        result.append(
            {
                "id": s.id,
                "title": s.topic or "Session",
                "date": s.session_date.isoformat() if s.session_date else "",
                "time": str(s.start_time) if s.start_time else "",
                "class_name": getattr(s, "class_name", ""),
                "student_count": student_count,
            }
        )
    return result


@router.get("/sessions")
def get_trainer_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all sessions for the trainer with pagination."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access this endpoint")

    trainer_ids = _trainer_ids(db, current_user)

    offset = (page - 1) * limit
    sessions = (
        db.query(SessionModel, AttendanceSession.is_active)
        .outerjoin(AttendanceSession, AttendanceSession.session_id == SessionModel.id)
        .filter(
            SessionModel.trainer_id.in_(trainer_ids),
            SessionModel.status != "confirmed"  # Exclude confirmed sessions
        )
        .order_by(SessionModel.session_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    class_names = {getattr(s[0], "class_name", None) for s in sessions}
    class_names.discard(None)
    class_names.discard("")
    class_counts = {}
    if class_names:
        # The mapped attribute is `class_name` (DB column named "class")
        class_counts = dict(
            db.query(Student.class_name, func.count(Student.id))
            .filter(Student.class_name.in_(class_names))
            .group_by(Student.class_name)
            .all()
        )

    result = []
    for sess, is_active in sessions:
        result.append(
            {
                "id": sess.id,
                "title": sess.topic or "Session",
                "date": sess.session_date.isoformat() if sess.session_date else "",
                "start_time": str(sess.start_time) if sess.start_time else "",
                "end_time": str(sess.end_time) if sess.end_time else "",
                "class_name": getattr(sess, "class_name", ""),
                "students": class_counts.get(getattr(sess, "class_name", ""), 0),
                "status": sess.status,
                "is_active": bool(is_active),
            }
        )

    return result


@router.get("/sessions/{session_id}/students")
def get_session_students(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get students for a trainer session (by class_name)."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access this endpoint")

    trainer_ids = _trainer_ids(db, current_user)

    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.trainer_id.in_(trainer_ids))
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    class_name = getattr(session, "class_name", "") or ""
    if not class_name:
        return []

    students = (
        db.query(Student)
        .filter(Student.class_name == class_name)
        .order_by(Student.last_name.asc(), Student.first_name.asc())
        .limit(500)
        .all()
    )

    return [
        {
            "id": s.id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "email": s.email,
            "class_name": s.class_name,
        }
        for s in students
    ]


@router.get("/attendance")
def get_trainer_attendance(
    session_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendance records for trainer's sessions."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access this endpoint")

    trainer_ids = _trainer_ids(db, current_user)

    query = (
        db.query(AttendanceRecord, SessionModel, Student)
        .join(SessionModel, SessionModel.id == AttendanceRecord.session_id)
        .join(Student, Student.id == AttendanceRecord.student_id)
        .filter(SessionModel.trainer_id.in_(trainer_ids))
    )

    if session_id:
        query = query.filter(AttendanceRecord.session_id == session_id)

    records = query.order_by(AttendanceRecord.marked_at.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "student_id": r.student_id,
            "student": f"{s.first_name} {s.last_name}".strip(),
            "email": s.email,
            "session": (session.title or session.topic or "Session"),
            "status": r.status,
            "date": session.session_date.isoformat() if session.session_date else "",
            "percentage": float(r.percentage) if r.percentage is not None else None,
            "marked_at": r.marked_at.isoformat() if r.marked_at else None,
            "justification": (
                {
                    "status": "approved" if r.status == "excused" else "pending",
                    "reason": r.justification,
                    "submitted_at": r.marked_at.isoformat() if r.marked_at else None,
                    "admin_comment": None,
                }
                if r.justification
                else None
            ),
        }
        for r, session, s in records
    ]


@router.patch("/attendance/{attendance_id}/justification")
def update_attendance_justification(
    attendance_id: int,
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update justification for an attendance record."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can update justifications")

    trainer_ids = _trainer_ids(db, current_user)

    record = (
        db.query(AttendanceRecord)
        .join(SessionModel, SessionModel.id == AttendanceRecord.session_id)
        .filter(AttendanceRecord.id == attendance_id, SessionModel.trainer_id.in_(trainer_ids))
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    decision = payload.get("status")
    if decision in {"approved", "rejected"}:
        if decision == "approved":
            # Minimal implementation: approving a justification turns absent/late into excused.
            if record.status in {"absent", "late"}:
                record.status = "excused"
        else:
            # Rejecting a justification clears it.
            record.justification = None
        db.commit()
        return {"status": "success", "id": record.id}

    if "justification" in payload:
        justification = (payload.get("justification") or "").strip()
        record.justification = justification or None

    db.commit()
    return {"status": "success", "id": record.id}


@router.get("/session-notes")
def get_session_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get session notes for trainer's sessions."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access session notes")

    trainer_ids = _trainer_ids(db, current_user)

    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.trainer_id.in_(trainer_ids), SessionModel.notes.isnot(None))
        .order_by(SessionModel.session_date.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": s.id,
            "session_id": s.id,
            "title": s.topic or "Session",
            "notes": s.notes,
            "date": s.session_date.isoformat() if s.session_date else "",
        }
        for s in sessions
    ]


@router.post("/session-notes")
def create_session_note(
    payload: Dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add or update notes for a session."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can create session notes")

    trainer_ids = _trainer_ids(db, current_user)

    session_id = payload.get("session_id")
    notes = payload.get("notes", "")

    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.trainer_id.in_(trainer_ids))
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.notes = notes
    db.commit()
    return {"status": "success", "session_id": session.id}


@router.get("/notifications")
def get_trainer_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get notifications for the trainer."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access notifications")

    from app.models.notification import Notification

    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.read.is_(False))

    notifications = query.order_by(Notification.created_at.desc()).limit(50).all()

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


@router.patch("/notifications/{notification_id}")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can update notifications")

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
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can delete notifications")

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


@router.get("/session-attendance")
def get_session_attendance_records(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get attendance records for a specific session (trainer view)."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can access this endpoint")

    trainer_ids = _trainer_ids(db, current_user)
    
    # Verify trainer owns the session
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.trainer_id.in_(trainer_ids)
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or not yours")
    
    # Get all students by class_name instead of missing Enrollment model
    from app.models.student import Student

    class_name = getattr(session, "class_name", "") or ""
    
    # Query students by the class column name - filter only active students
    students_in_class = db.query(Student).filter(
        Student.class_name == class_name,
        Student.is_deleted == False,
        Student.academic_status == "active"
    ).all()

    # Get attendance records for this session
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session_id)
        .all()
    )

    # Log for debugging
    print(f"Session {session_id} - Class: {class_name}, Students found: {len(students_in_class)}, Records: {len(records)}")

    record_map = {r.student_id: r for r in records}

    # Build response with all students in the class
    attendance_list = []
    for student in students_in_class:
        record = record_map.get(student.id)
        
        # Build student name from first_name and last_name
        student_name = f"{student.first_name} {student.last_name}" if student.first_name and student.last_name else "Unknown"

        attendance_list.append({
            "id": record.id if record else None,
            "student_id": student.id,
            "student_name": student_name,
            "status": record.status if record else "absent",
            "face_confidence": float(record.facial_confidence) if record and record.facial_confidence else None,
            "liveness_passed": True if record else False,  # AttendanceRecord doesn't have this field
            "location_verified": True if record and record.location_data else False,
            "checked_in_at": record.marked_at.isoformat() if record and record.marked_at else None,
            "photo_url": record.verification_photo_path if record and record.verification_photo_path else None,
        })

    return attendance_list


@router.post("/confirm-attendance")
def confirm_session_attendance(
    session_id: int = Query(...),
    attendance_records: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirm attendance for a session and send to admins."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can confirm attendance")

    trainer_ids = _trainer_ids(db, current_user)
    
    # Verify trainer owns the session
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.trainer_id.in_(trainer_ids)
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or not yours")
    
    # Mark session as confirmed
    session.status = "confirmed"
    session.attendance_marked = True
    db.add(session)
    
    # Deactivate attendance session
    from app.models.smart_attendance import AttendanceSession
    
    att_session = db.query(AttendanceSession).filter(
        AttendanceSession.session_id == session_id
    ).first()
    
    if att_session:
        att_session.is_active = False  # Deactivate after confirmation
        att_session.confirmed_at = datetime.now()
        db.add(att_session)
    
    # Create absence records for all students in the class who don't have attendance records
    from app.models.student import Student
    from app.models.attendance import AttendanceRecord
    from app.services.attendance import AttendanceService
    
    class_name = session.class_name
    absent_students = []  # Track for N8N logging
    
    if class_name:
        # Get all students in the class
        all_students = db.query(Student).filter(Student.class_name == class_name).all()
        
        # Get students who already have attendance records for this session
        existing_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.session_id == session_id
        ).all()
        existing_student_ids = {r.student_id for r in existing_records}
        
        # Create "absent" records for missing students
        for student in all_students:
            if student.id not in existing_student_ids:
                absent_record = AttendanceRecord(
                    session_id=session_id,
                    student_id=student.id,
                    status="absent",
                    marked_via="auto_confirmation"
                )
                db.add(absent_record)
                absent_students.append(student.id)
                
                # Update student stats for each absent student
                AttendanceService._update_student_stats(db, student.id, session_id, "absent")
    
    # Commit attendance records first
    db.commit()
    
    # ⭐ N8N INTEGRATION: Log absences for email workflow (after session confirmation)
    for student_id in absent_students:
        AttendanceService._log_absence_for_n8n(db, student_id, session_id)
    
    # Send notification to admins
    from app.services.notification import NotificationService
    from app.schemas.notification import NotificationCreate
    
    admins = db.query(User).filter(User.role == "admin").all()
    
    for admin in admins:
        payload = NotificationCreate(
            user_id=admin.id,
            user_type="admin",
            title="Attendance Confirmed",
            message=f"Trainer {current_user.username} confirmed attendance for {session.title or session.topic}",
            notification_type="attendance_confirmed"
        )
        NotificationService.create_notification(db, payload)
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Attendance confirmed for {session.title}",
        "session_id": session_id,
        "confirmed_at": datetime.now().isoformat()
    }


@router.post("/activate-session")
def activate_session_attendance(
    session_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate attendance tracking for a session."""
    if current_user.role != "trainer":
        raise HTTPException(status_code=403, detail="Only trainers can activate sessions")

    trainer_ids = _trainer_ids(db, current_user)
    
    # Verify trainer owns the session
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.trainer_id.in_(trainer_ids)
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or not yours")
    
    # Create or update attendance session
    from app.models.smart_attendance import AttendanceSession
    
    att_session = db.query(AttendanceSession).filter(
        AttendanceSession.session_id == session_id
    ).first()
    
    if not att_session:
        att_session = AttendanceSession(
            session_id=session_id,
            mode="self_checkin",
            is_active=True,
            activated_at=datetime.now(),
        )
        db.add(att_session)
    else:
        att_session.is_active = True
        att_session.activated_at = datetime.now()
        att_session.confirmed_at = None  # Reset confirmation
        db.add(att_session)
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Attendance activated for {session.title}",
        "session_id": session_id,
        "activated_at": datetime.now().isoformat(),
        "is_active": True
    }
