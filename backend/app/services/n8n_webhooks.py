"""
N8N Webhook Integration Service
Enhanced webhook system for real-time N8N automation triggers
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

import httpx

from app.core.config import get_settings
from app.models.absence import Absence
from app.models.student import Student
from app.models.controle import Controle

logger = logging.getLogger(__name__)
settings = get_settings()

class N8NWebhookService:
    """Enhanced N8N webhook service for real-time automation triggers"""
    
    def __init__(self):
        self.n8n_webhook_url = getattr(settings, 'N8N_WEBHOOK_URL', None)
        self.timeout = 30
        self.retry_attempts = 3
        
    async def trigger_absence_notification(self, absence: Absence, student: Student, db: Session):
        """Trigger N8N workflow for new absence"""
        if not self.n8n_webhook_url:
            logger.warning("N8N webhook URL not configured")
            return False
            
        payload = {
            "event_type": "new_absence",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "absence_id": absence.id,
                "student_id": absence.studentid,
                "student_name": f"{student.firstname} {student.lastname}",
                "student_email": student.email,
                "parent_email": student.parent_email,
                "absence_date": absence.date.isoformat() if absence.date else None,
                "absence_hours": float(absence.hours) if absence.hours else 0,
                "notified": absence.notified
            }
        }
        
        return await self._send_webhook(payload)
    
    async def trigger_exam_reminder(self, controle: Controle, students: List[Student], db: Session):
        """Trigger N8N workflow for exam reminder"""
        if not self.n8n_webhook_url:
            return False
            
        payload = {
            "event_type": "exam_reminder",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "controle_id": controle.id,
                "module": controle.module,
                "date_controle": controle.date_controle.isoformat() if controle.date_controle else None,
                "type": controle.type,
                "notified": controle.notified,
                "students": [
                    {
                        "student_id": student.id,
                        "name": f"{student.firstname} {student.lastname}",
                        "email": student.email,
                        "parent_email": student.parent_email
                    }
                    for student in students
                ]
            }
        }
        
        return await self._send_webhook(payload)
    
    async def trigger_whatsapp_alert(self, student: Student, total_hours: float, db: Session):
        """Trigger N8N workflow for WhatsApp alert"""
        if not self.n8n_webhook_url:
            return False
            
        payload = {
            "event_type": "whatsapp_alert",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "student_id": student.id,
                "student_name": f"{student.firstname} {student.lastname}",
                "parent_phone": student.parent_phone,
                "total_absence_hours": total_hours,
                "alert_sent": student.alertsent,
                "attendance_score": student.pourcentage
            }
        }
        
        return await self._send_webhook(payload)
    
    async def trigger_daily_report(self, class_name: str, date: str, absences_data: List[Dict]):
        """Trigger N8N workflow for daily PDF report generation"""
        if not self.n8n_webhook_url:
            return False
            
        payload = {
            "event_type": "daily_report",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "class": class_name,
                "date": date,
                "absences": absences_data,
                "total_absences": len(absences_data)
            }
        }
        
        return await self._send_webhook(payload)
    
    async def trigger_ai_scoring(self, student: Student, absence_data: Dict[str, Any]):
        """Trigger N8N workflow for AI attendance scoring"""
        if not self.n8n_webhook_url:
            return False
            
        payload = {
            "event_type": "ai_scoring",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "student_id": student.id,
                "student_name": f"{student.firstname} {student.lastname}",
                "absence_data": absence_data,
                "current_score": student.pourcentage,
                "current_justification": student.justification
            }
        }
        
        return await self._send_webhook(payload)
    
    async def _send_webhook(self, payload: Dict[str, Any]) -> bool:
        """Send webhook to N8N with retry logic"""
        if not self.n8n_webhook_url:
            logger.warning("N8N webhook URL not configured")
            return False
            
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.n8n_webhook_url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "SmartPresence-AI/1.0"
                        }
                    )
                    
                    if response.status_code in [200, 201, 202]:
                        logger.info(f"N8N webhook sent successfully: {payload.get('event_type')}")
                        return True
                    else:
                        logger.warning(f"N8N webhook failed (attempt {attempt + 1}): {response.status_code}")
                        
            except Exception as e:
                logger.error(f"N8N webhook error (attempt {attempt + 1}): {e}")
                
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        logger.error(f"N8N webhook failed after {self.retry_attempts} attempts")
        return False

# Global webhook service instance
webhook_service = N8NWebhookService()

# Convenience functions for easy importing
async def trigger_absence_webhook(absence: Absence, student: Student, db: Session):
    """Trigger absence notification webhook"""
    return await webhook_service.trigger_absence_notification(absence, student, db)

async def trigger_exam_webhook(controle: Controle, students: List[Student], db: Session):
    """Trigger exam reminder webhook"""
    return await webhook_service.trigger_exam_reminder(controle, students, db)

async def trigger_whatsapp_webhook(student: Student, total_hours: float, db: Session):
    """Trigger WhatsApp alert webhook"""
    return await webhook_service.trigger_whatsapp_alert(student, total_hours, db)

async def trigger_daily_report_webhook(class_name: str, date: str, absences_data: List[Dict]):
    """Trigger daily report webhook"""
    return await webhook_service.trigger_daily_report(class_name, date, absences_data)

async def trigger_ai_scoring_webhook(student: Student, absence_data: Dict[str, Any]):
    """Trigger AI scoring webhook"""
    return await webhook_service.trigger_ai_scoring(student, absence_data)
