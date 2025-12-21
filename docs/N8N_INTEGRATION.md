# N8N Integration Guide

## Overview
SmartPresence integrates with N8N automation workflows to provide automated notifications and reporting. N8N reads from SmartPresence database tables and sends emails, WhatsApp messages, and generates PDF reports.

## Architecture

```
SmartPresence Backend → Database Tables → N8N (Schedule Trigger) → Emails/WhatsApp/PDFs
                    ↑
                    └── PDF Upload Endpoint
```

## Database Tables Used by N8N

### 1. `absence` Table
**Purpose:** Track absences for parent email notifications (Workflow 1)

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| studentid | Integer | Student ID |
| date | DateTime | Absence date |
| hours | Decimal(5,2) | Absence duration in hours |
| notified | Boolean | Email sent flag (N8N marks TRUE after sending) |
| created_at | DateTime | Record creation timestamp |

**Flow:**
1. Trainer confirms session attendance in SmartPresence
2. System auto-marks all non-checked-in students as "absent"
3. Backend creates records in `absence` table with `notified=FALSE`
4. N8N scheduled workflow queries `WHERE notified=FALSE`
5. N8N sends email to parent
6. N8N updates `notified=TRUE`

**Important:** Absences are finalized when the trainer clicks "Confirm Attendance" for the session. At this point, any student who didn't check in (via facial recognition, QR code, or manual marking) is automatically marked absent.

---

### 2. `students` Table (Enhanced)
**Purpose:** Store student data + N8N AI scoring

| N8N-Specific Columns | Type | Description |
|---------------------|------|-------------|
| pourcentage | Integer | AI attendance score (0-100) from Workflow 4 |
| justification | Text | AI explanation for score |
| alertsent | Boolean | WhatsApp alert sent flag (Workflow 3) |
| idStr | String(20) | String ID for N8N compatibility |
| total_absence_hours | Integer | Cumulative absence hours (auto-calculated) |

**Flow:**
- **Workflow 3 (WhatsApp):** Queries students with `total_absence_hours >= 8 AND alertsent=FALSE`
- **Workflow 4 (AI Score):** N8N calls OpenRouter API to calculate `pourcentage` and `justification`, then updates students table

---

### 3. `controles` Table
**Purpose:** Track exams for 72h reminder emails (Workflow 2)

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| module | String | Exam subject |
| date | DateTime | Exam date |
| class | String | Class name |
| notified | Boolean | Reminder sent flag |

**Flow:**
1. Admin creates controle in SmartPresence
2. N8N scheduled workflow calculates days until exam
3. If 3 days before exam (`diffDays == 3`) and `notified=FALSE`
4. N8N sends reminder email to all students in class
5. N8N updates `notified=TRUE`

---

### 4. `pdfabsences` Table
**Purpose:** Store daily absence summary PDFs (Workflow 5)

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| class | String | Class name |
| date | String | Report date (YYYY-MM-DD) |
| pdf_path | String | File path to PDF |
| created_at | DateTime | Upload timestamp |

**Flow:**
1. N8N groups absences by class
2. N8N generates HTML table
3. N8N calls Gotenberg API to convert HTML→PDF
4. N8N uploads PDF to SmartPresence via `/api/upload`
5. SmartPresence stores file and records in `pdfabsences` table

---

## N8N Workflows

### Workflow 1: Email Parents on Absence
**Trigger:** Schedule (every 5 minutes)
**Query:** `SELECT * FROM absence WHERE notified=FALSE`
**Actions:**
1. Get student data from `students` table
2. Send email to `parent_email` with absence details
3. Update `absence.notified=TRUE`

**Error Handling:** Sends error email to admin if Gmail API fails

---

### Workflow 2: Email Students 72h Before Exam
**Trigger:** Schedule (daily at 8:00 AM)
**Query:** `SELECT * FROM controles WHERE notified=FALSE`
**Actions:**
1. Calculate days until exam (`diffDays = (exam_date - today)`)
2. Filter controles where `diffDays == 3`
3. Get all students in class
4. Send reminder email with exam details
5. Update `controles.notified=TRUE`

**Error Handling:** Sends error email to admin if database/Gmail fails

---

