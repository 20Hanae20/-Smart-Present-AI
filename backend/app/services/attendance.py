from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord
from app.models.session import Session as SessionModel
from app.models.student import Student
from app.models.absence import Absence  # N8N integration
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate


class AttendanceService:
    """Service layer for attendance marking and analytics."""

    @staticmethod
    def mark_attendance(
        db: Session, session_id: int, student_id: int, payload: AttendanceCreate
    ) -> AttendanceRecord:
        """Mark attendance for a student in a session.
        
        Args:
            db: Database session
            session_id: Session ID
            student_id: Student ID
            payload: Attendance creation payload
            
        Returns:
            AttendanceRecord: Created or existing attendance record
            
        Note:
            If attendance already exists for this session/student, returns existing record.
        """
        # Check if already marked
        existing = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id == student_id,
            )
            .first()
        )
        if existing:
            return existing

        record = AttendanceRecord(
            session_id=session_id,
            student_id=student_id,
            status=payload.status,
            marked_via=payload.marked_via or "manual",
            facial_confidence=payload.facial_confidence,
            verification_photo_path=payload.verification_photo_path,
            actual_arrival_time=payload.actual_arrival_time,
            late_minutes=payload.late_minutes or 0,
            percentage=payload.percentage or Decimal("0.00"),
            justification=payload.justification,
            device_id=payload.device_id,
            ip_address=payload.ip_address,
            location_data=payload.location_data,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        # ⭐ AUTO-CALCULATE ABSENCE HOURS, ATTENDANCE RATE & ALERT LEVEL
        AttendanceService._update_student_stats(db, student_id, session_id, payload.status)
        
        # ⭐ N8N INTEGRATION: Log absence for email notification workflow
        # Only if marked via manual/auto_confirmation (when trainer confirms session)
        if payload.status == "absent" and payload.marked_via in ["auto_confirmation", "manual"]:
            AttendanceService._log_absence_for_n8n(db, student_id, session_id)
        
        return record

    @staticmethod
    def update_attendance(
        db: Session, attendance_id: int, payload: AttendanceUpdate
    ) -> AttendanceRecord:
        """Update existing attendance record (trainer/admin only).
        
        Args:
            db: Database session
            attendance_id: Attendance record ID
            payload: Update payload with partial fields
            
        Returns:
            AttendanceRecord | None: Updated record or None if not found
        """
        record = db.query(AttendanceRecord).filter(AttendanceRecord.id == attendance_id).first()
        if not record:
            return None

        # Track if status changed for stats recalculation
        status_changed = False
        old_status = record.status
        
        for field, value in payload.dict(exclude_unset=True).items():
            if field == "status" and value != old_status:
                status_changed = True
            setattr(record, field, value)

        db.commit()
        db.refresh(record)
        
        # ⭐ Recalculate stats if status changed
        if status_changed:
            AttendanceService._update_student_stats(db, record.student_id, record.session_id, record.status)
        
        return record

    @staticmethod
    def get_student_attendance_summary(db: Session, student_id: int, days: int = 30):
        """Get attendance summary for a student.
        
        Args:
            db: Database session
            student_id: Student ID
            days: Number of days to look back (default: 30)
            
        Returns:
            dict: Summary with total_sessions, present, absent, late, excused counts,
                  attendance_rate (%), and period_days
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        records = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.marked_at >= cutoff_date,
            )
            .all()
        )

        total = len(records)
        present = sum(1 for r in records if r.status == "present")
        absent = sum(1 for r in records if r.status == "absent")
        late = sum(1 for r in records if r.status == "late")
        excused = sum(1 for r in records if r.status == "excused")

        attendance_rate = (present / total * 100) if total > 0 else 0

        return {
            "student_id": student_id,
            "total_sessions": total,
            "present": present,
            "absent": absent,
            "late": late,
            "excused": excused,
            "attendance_rate": round(attendance_rate, 2),
            "period_days": days,
        }

    @staticmethod
    def get_session_attendance(db: Session, session_id: int):
        """Get all attendance records for a session."""
        records = db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id).all()
        return records

    @staticmethod
    def get_class_attendance_stats(db: Session, class_name: str, days: int = 30):
        """Get attendance statistics for a class."""
        cutoff_date = datetime.now() - timedelta(days=days)

        records = (
            db.query(AttendanceRecord)
            .join(Student, AttendanceRecord.student_id == Student.id)
            .filter(
                Student.class_name == class_name,
                AttendanceRecord.marked_at >= cutoff_date,
            )
            .all()
        )

        if not records:
            return None

        total = len(records)
        present = sum(1 for r in records if r.status == "present")
        avg_rate = (present / total * 100) if total > 0 else 0

        return {
            "class": class_name,
            "total_records": total,
            "present_count": present,
            "average_attendance_rate": round(avg_rate, 2),
            "period_days": days,
        }

    @staticmethod
    def justify_absence(
        db: Session, attendance_id: int, justification: str, documents_path: str = None
    ):
        """Add justification to an attendance record."""
        record = db.query(AttendanceRecord).filter(AttendanceRecord.id == attendance_id).first()
        if not record:
            return None

        record.justification = justification
        if documents_path:
            record.verification_photo_path = documents_path

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_attendance_by_date_range(
        db: Session, student_id: int, start_date: datetime, end_date: datetime
    ):
        """Get attendance records within a date range."""
        records = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.marked_at >= start_date,
                AttendanceRecord.marked_at <= end_date,
            )
            .order_by(AttendanceRecord.marked_at.desc())
            .all()
        )
        return records

    @staticmethod
    def _update_student_stats(db: Session, student_id: int, session_id: int, status: str):
        """Auto-calculate absence hours, attendance rate, and alert level.
        
        This method implements three key automations:
        1. Auto-Calculate Absence Hours: Adds session duration when absent
        2. Auto-Update Attendance Rate: Recalculates percentage after each attendance
        3. Auto-Escalate Alert Level: Updates alert status based on thresholds
        """
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return

        # 1. AUTO-CALCULATE ABSENCE HOURS ⭐
        if status == "absent":
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if session and session.duration_minutes:
                # Convert minutes to hours and add to total
                absence_hours = session.duration_minutes / 60.0
                student.total_absence_hours = (student.total_absence_hours or 0) + int(absence_hours)
        
        # Also track late minutes
        if status == "late":
            # Late minutes are already in the attendance record, just aggregate
            total_late = db.query(AttendanceRecord).filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == "late"
            ).all()
            student.total_late_minutes = sum(r.late_minutes or 0 for r in total_late)

        # 2. AUTO-UPDATE ATTENDANCE RATE ⭐
        # Get all attendance records for this student
        all_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.student_id == student_id
        ).all()
        
        total_sessions = len(all_records)
        if total_sessions > 0:
            # Count present (including late and excused as present)
            present_count = sum(
                1 for r in all_records 
                if r.status in ["present", "late", "excused"]
            )
            attendance_rate = (present_count / total_sessions) * 100
            student.attendance_rate = Decimal(str(round(attendance_rate, 2)))
        else:
            student.attendance_rate = Decimal("100.00")

        # 3. AUTO-ESCALATE ALERT LEVEL ⭐
        # Calculate absence percentage (inverse of attendance rate)
        absence_rate = 100 - float(student.attendance_rate or 100)
        
        # Update alert level based on thresholds
        if absence_rate < 15:
            student.alert_level = "none"  # Green (OK)
        elif 15 <= absence_rate < 20:
            student.alert_level = "warning"  # Yellow (Warning)
        elif 20 <= absence_rate < 25:
            student.alert_level = "critical"  # Orange (Critical)
        else:  # >= 25%
            student.alert_level = "failing"  # Red (Failing)

        db.commit()
        db.refresh(student)

    @staticmethod
    def _log_absence_for_n8n(db: Session, student_id: int, session_id: int):
        """
        Log absence to N8N absence table for email notification workflow.
        
        N8N Workflow 1 reads from this table to send emails to parents.
        """
        # Get student and session data
        student = db.query(Student).filter(Student.id == student_id).first()
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        
        if not student or not session:
            return
        
        # Calculate absence hours from session duration
        absence_hours = (session.duration_minutes / 60.0) if session.duration_minutes else 0
        
        # Create absence record for N8N
        absence = Absence(
            studentid=student_id,
            date=session.start_time or datetime.now(),
            hours=Decimal(str(round(absence_hours, 2))),
            notified=False  # N8N will mark as True after sending email
        )
        db.add(absence)
        db.commit()
        
        # Update alertsent flag if threshold exceeded (for WhatsApp workflow)
        if student.total_absence_hours >= 8 and not student.alertsent:
            # N8N Workflow 3 will pick this up for WhatsApp notification
            pass  # Keep alertsent=False so N8N can detect and send WhatsApp

    @staticmethod
    def _log_absence_for_n8n_webhook(db: Session, student_id: int, session_id: int):
        """Log absence record for N8N automation with webhook trigger"""
        try:
            from app.models.absence import Absence
            from app.models.student import Student
            from app.services.n8n_webhooks import trigger_absence_webhook
            
            # Get student and session info
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                return
                
            # Create absence record
            absence = Absence(
                studentid=student_id,
                date=datetime.utcnow(),
                hours=2.0,  # Default session duration
                notified=False
            )
            db.add(absence)
            db.flush()  # Get the ID
            
            # Trigger N8N webhook asynchronously
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.create_task(trigger_absence_webhook(absence, student, db))
            
            logger.info(f"Logged absence for student {student_id} and triggered N8N webhook")
            
        except Exception as e:
            logger.error(f"Failed to log absence for N8N: {e}")
            # Don't raise - this is secondary functionality
            pass
