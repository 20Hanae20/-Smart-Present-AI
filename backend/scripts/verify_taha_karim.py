#!/usr/bin/env python3
"""Verify Taha and Karim have different scores"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

engine = create_engine('postgresql://postgres:postgres@db:5432/smart_attendance')
Session = sessionmaker(bind=engine)
db = Session()

query = text("""
    SELECT 
        u.email,
        s.first_name || ' ' || s.last_name as name,
        s.pourcentage as ai_score,
        COUNT(ar.id) as total_sessions,
        COUNT(CASE WHEN ar.status = 'present' THEN 1 END) as presences
    FROM students s
    JOIN users u ON s.user_id = u.id
    LEFT JOIN attendance_records ar ON s.id = ar.student_id
    WHERE u.email IN ('taha.khebazi@smartpresence.com', 'karimboudhim@smartpresence.com')
    GROUP BY u.email, s.first_name, s.last_name, s.pourcentage, s.id
    ORDER BY u.email;
""")

results = db.execute(query).fetchall()

print("\n🔍 VERIFICATION: Taha vs Karim Data")
print("=" * 80)
for row in results:
    email, name, score, sessions, presences = row
    rate = (presences / sessions * 100) if sessions > 0 else 0
    print(f"\n📧 {email}")
    print(f"   Name: {name}")
    print(f"   AI Score: {score}/100")
    print(f"   Sessions: {sessions}")
    print(f"   Presences: {presences}")
    print(f"   Rate: {rate:.1f}%")
    
    if score != int(rate):
        print(f"   ⚠️  MISMATCH: Score {score} doesn't match calculated rate {rate:.1f}%!")

print("\n" + "=" * 80)
db.close()
