# N8N Workflows - Next Steps

**System Status:** ✅ **All services running** (Frontend:3000, Backend:8000, DB:5432, Redis:6380, Gotenberg:3001)

## ✅ Completed Today (Dec 21, 2024)

### Infrastructure
- ✅ Added Gotenberg to `docker-compose.yml` (image: gotenberg/gotenberg:8)
- ✅ Updated `scripts/start.sh` to show Gotenberg URL
- ✅ Updated `scripts/status.sh` to monitor Gotenberg health
- ✅ Restarted all services with integrated Gotenberg

### Frontend Features (All 5 N8N Workflows Supported)
- ✅ **Workflow 1 (Parent Email)**: Notification bell shows parent alerts
- ✅ **Workflow 2 (Exam Reminder)**: Notification bell shows exam reminders
- ✅ **Workflow 3 (WhatsApp Alert)**: Notification system supports SMS/WhatsApp
- ✅ **Workflow 4 (AI Score)**: 
  - Student dashboard shows AI score card (0-100 with color coding)
  - Admin students page shows "Score IA" column with explanation popup
- ✅ **Workflow 5 (PDF Reports)**: 
  - New admin page at `/admin/reports` for PDF management
  - Download buttons, class filter, auto-refresh
  - Backend endpoint `/api/n8n/pdfs/download/{id}`

### Backend Endpoints
- ✅ Student stats expose `ai_score` and `ai_explanation` fields
- ✅ Admin students endpoint exposes `pourcentage` and `justification`
- ✅ N8N routes include PDF listing and download endpoints
- ✅ Database schema has all required fields:
  - `students.pourcentage` (AI score)
  - `students.justification` (AI explanation)
  - `students.parent_email` (for Workflow 1)
  - `students.parent_phone` (for Workflow 3)
  - `pdfabsences` table (for Workflow 5)

---

## 🔄 Testing Frontend Features (Do This Next)

### 1. Test AI Score Display (Workflows 4)
```sql
-- Connect to DB: docker exec -it smartpresence_db psql -U postgres -d smartpresence

-- Insert test AI score for a student
UPDATE students 
SET pourcentage = 85, 
    justification = 'Excellent participation et compréhension du cours. A montré une amélioration constante dans les évaluations.'
WHERE id = 1;
```

**Then verify:**
1. Login as student (email from `students` table where id=1)
2. Go to dashboard → See AI score card with 85/100 (orange color)
3. Login as admin
4. Go to `/admin/students` → See "Score IA: 85%" in table
5. Click sparkles icon → See AI explanation popup

### 2. Test PDF Reports Page (Workflow 5)
```sql
-- Insert test PDF record
INSERT INTO pdfabsences (id, filename, filepath, classe, generated_at)
VALUES (
  gen_random_uuid(),
  'absences_DSI2_2024-12-21.pdf',
  '/storage/pdfs/test.pdf',
  'DSI2',
  NOW()
);
```

**Then verify:**
1. Login as admin
2. Go to "Rapports PDF" in navbar → Opens `/admin/reports`
3. See the test PDF in the list
4. Click "Télécharger" → Backend should call Gotenberg
5. Filter by class "DSI2" → Should show only DSI2 PDFs

### 3. Test Notifications (Workflows 1, 2, 3)
```sql
-- Test parent email notification (Workflow 1)
-- N8N will create these automatically, but you can simulate:
INSERT INTO notifications (user_id, title, message, type, created_at)
SELECT id, 
       'Email envoyé aux parents',
       'Email d''absence envoyé à parent@example.com',
       'parent_email',
       NOW()
FROM students WHERE id = 1;

-- Test exam reminder (Workflow 2)
INSERT INTO notifications (user_id, title, message, type, created_at)
SELECT id,
       'Rappel d''examen',
       'Examen de Mathématiques demain à 10h00',
       'exam_reminder',
       NOW()
FROM students WHERE classe = 'DSI2';
```

