#!/usr/bin/env python3
"""Verify student stats are correct"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/smart_attendance')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

print("📊 VERIFYING STUDENT DATA...")
print("=" * 80)

# Query student stats
query = text("""
    SELECT 
        s.id,
        s.first_name || ' ' || s.last_name as name,
        s.class_name,
        s.pourcentage as ai_score,
        s.attendance_rate as db_attendance_rate,
        COUNT(ar.id) as total_sessions,
        COUNT(ar.id) FILTER (WHERE ar.status = 'present') as presences,
        COUNT(ar.id) FILTER (WHERE ar.status = 'late') as lates,
        COUNT(ar.id) FILTER (WHERE ar.status = 'absent') as absences,
        ROUND((COUNT(ar.id) FILTER (WHERE ar.status IN ('present', 'late'))::numeric / 
               NULLIF(COUNT(ar.id), 0)) * 100, 1) as calculated_rate
    FROM students s
    JOIN users u ON s.user_id = u.id
    LEFT JOIN attendance_records ar ON s.id = ar.student_id
    WHERE u.role = 'student'
    AND (s.first_name LIKE '%Taha%' OR s.first_name LIKE '%Karim%' OR s.first_name LIKE '%karim%')
    GROUP BY s.id, s.first_name, s.last_name, s.class_name, s.pourcentage, s.attendance_rate
    ORDER BY s.first_name
""")

results = db.execute(query).fetchall()

if not results:
    print("❌ NO STUDENTS FOUND!")
else:
    for row in results:
        print(f"\n👤 {row[1]} (ID: {row[0]})")
        print(f"   Class: {row[2]}")
        print(f"   AI Score: {row[3]}/100")
        print(f"   Total Sessions: {row[5]}")
        print(f"   Presences: {row[6]}")
        print(f"   Lates: {row[7]}")
        print(f"   Absences: {row[8]}")
        print(f"   Calculated Attendance Rate: {row[9]}%")
        print(f"   DB Attendance Rate: {row[4]}%")
        
        if row[5] > 0:
            if row[9] >= 80:
                print(f"   Status: ✅ EXCELLENT")
            elif row[9] >= 60:
                print(f"   Status: ⚠️  GOOD")
            else:
                print(f"   Status: 🔴 NEEDS IMPROVEMENT")
        else:
            print(f"   Status: ℹ️  NO DATA")

print("\n" + "=" * 80)
print("✅ Verification complete!")

db.close()