### Workflow 3: WhatsApp Parents if >8h Absences
**Trigger:** Schedule (every hour)
**Query:** `SELECT * FROM students WHERE total_absence_hours >= 8 AND alertsent=FALSE`
**Actions:**
1. Send WhatsApp message to `parent_phone`
2. Update `students.alertsent=TRUE`

**Requirements:**
- WhatsApp Business API credentials
- Parent phone numbers in E.164 format (+212XXXXXXXXX)

**Error Handling:** Sends error email to admin if WhatsApp API fails

---

### Workflow 4: AI Attendance Score Calculation
**Trigger:** Schedule (daily at 6:00 PM)
**Query:** `SELECT * FROM absence GROUP BY studentid`
**Actions:**
1. Group absences by student
2. For each student:
   - Build prompt with absence history
   - Call OpenRouter API (Gemma-3-27B model)
   - AI analyzes patterns and calculates score (0-100)
   - AI generates justification text
3. Update `students.pourcentage` and `students.justification`

**AI Prompt:**
```
Analyze attendance data for student. Calculate score 0-100 based on:
- Frequency of absences
- Patterns (short period vs spread out)
- Recent trends

Return JSON: {"studentId":"xxx","pourcentage":85,"justification":"..."}
```

**Error Handling:** Sends error email to admin if API fails

---

### Workflow 5: Daily PDF Absence Summary
**Trigger:** Schedule (daily at 11:59 PM)
**Query:** `SELECT * FROM absence WHERE DATE(date) = TODAY()`
**Actions:**
1. Group today's absences by class
2. Generate HTML table with student details
3. Convert HTML to PDF via Gotenberg (`http://host.docker.internal:3000/forms/chromium/convert/html`)
4. Rename PDF: `absences_{class}_{date}.pdf`
5. Upload to SmartPresence: `POST /api/upload`
6. SmartPresence saves to `/app/storage/n8n_pdfs/` and records in DB

**PDF Includes:**
- Student firstname, lastname
- Parent email
- Absence date and hours
- Total count per class

**Error Handling:** Sends error email to admin if Gotenberg/upload fails

---

## SmartPresence API Endpoints

### POST `/api/upload`
**Purpose:** Receive PDF files from N8N Workflow 5

**Request:**
```http
POST /api/upload
Content-Type: multipart/form-data

file: absences_FS202_2025-12-21.pdf (binary)
```

**Response:**
```json
{
  "status": "success",
  "filename": "absences_FS202_2025-12-21.pdf",
  "path": "/app/storage/n8n_pdfs/absences_FS202_2025-12-21.pdf",
  "class": "FS202",
  "date": "2025-12-21"
}
```

### GET `/api/pdfs/{class_name}/{date}`
**Purpose:** Retrieve PDF path for admin download

**Request:**
```http
GET /api/pdfs/FS202/2025-12-21
```

**Response:**
```json
{
  "class": "FS202",
  "date": "2025-12-21",
  "pdf_path": "/app/storage/n8n_pdfs/absences_FS202_2025-12-21.pdf",
  "created_at": "2025-12-21T23:59:30"
}
```

### GET `/api/pdfs/recent?limit=10`
**Purpose:** List recent PDF reports

**Response:**
```json
[
  {
    "id": 1,
    "class": "FS202",
    "date": "2025-12-21",
    "pdf_path": "/app/storage/n8n_pdfs/absences_FS202_2025-12-21.pdf",
    "created_at": "2025-12-21T23:59:30"
  }
]
```

---

## Database Connection from N8N

**PostgreSQL Credentials:**
```
Host: host.docker.internal (if N8N in Docker)
Port: 5432
Database: smart_presence
Username: postgres
Password: <from .env>
```

**N8N Node:** `n8n-nodes-base.postgres`

**Important:** Ensure N8N container can reach PostgreSQL:
- Docker Compose: Use service name `db`
- External N8N: Use `localhost:5432` or server IP

---

## Setup Instructions

### 1. Import N8N Workflow JSON
1. Open N8N web interface (`http://<colleague-pc-ip>:5678`)
2. Click "Workflows" → "Import from File"
3. Upload the provided workflow JSON
4. Configure credentials:
   - PostgreSQL account (Postgres account)
   - Gmail OAuth2 (Gmail account)
   - WhatsApp API (WhatsApp account)
   - OpenRouter API key (sk-or-v1-...)

