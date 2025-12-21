from typing import List, Optional

from datetime import date as date_type, datetime, time as time_type

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.session import Session as SessionModel
from app.models.trainer import Trainer
from app.models.student import Student
from app.models.user import User
from app.services.auth import get_current_user
from app.utils.cache import cached_response, redis_cache, response_cache
from app.utils.deps import get_db
from app.utils.task_queue import task_queue

router = APIRouter()


class StudentResponse(BaseModel):
    id: int
    name: str
    student_code: str
    email: str
    class_name: str
    facial_data_encoded: bool
    attendance_rate: float
    pourcentage: Optional[int] = None  # AI attendance score (0-100)
    justification: Optional[str] = None  # AI explanation

    class Config:
        from_attributes = True


class PaginatedStudentsResponse(BaseModel):
    items: List[StudentResponse]
    total: int
    total_pages: int
    page: int
    page_size: int


class TrainerResponse(BaseModel):
    id: int
    name: str
    email: str
    subjects: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedTrainersResponse(BaseModel):
    items: List[TrainerResponse]
    total: int
    total_pages: int
    page: int
    page_size: int


class SessionResponse(BaseModel):
    id: int
    title: str
    class_name: str
    trainer_id: Optional[int] = None
    trainer_name: Optional[str] = None
    date: str
    start_time: str
    end_time: str

    class Config:
        from_attributes = True


class PaginatedSessionsResponse(BaseModel):
    items: List[SessionResponse]
    total: int
    total_pages: int
    page: int
    page_size: int


class SmartSearchItem(BaseModel):
    id: int
    entity: str
    title: str
    subtitle: str | None = None


class SmartSearchResponse(BaseModel):
    items: List[SmartSearchItem]


# ==================== STUDENTS ENDPOINTS ====================


@router.get("/students", response_model=PaginatedStudentsResponse)
def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", min_length=0),
    class_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all students with pagination and optional filtering."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can list students"
        )

    cache_key = f"students:{page}:{page_size}:{search}:{class_name or 'all'}"

    def fetch_students():
        query = db.query(Student)

        # Search by name or student_code
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Student.first_name.ilike(search_term))
                | (Student.last_name.ilike(search_term))
                | (Student.student_code.ilike(search_term))
            )

        # Filter by class
        if class_name:
            query = query.filter(Student.class_name == class_name)

        total = query.count()
        total_pages = (total + page_size - 1) // page_size

        # Pagination
        offset = (page - 1) * page_size
        students = query.offset(offset).limit(page_size).all()

        items = [
            StudentResponse(
                id=s.id,
                name=f"{s.first_name} {s.last_name}",
                student_code=s.student_code,
                email=s.email,
                class_name=s.class_name,
                facial_data_encoded=s.facial_data_encoded,
                attendance_rate=s.attendance_rate,
            )
            for s in students
        ]

        return PaginatedStudentsResponse(
            items=items, total=total, total_pages=total_pages, page=page, page_size=page_size
        )

    # Prefer Redis cache when available
    if redis_cache and redis_cache.available():
        cached = redis_cache.get(cache_key)
        if cached:
            return cached
        result = fetch_students()
        redis_cache.set(cache_key, result.model_dump())
        return result

    return cached_response(cache_key, fetch_students)