**Then verify:**
1. Login as student
2. Click notification bell (top-right) → See 2 notifications
3. Notifications should show icon, title, message, timestamp

---

## 🎯 N8N Configuration (For Your Colleague)

### Prerequisites
- N8N instance running (provide URL)
- Access to workflow JSON files (already created in `workflows/` folder)

### Step-by-Step Setup

#### 1. Import Workflows
Import these 5 workflow JSON files into N8N:
1. `parent_email_notification.json` (Workflow 1)
2. `exam_reminder.json` (Workflow 2)
3. `whatsapp_alert.json` (Workflow 3)
4. `ai_scoring.json` (Workflow 4)
5. `pdf_absence_reports.json` (Workflow 5)

#### 2. Configure PostgreSQL Connection
All workflows need DB access to query data:
```
Host: 192.168.11.111
Port: 5432
Database: smartpresence
User: postgres
Password: [from .env file]
```

**Test Query:**
```sql
SELECT id, nom, prenom, parent_email, pourcentage 
FROM students 
LIMIT 5;
```

#### 3. Configure Workflow-Specific Credentials

**Workflow 1 (Parent Email):**
- Gmail OAuth2 credentials OR SMTP server
- Test with: `SELECT parent_email FROM students WHERE parent_email IS NOT NULL LIMIT 1;`

**Workflow 2 (Exam Reminder):**
- Same email credentials as Workflow 1
- Configure schedule: Daily at 8:00 AM (cron: `0 8 * * *`)

**Workflow 3 (WhatsApp Alert - Optional):**
- WhatsApp Business API credentials (if available)
- OR Twilio credentials for SMS
- Test with: `SELECT parent_phone FROM students WHERE parent_phone IS NOT NULL LIMIT 1;`

**Workflow 4 (AI Scoring):**
- OpenRouter API key for Claude/GPT access
- Configure prompt template:
  ```
  Analysez la performance de l'étudiant:
  - Présences: {{attendance_count}}
  - Absences: {{absence_count}}
  - Taux: {{attendance_rate}}%
  
  Donnez un score de 0 à 100 et une justification en français.
  ```
- Schedule: Weekly on Sunday at 23:00 (cron: `0 23 * * 0`)

**Workflow 5 (PDF Reports):**
- Gotenberg URL: `http://192.168.11.111:3001`
- Schedule: Daily at 07:00 (cron: `0 7 * * *`)
- Output folder: `/storage/pdfs/` (backend container path)

#### 4. Activate Workflows
In N8N UI:
1. Open each workflow
2. Click "Activate" toggle (top-right)
3. Verify schedule trigger is enabled for Workflows 2, 4, 5

#### 5. Test Each Workflow Manually

**Test Workflow 1 (Parent Email):**
```sql
-- Mark student absent
INSERT INTO absence (student_id, session_id, absence_type, absence_status)
VALUES (1, (SELECT id FROM sessions WHERE date = CURRENT_DATE LIMIT 1), 'UNJUSTIFIED', 'ABSENT');
```
→ Workflow should trigger and send email to `parent_email`

**Test Workflow 2 (Exam Reminder):**
```sql
-- Create exam tomorrow
INSERT INTO controles (classe, matiere, date_controle, heure_debut)
VALUES ('DSI2', 'Mathématiques', CURRENT_DATE + INTERVAL '1 day', '10:00:00');
```
→ Workflow should send reminder to all DSI2 students

**Test Workflow 4 (AI Scoring):**
Click "Execute Workflow" in N8N → Should update `pourcentage` and `justification` for all students

**Test Workflow 5 (PDF Reports):**
Click "Execute Workflow" in N8N → Should:
1. Query absences from DB
2. Call Gotenberg to generate PDF
3. Save to `pdfabsences` table
4. Visible in frontend at `/admin/reports`

---

## 📋 Verification Checklist

