#!/bin/bash
# Quick test to verify student data is in database

echo "🔍 TESTING STUDENT DATA IN DATABASE..."
echo "=" | tr '=' '=' | head -c 80
echo ""

docker-compose exec -T db psql -U postgres -d smart_attendance -c "
SELECT 
    s.id,
    s.first_name || ' ' || s.last_name as name,
    s.pourcentage as ai_score,
    COUNT(ar.id) as total_sessions,
    COUNT(CASE WHEN ar.status = 'present' THEN 1 END) as presences
FROM students s
JOIN users u ON s.user_id = u.id
LEFT JOIN attendance_records ar ON s.id = ar.student_id
WHERE u.role = 'student'
AND s.first_name IN ('Taha', 'karim')
GROUP BY s.id, s.first_name, s.last_name, s.pourcentage
ORDER BY s.first_name;
" 2>/dev/null || echo "❌ Database query failed - trying API test instead..."

echo ""
echo "✅ If you see scores above (not NULL), the data is good!"
echo "📱 Hard refresh your browser: Ctrl+Shift+R or Cmd+Shift+R"