@router.post("/students", status_code=status.HTTP_201_CREATED)
def create_student(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """Create a new student."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create students"
        )

    # Check if email already exists
    existing = db.query(User).filter(User.email == payload.get("email")).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create user
    user = User(
        username=payload.get("email", "").split("@")[0],
        email=payload.get("email"),
        password_hash=get_password_hash(payload.get("password", "password123")),
        role="student",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create student
    student = Student(
        user_id=user.id,
        first_name=payload.get("firstName", ""),
        last_name=payload.get("lastName", ""),
        email=payload.get("email"),
        class_name=payload.get("className", "UNASSIGNED"),
        student_code=payload.get("studentCode", f"STU{user.id:04d}"),
        phone=payload.get("phone"),
        address=payload.get("address"),
        alert_level="normal",
        attendance_rate=100.0,
        facial_data_encoded=False,
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # Invalidate cached student lists
    response_cache.invalidate(prefix="students:")
    if redis_cache and redis_cache.available():
        redis_cache.invalidate(prefix="students:")

    # Background hook for any async follow-ups (notifications, audit logs)
    if background_tasks:
        background_tasks.add_task(lambda: None)
    else:
        task_queue.submit(lambda: None)

    return {
        "id": student.id,
        "name": f"{student.first_name} {student.last_name}",
        "student_code": student.student_code,
        "email": student.email,
        "class_name": student.class_name,
    }


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a student."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete students"
        )

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Delete associated user
    user = db.query(User).filter(User.id == student.user_id).first()
    if user:
        db.delete(user)

    db.delete(student)
    db.commit()
    response_cache.invalidate(prefix="students:")
    return None


# ==================== TRAINERS ENDPOINTS ====================


@router.get("/trainers", response_model=PaginatedTrainersResponse)
def list_trainers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", min_length=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all trainers with pagination."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can list trainers"
        )

    cache_key = f"trainers:{page}:{page_size}:{search}"

    def fetch_trainers():
        query = db.query(User).filter(User.role == "trainer")

        # Search by email or username
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.email.ilike(search_term)) | (User.username.ilike(search_term))
            )

        total = query.count()
        total_pages = (total + page_size - 1) // page_size

        # Pagination
        offset = (page - 1) * page_size
        trainers = query.offset(offset).limit(page_size).all()

        items = [
            TrainerResponse(id=t.id, name=t.username, email=t.email, subjects=None)
            for t in trainers
        ]

        return PaginatedTrainersResponse(
            items=items, total=total, total_pages=total_pages, page=page, page_size=page_size
        )

    if redis_cache and redis_cache.available():
        cached = redis_cache.get(cache_key)
        if cached:
            return cached
        result = fetch_trainers()
        redis_cache.set(cache_key, result.model_dump())
        return result

    return cached_response(cache_key, fetch_trainers)


@router.post("/trainers", status_code=status.HTTP_201_CREATED)
def create_trainer(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """Create a new trainer."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create trainers"
        )

    # Check if email already exists
    existing = db.query(User).filter(User.email == payload.get("email")).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create trainer user
    user = User(
        username=payload.get("email", "").split("@")[0],
        email=payload.get("email"),
        password_hash=get_password_hash(payload.get("password", "password123")),
        role="trainer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    response_cache.invalidate(prefix="trainers:")
    if redis_cache and redis_cache.available():
        redis_cache.invalidate(prefix="trainers:")
    if background_tasks:
        background_tasks.add_task(lambda: None)
    else:
        task_queue.submit(lambda: None)

    return {"id": user.id, "name": user.username, "email": user.email, "role": "trainer"}


@router.delete("/trainers/{trainer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trainer(
    trainer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a trainer."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete trainers"
        )

    trainer = db.query(User).filter(User.id == trainer_id, User.role == "trainer").first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")

    db.delete(trainer)
    db.commit()
    response_cache.invalidate(prefix="trainers:")
    if redis_cache and redis_cache.available():
        redis_cache.invalidate(prefix="trainers:")
    return None


# ==================== SESSIONS ENDPOINTS ====================


@router.get("/sessions", response_model=PaginatedSessionsResponse)
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", min_length=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all sessions with pagination."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can list sessions"
        )

    cache_key = f"sessions:{page}:{page_size}:{search}"

    def fetch_sessions():
        query = db.query(SessionModel).filter(
            SessionModel.status != "confirmed"  # Exclude confirmed sessions
        )

        # Search by title or class_name
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (SessionModel.title.ilike(search_term))
                | (SessionModel.class_name.ilike(search_term))
            )

        total = query.count()
        total_pages = (total + page_size - 1) // page_size

        # Pagination
        offset = (page - 1) * page_size
        sessions = query.offset(offset).limit(page_size).all()

        trainer_ids = {getattr(s, "trainer_id", None) for s in sessions}
        trainer_ids.discard(None)

        # Sessions.trainer_id is intended to store users.id, but some data may contain trainers.id.
        # Resolve trainer names for both cases without N+1 queries.
        trainer_map: dict[int, str] = {}
        if trainer_ids:
            user_rows = db.query(User.id, User.username).filter(User.id.in_(trainer_ids)).all()
            trainer_map = {r[0]: r[1] for r in user_rows}

            unknown_ids = [tid for tid in trainer_ids if tid not in trainer_map]
            if unknown_ids:
                trainer_rows = (
                    db.query(Trainer.id, Trainer.user_id)
                    .filter(Trainer.id.in_(unknown_ids))
                    .all()
                )
                user_ids = [r[1] for r in trainer_rows if r[1] is not None]
                if user_ids:
                    user_rows2 = db.query(User.id, User.username).filter(User.id.in_(user_ids)).all()
                    user_map2 = {r[0]: r[1] for r in user_rows2}
                    for tr_id, user_id in trainer_rows:
                        if user_id in user_map2:
                            trainer_map[tr_id] = user_map2[user_id]

        items = [
            SessionResponse(
                id=s.id,
                title=s.title,
                class_name=s.class_name,
                trainer_id=getattr(s, "trainer_id", None),
                trainer_name=trainer_map.get(getattr(s, "trainer_id", None)),
                date=(
                    s.session_date.isoformat()
                    if hasattr(s, "session_date") and s.session_date
                    else ""
                ),
                start_time=str(getattr(s, "start_time", "")),
                end_time=str(getattr(s, "end_time", "")),
            )
            for s in sessions
        ]

        return PaginatedSessionsResponse(
            items=items, total=total, total_pages=total_pages, page=page, page_size=page_size
        )

    if redis_cache and redis_cache.available():
        cached = redis_cache.get(cache_key)
        if cached:
            return cached
        result = fetch_sessions()
        redis_cache.set(cache_key, result.model_dump())
        return result

    return cached_response(cache_key, fetch_sessions)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """Create a new session."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create sessions"
        )

    def _get(*keys, default=None):
        for k in keys:
            if k in payload and payload.get(k) is not None:
                return payload.get(k)
        return default

    def _parse_date(value) -> date_type:
        if isinstance(value, date_type):
            return value
        if isinstance(value, str) and value:
            return date_type.fromisoformat(value)
        raise ValueError("Invalid date; expected YYYY-MM-DD")

    def _parse_time(value) -> time_type:
        if isinstance(value, time_type):
            return value
        if isinstance(value, str) and value:
            return time_type.fromisoformat(value)
        raise ValueError("Invalid time; expected HH:MM")

    try:
        title = _get("title", "topic", default="")
        class_name = _get("class_name", "className", default="")
        trainer_id = _get("trainer_id", "trainerId")
        module_id = _get("module_id", "moduleId", default=1)
        classroom_id = _get("classroom_id", "classroomId", default=1)
        session_type = _get("session_type", "sessionType", default=None)
        status_value = _get("status", default=None)
        notes = _get("notes", default=None)

        session_date = _parse_date(_get("session_date", "date"))
        start_time = _parse_time(_get("start_time", "startTime"))
        end_time = _parse_time(_get("end_time", "endTime"))

        if not title:
            raise ValueError("Missing title")
        if not class_name:
            raise ValueError("Missing class")
        if trainer_id is None:
            raise ValueError("Missing trainer")

        # Normalize trainer_id: accept either users.id (role=trainer) or trainers.id (map to user_id)
        trainer_id_int = int(trainer_id)
        trainer_user = db.query(User).filter(User.id == trainer_id_int, User.role == "trainer").first()
        if trainer_user:
            trainer_id_int = trainer_user.id
        else:
            trainer_row = db.query(Trainer).filter(Trainer.id == trainer_id_int).first()
            if trainer_row and getattr(trainer_row, "user_id", None):
                trainer_user = (
                    db.query(User)
                    .filter(User.id == trainer_row.user_id, User.role == "trainer")
                    .first()
                )
                if trainer_user:
                    trainer_id_int = trainer_user.id
        if not trainer_user:
            raise ValueError("Invalid trainer")

        duration_minutes = None
        try:
            start_dt = datetime.combine(session_date, start_time)
            end_dt = datetime.combine(session_date, end_time)
            if end_dt < start_dt:
                end_dt = end_dt.replace(day=end_dt.day + 1)
            duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
        except Exception:
            duration_minutes = None

        session_obj = SessionModel(
            module_id=int(module_id),
            classroom_id=int(classroom_id),
            trainer_id=trainer_id_int,
            class_name=class_name,
            session_date=session_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            title=title,
            topic=_get("topic", default=title) or title,
            session_type=session_type or "theory",
            status=status_value or "scheduled",
            notes=notes,
        )
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
        response_cache.invalidate(prefix="sessions:")
        if redis_cache and redis_cache.available():
            redis_cache.invalidate(prefix="sessions:")
        if background_tasks:
            background_tasks.add_task(lambda: None)
        else:
            task_queue.submit(lambda: None)

        trainer_name = None
        try:
            trainer = db.query(User).filter(User.id == session_obj.trainer_id).first()
            trainer_name = getattr(trainer, "username", None) if trainer else None
        except Exception:
            trainer_name = None

        return SessionResponse(
            id=session_obj.id,
            title=session_obj.title or session_obj.topic or "",
            class_name=session_obj.class_name or "",
            trainer_id=session_obj.trainer_id,
            trainer_name=trainer_name,
            date=session_obj.session_date.isoformat() if session_obj.session_date else "",
            start_time=str(session_obj.start_time or ""),
            end_time=str(session_obj.end_time or ""),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a session."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete sessions"
        )

    session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session_obj)
    db.commit()
    response_cache.invalidate(prefix="sessions:")
    if redis_cache and redis_cache.available():
        redis_cache.invalidate(prefix="sessions:")
    return None


# ==================== SMART SEARCH ====================


@router.get("/search", response_model=SmartSearchResponse)
def smart_search(
    q: str = Query("", min_length=1),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can search across entities"
        )

    term = f"%{q}%"

    students = (
        db.query(Student)
        .filter(
            or_(
                Student.first_name.ilike(term),
                Student.last_name.ilike(term),
                Student.student_code.ilike(term),
                Student.email.ilike(term),
            )
        )
        .limit(limit)
        .all()
    )

    trainers = (
        db.query(User)
        .filter(User.role == "trainer")
        .filter(or_(User.email.ilike(term), User.username.ilike(term)))
        .limit(limit)
        .all()
    )

    sessions = (
        db.query(SessionModel)
        .filter(
            or_(
                SessionModel.topic.ilike(term),
                getattr(SessionModel, "class_name", SessionModel.topic).ilike(term),
            )
        )
        .limit(limit)
        .all()
    )

    items: List[SmartSearchItem] = []
    for s in students[: limit // 3]:
        items.append(
            SmartSearchItem(
                id=s.id,
                entity="student",
                title=f"{s.first_name} {s.last_name}",
                subtitle=f"{s.student_code} · {s.class_name}",
            )
        )

    for t in trainers[: limit // 3]:
        items.append(
            SmartSearchItem(
                id=t.id,
                entity="trainer",
                title=t.username,
                subtitle=t.email,
            )
        )

    for sess in sessions[: limit // 3]:
        items.append(
            SmartSearchItem(
                id=sess.id,
                entity="session",
                title=getattr(sess, "topic", "Session"),
                subtitle=f"{getattr(sess, 'class_name', '')} · {getattr(sess, 'session_date', '')}",
            )
        )

    return SmartSearchResponse(items=items)


# ==================== USERS (Legacy) ====================




@router.get("/confirmed-sessions")
def get_confirmed_sessions(
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all confirmed sessions with attendance data."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

    from app.models.smart_attendance import AttendanceSession
    from app.models.attendance import AttendanceRecord

    # Get confirmed sessions (where attendance was confirmed by trainer)
    confirmed_sessions = (
        db.query(AttendanceSession)
        .filter(AttendanceSession.confirmed_at.isnot(None))
        .order_by(AttendanceSession.confirmed_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for att_session in confirmed_sessions:
        session = db.query(SessionModel).filter(SessionModel.id == att_session.session_id).first()
        
        if not session:
            continue
        
        # Get attendance counts
        all_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.session_id == session.id
        ).all()
        
        present = sum(1 for r in all_records if r.status in ("present", "late"))
        absent = sum(1 for r in all_records if r.status == "absent")
        
        # Get trainer info
        trainer_name = "Unknown"
        if session.trainer_id:
            # session.trainer_id could be either a Trainer.id or a User.id
            # Try User first (more common)
            user = db.query(User).filter(User.id == session.trainer_id).first()
            if user:
                trainer_name = user.username
            else:
                # Try Trainer table
                trainer = db.query(Trainer).filter(Trainer.id == session.trainer_id).first()
                if trainer and trainer.user_id:
                    user = db.query(User).filter(User.id == trainer.user_id).first()
                    if user:
                        trainer_name = user.username
        
        result.append({
            "id": session.id,
            "title": session.title or session.topic,
            "class_name": session.class_name,
            "date": session.session_date.isoformat() if session.session_date else None,
            "trainer_name": trainer_name,
            "total_students": len(all_records) or 0,
            "present_count": present,
            "absent_count": absent,
            "confirmed_at": att_session.confirmed_at.isoformat() if att_session.confirmed_at else None,
        })
    
    return result


@router.get("/confirmed-session-details")
def get_confirmed_session_details(
    session_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed attendance records for a confirmed session."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

    from app.models.attendance import AttendanceRecord
    from app.models.student import Student

    # Get attendance records for this session
    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.session_id == session_id
    ).all()

    result = []
    for record in records:
        # Get student info
        student = db.query(Student).filter(Student.id == record.student_id).first()
        student_name = "Unknown"
        if student:
            student_name = f"{student.first_name} {student.last_name}"
        
        result.append({
            "student_name": student_name,
            "status": record.status,
            "face_confidence": float(record.facial_confidence) if record.facial_confidence else None,
        })

    return result


@router.get("/session-attendance-report")
async def download_session_attendance_report(
    session_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download session attendance as CSV report."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

    from app.models.attendance import AttendanceRecord
    from app.models.student import Student
    import csv
    from io import StringIO

    # Get attendance records
    records = (
        db.query(AttendanceRecord, Student)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .filter(AttendanceRecord.session_id == session_id)
        .all()
    )

    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nom Étudiant", "Statut", "Confiance Faciale", "Check-in At"])
    
    for record, student in records:
        writer.writerow([
            student.user.name if student.user else "Unknown",
            record.status,
            f"{record.face_confidence * 100:.1f}%" if record.face_confidence else "N/A",
            record.checked_in_at.isoformat() if record.checked_in_at else "N/A",
        ])

    return {"csv": output.getvalue()}



