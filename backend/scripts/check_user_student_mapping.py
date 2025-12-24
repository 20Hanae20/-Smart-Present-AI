#!/usr/bin/env python3
"""Fix student-user linkage to ensure each user has their own student record"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/smart_attendance')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

print("🔍 CHECKING STUDENT-USER LINKAGE...")
print("=" * 80)

# Check for duplicate student records with same user_id
query = text("""
    SELECT 
        u.id as user_id,
        u.email,
        u.role,
        s.id as student_id,
        s.first_name || ' ' || s.last_name as student_name,
        s.pourcentage as ai_score,
        (SELECT COUNT(*) FROM attendance_records WHERE student_id = s.id) as sessions
    FROM users u
    LEFT JOIN students s ON s.user_id = u.id
    WHERE u.role = 'student'
    ORDER BY u.email
    LIMIT 30;
""")

results = db.execute(query).fetchall()

print(f"\n📊 Found {len(results)} student users:\n")

user_student_map = {}
for row in results:
    user_id, email, role, student_id, student_name, ai_score, sessions = row
    
    if student_id is None:
        print(f"❌ {email} → NO STUDENT RECORD LINKED!")
    else:
        if user_id in user_student_map:
            print(f"⚠️  DUPLICATE: User {user_id} ({email}) has multiple student records!")
        else:
            user_student_map[user_id] = student_id
            status = "✅" if sessions > 0 else "⚠️ "
            print(f"{status} {email:<40} → Student ID: {student_id:>3} ({student_name:<20}) | Score: {ai_score or 'NULL':>3} | Sessions: {sessions}")

print("\n" + "=" * 80)

# Check for students with same email/name (duplicates)
duplicate_check = text("""
    SELECT email, first_name, last_name, COUNT(*) as count
    FROM students
    GROUP BY email, first_name, last_name
    HAVING COUNT(*) > 1;
""")

duplicates = db.execute(duplicate_check).fetchall()

if duplicates:
    print("\n🚨 DUPLICATE STUDENTS FOUND:")
    for row in duplicates:
        print(f"   {row[1]} {row[2]} ({row[0]}) - {row[3]} records")
else:
    print("\n✅ No duplicate student records found")

db.close()