### Frontend Verification
- [ ] AI score card visible on student dashboard (`/student`)
- [ ] Score IA column visible in admin students table (`/admin/students`)
- [ ] AI explanation popup works (sparkles icon click)
- [ ] PDF reports page accessible (`/admin/reports`)
- [ ] PDF download button works
- [ ] Notification bell shows parent email alerts
- [ ] Notification bell shows exam reminders
- [ ] All colors/icons render correctly (Tailwind CSS)

### Backend Verification
- [ ] `/api/student/stats` returns `ai_score` and `ai_explanation`
- [ ] `/api/admin/students` returns `pourcentage` and `justification`
- [ ] `/api/n8n/pdfs/recent` returns PDF list
- [ ] `/api/n8n/pdfs/download/{id}` downloads PDF file
- [ ] Gotenberg health check: `curl http://localhost:3001/health`

### N8N Verification
- [ ] All 5 workflows imported successfully
- [ ] PostgreSQL credentials configured and tested
- [ ] Email credentials configured (Gmail/SMTP)
- [ ] OpenRouter API key added (Workflow 4)
- [ ] Gotenberg URL configured (Workflow 5)
- [ ] All workflows activated
- [ ] Schedule triggers enabled
- [ ] Manual execution works for each workflow

### Database Verification
```sql
-- Check students have required fields
SELECT id, nom, prenom, parent_email, parent_phone, pourcentage, justification 
FROM students LIMIT 5;

-- Check PDF records exist
SELECT id, filename, classe, generated_at FROM pdfabsences LIMIT 5;

-- Check notifications exist
SELECT id, user_id, title, type, created_at FROM notifications LIMIT 5;
```

---

## 🚀 Production Deployment Notes

### Environment Variables (Required for Production)
```bash
# Backend .env
OPENROUTER_API_KEY=sk-or-v1-xxxxx  # For Workflow 4 (AI scoring)
GOTENBERG_URL=http://gotenberg:3000  # Internal Docker network
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# N8N .env (on separate server if needed)
N8N_ENCRYPTION_KEY=your-secure-key-here
DB_POSTGRESDB_HOST=192.168.11.111
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=smartpresence
DB_POSTGRESDB_USER=postgres
DB_POSTGRESDB_PASSWORD=your-db-password
```

### Security Considerations
1. **API Keys**: Store in `.env`, never commit to Git
2. **Email OAuth**: Use Gmail OAuth2 instead of app passwords
3. **Database**: Use read-only user for N8N queries (except Workflow 4 which needs UPDATE)
4. **Gotenberg**: Keep on internal network, not exposed publicly
5. **CORS**: Backend already configured for frontend origin

### Monitoring
- All services have health checks in `docker-compose.yml`
- Use `./scripts/status.sh` to verify all 5 services
- Check logs: `./scripts/logs.sh [service]`
- Backend logs in `/backend/logs/api.log.*` (rotated)

---

## 📞 Support Resources

- **Frontend Guide**: `docs/N8N_WORKFLOW_4_5_FRONTEND.md`
- **Complete Status**: `docs/N8N_WORKFLOWS_COMPLETE_STATUS.md`
- **Integration Guide**: `docs/INTEGRATION_GUIDE.md`
- **Scripts Reference**: `scripts/README.md`
- **Docker Setup**: `DOCKER_SETUP.md`

**GitHub Repository**: https://github.com/Boudhim-Badr-Eddine/Smart-Presence-AI

---

## 📝 Summary

✅ **Infrastructure**: All 5 services running (PostgreSQL, Redis, Backend, Frontend, Gotenberg)  
✅ **Frontend**: All 5 N8N workflows have complete UI support  
✅ **Backend**: All API endpoints ready for N8N integration  
✅ **Database**: All required tables and fields exist  

🎯 **Next Steps**:
1. Test frontend features with SQL test data (see "Testing Frontend Features" section)
2. Import N8N workflows and configure credentials
3. Activate workflows and test each one manually
4. Monitor logs and verify end-to-end flow

**Time Estimate**: 2-3 hours for N8N configuration + testing
