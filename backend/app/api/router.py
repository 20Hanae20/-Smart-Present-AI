from fastapi import APIRouter

from app.api.routes import (
    admin,
    admin_messages,
    admin_users,
    analytics,
    attendance,
    auth,
    chatbot,
    controles,
    dashboard,
    export,
    facial,
    gdpr,
    imports,
    integrations,
    messages,
    n8n,
    notifications,
    qr_checkin,
    reports,
    session_requests,
    sessions,
    smart_attendance,
    student,
    students,
    trainer,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(facial.router, prefix="/facial")
api_router.include_router(users.router, prefix="/users")
api_router.include_router(sessions.router, prefix="/sessions")
api_router.include_router(students.router, prefix="/students")
api_router.include_router(attendance.router, prefix="/attendance")
api_router.include_router(controles.router, prefix="/controles", tags=["Controles"])
api_router.include_router(chatbot.router, prefix="/chatbot")
api_router.include_router(notifications.router, prefix="/notifications")
api_router.include_router(session_requests.router, prefix="/session-requests")
api_router.include_router(reports.router, prefix="/reports")
api_router.include_router(smart_attendance.router)  # Uses /smart-attendance from router
api_router.include_router(admin.router, prefix="/admin")
api_router.include_router(admin_users.router, prefix="/admin")
api_router.include_router(admin_messages.router, prefix="/admin")
api_router.include_router(imports.router, prefix="/admin")
api_router.include_router(analytics.router, prefix="/admin")
api_router.include_router(trainer.router, prefix="/trainer")
api_router.include_router(student.router, prefix="/student")
api_router.include_router(messages.router, prefix="/messages")
api_router.include_router(gdpr.router)
api_router.include_router(qr_checkin.router)
api_router.include_router(export.router)
api_router.include_router(integrations.router)
api_router.include_router(dashboard.router)
api_router.include_router(n8n.router, prefix="/n8n", tags=["N8N Integration"])  # N8N webhook endpoints
try:
    from app.api.routes import embeddings

    api_router.include_router(embeddings.router, prefix="/embeddings")
except Exception:
    # Optional route: ignore if import fails
    pass
