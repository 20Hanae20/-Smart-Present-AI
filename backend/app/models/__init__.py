from app.models.attendance import AttendanceRecord
from app.models.audit_log import AuditLog
from app.models.controle import Controle
from app.models.feedback import StudentFeedback
from app.models.facial_verification_log import FacialVerificationLog
from app.models.message import Message, MessageThread
from app.models.notification import Notification
from app.models.notification_preferences import NotificationPreferences
from app.models.session import Session
from app.models.smart_attendance import (
    AttendanceAlert,
    AttendanceSession,
    FraudDetection,
    SelfCheckin,
    SmartAttendanceLog,
    TeamsParticipation,
)
from app.models.student import Student
from app.models.trainer import Trainer
from app.models.user import User
from app.models.webhook import Webhook, WebhookLog

__all__ = [
    "User",
    "Student",
    "Trainer",
    "Session",
    "AttendanceRecord",
    "Controle",
    "Notification",
    "NotificationPreferences",
    "StudentFeedback",
    "AttendanceSession",
    "SelfCheckin",
    "TeamsParticipation",
    "AttendanceAlert",
    "FraudDetection",
    "SmartAttendanceLog",
    "AuditLog",
    "Webhook",
    "WebhookLog",
    "MessageThread",
    "Message",
    "FacialVerificationLog",
]