### 2. Run Database Migrations
```bash
cd /home/luno-xar/SmartPresence
./scripts/migrate.sh
```

This creates:
- `absence` table
- `pdfabsences` table
- New columns in `students`: `pourcentage`, `justification`, `alertsent`, `idStr`

### 3. Configure N8N Gotenberg URL
Ensure Gotenberg is running (for PDF generation):
```bash
docker run -d -p 3000:3000 gotenberg/gotenberg:8
```

Update N8N HTTP Request2 node:
```
URL: http://host.docker.internal:3000/forms/chromium/convert/html
```

### 4. Update N8N Upload Endpoint
In N8N HTTP Request node, set:
```
URL: http://host.docker.internal:8000/api/upload
```

### 5. Test Integration
```bash
# Mark a student absent
curl -X POST http://localhost:8000/api/attendance/mark \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "student_id": 31,
    "status": "absent"
  }'

# Check absence table
docker exec -it smart_presence-db-1 psql -U postgres -d smart_presence \
  -c "SELECT * FROM absence WHERE notified=FALSE;"

# Manually trigger N8N workflow
# N8N will detect the absence and send email
```

---

## Monitoring & Logs

### SmartPresence Logs
```bash
./scripts/logs.sh backend  # Check absence creation logs
```

### N8N Execution Logs
1. Open N8N UI
2. Click "Executions" tab
3. View success/failure status for each workflow run

### Database Verification
```sql
-- Check absences pending notification
SELECT * FROM absence WHERE notified = FALSE;

-- Check students with >8h absences
SELECT id, first_name, last_name, total_absence_hours, alertsent 
FROM students 
WHERE total_absence_hours >= 8;

-- Check AI scores
SELECT id, first_name, last_name, pourcentage, justification 
FROM students 
WHERE pourcentage IS NOT NULL;

-- Check daily PDFs
SELECT * FROM pdfabsences ORDER BY created_at DESC LIMIT 10;
```

---

## Troubleshooting

### Issue: Absences not appearing in `absence` table
**Solution:** Check backend logs. Ensure `AttendanceService._log_absence_for_n8n()` is executing.

### Issue: N8N can't connect to PostgreSQL
**Solutions:**
- Check `host.docker.internal` resolves (Docker Desktop required)
- Use PostgreSQL container IP: `docker inspect smart_presence-db-1 | grep IPAddress`
- Verify firewall allows port 5432

### Issue: Emails not sending
**Solutions:**
- Check Gmail OAuth2 credentials in N8N
- Verify parent_email exists in students table
- Check N8N execution logs for error details

### Issue: WhatsApp messages fail
**Solutions:**
- Verify WhatsApp Business API credentials
- Check phone numbers are in E.164 format (+212XXXXXXXXX)
- Ensure parent_phone field populated

### Issue: PDF upload fails
**Solutions:**
- Check SmartPresence API is reachable from N8N
- Verify `/app/storage/n8n_pdfs` directory exists and is writable
- Check backend logs: `./scripts/logs.sh backend`

### Issue: AI scoring returns errors
**Solutions:**
- Verify OpenRouter API key is valid
- Check API quota/limits
- Review N8N HTTP Request1 error output

---

## Security Considerations

1. **Database Access:** N8N has read/write access to SmartPresence DB. Use dedicated N8N user with limited permissions in production.

2. **API Keys:** Store OpenRouter API key securely in N8N credentials vault.

3. **Email Privacy:** Emails contain student absence data. Ensure Gmail account is secure.

4. **WhatsApp Compliance:** Verify GDPR compliance for parent phone number storage.

5. **PDF Storage:** Absence PDFs contain sensitive data. Restrict access to `/app/storage/n8n_pdfs`.

---

## Future Enhancements

1. **Webhook Integration:** Replace scheduled polling with real-time webhooks
2. **SMS Notifications:** Add Twilio integration for SMS alerts
3. **Parent Portal:** Allow parents to download PDFs directly
4. **AI Predictions:** Extend AI to predict at-risk students
5. **Multi-Language:** Translate emails/PDFs based on parent preferences

---

## Support

For N8N workflow issues, contact: **mohamed.fanani.pro@gmail.com** (Admin email configured in error handlers)

For SmartPresence backend issues, check: `docs/` directory and `README.md`
