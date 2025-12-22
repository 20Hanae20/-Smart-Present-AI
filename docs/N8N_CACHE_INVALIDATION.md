# N8N Workflows - Cache Invalidation & Real-Time Updates

## 🎯 Ensuring Frontend Shows Changes IMMEDIATELY

When N8N updates data (AI scores or PDFs), the frontend must see changes instantly.  
This document explains the caching system and how to ensure real-time updates.

---

## 📊 Current Caching System

### Backend (Redis)
- **Students API:** Cached for 5 minutes (`/api/admin/students`)
- **PDFs API:** Cached for efficiency
- **Cache Keys:**
  - `students:{page}:{page_size}:{search}:{class}`
  - `pdfs:*` (various PDF-related queries)

### Frontend (React Query)
- **Students Page:** `staleTime: 5 minutes`
- **Reports Page:** `refetchInterval: 30 seconds` (auto-refresh)
- **Manual Refresh:** Users can click refresh button

---

## ✅ Automatic Cache Invalidation (RECOMMENDED)

### Method 1: Use Built-in Auto-Invalidation
The `/api/n8n/upload` endpoint **automatically** clears PDF cache when called.

**N8N Workflow 5 (PDF Upload):**
```json
{
  "name": "Upload PDF to Backend",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "http://backend:8000/api/n8n/upload",
    "sendBinaryData": true,
    "binaryPropertyName": "data"
  }
}
// ✅ Cache automatically cleared on upload!
// Frontend will see new PDF within 30 seconds (auto-refresh)
```

### Method 2: Call Cache Invalidation Endpoint
After N8N updates student scores, call the cache invalidation endpoint.

**N8N Workflow 4 (AI Scoring) - Final Node:**
```json
{
  "name": "Invalidate Cache",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "http://backend:8000/api/n8n/cache/invalidate",
    "body": {},
    "options": {
      "timeout": 5000
    }
  }
}
```

**Benefits:**
- ✅ Frontend gets fresh data on next API call
- ✅ No wait time for cache expiration
- ✅ Users see updates within seconds

---

## 🔄 N8N Workflow 4: AI Scoring (Complete Setup)

### Node Flow
1. **PostgreSQL - Get Students** → Query students to score
2. **Calculate Attendance** → Count presences/absences  
3. **OpenRouter - Generate AI Score** → Call AI API
4. **PostgreSQL - Update Scores** → Write to database
5. **HTTP Request - Invalidate Cache** → Clear Redis cache ✨

### Node 5: Cache Invalidation (ADD THIS)
```json
{
  "name": "Clear Cache",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 1,
  "position": [900, 300],
  "parameters": {
    "method": "POST",
    "url": "http://192.168.11.111:8000/api/n8n/cache/invalidate",
    "authentication": "none",
    "options": {
      "timeout": 3000
    },
    "sendBody": true,
    "bodyParameters": {
      "parameters": []
    }
  }
}
```

**Timeline After Execution:**
- `T+0s`: N8N updates student pourcentage in database ✅
- `T+0s`: N8N calls cache invalidation endpoint ✅
- `T+0s`: Redis cache cleared ✅
- `T+1s`: User refreshes `/admin/students` page
- `T+1s`: Backend fetches fresh data from database
- `T+1s`: Frontend shows new AI scores with sparkles ✨

---

## 📄 N8N Workflow 5: PDF Reports (Complete Setup)

### Node Flow
1. **PostgreSQL - Get Absences** → Query daily absences
2. **Build HTML Template** → Create report HTML
3. **Gotenberg - Generate PDF** → Convert HTML to PDF
4. **HTTP Request - Upload PDF** → Send to backend ✨

### Node 4: Upload PDF (ALREADY AUTO-CLEARS CACHE)
```json
{
  "name": "Upload PDF to Backend",
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 1,
  "position": [900, 300],
  "parameters": {
    "method": "POST",
    "url": "http://192.168.11.111:8000/api/n8n/upload",
    "sendBinaryData": true,
    "binaryPropertyName": "data",
    "options": {
      "timeout": 10000
    }
  }
}
```

**Backend automatically:**
1. Saves PDF file to `/storage/pdfs/`
2. Inserts record in `pdfabsences` table
3. **Clears PDF cache** (`redis_cache.invalidate(prefix="pdfs:")`)
4. Returns success response

**Timeline After Execution:**
- `T+0s`: N8N uploads PDF ✅
- `T+0s`: Backend saves file + clears cache ✅
- `T+0-30s`: Frontend auto-refresh triggers (30s interval)
- `T+0-30s`: Frontend shows new PDF in reports page ✨

---

## 🚀 Frontend Auto-Refresh Configuration

### Admin Reports Page (Already Configured)
```tsx
const { data: reports = [] } = useQuery({
  queryKey: ['admin-pdf-reports'],
  queryFn: async () => {
    return apiClient<PDFReport[]>('/api/n8n/pdfs/recent?limit=50');
  },
  refetchInterval: 30000  // ✅ Auto-refresh every 30 seconds
});
```

**Result:** New PDFs appear automatically within 30 seconds!

### Admin Students Page (Manual Refresh)
```tsx
const { data, refetch } = useQuery({
  queryKey: ['admin-students', page, search, filters],
  queryFn: async () => { /* ... */ },
  staleTime: 5 * 60 * 1000  // 5 minutes cache
});
```

**Options for immediate updates:**
1. **User clicks refresh button** (🔄 icon) → Calls `refetch()`
2. **User navigates away and back** → Fetches fresh data
3. **Cache expires after 5 minutes** → Automatically refetches

---

## 🧪 Testing Cache Invalidation

### Test 1: Workflow 4 (AI Scores)
```bash
# 1. Run N8N Workflow 4 for a student
# 2. Verify cache invalidation endpoint was called:
docker-compose logs backend | grep "cache/invalidate"

# 3. Check Redis cache is empty:
docker-compose exec redis redis-cli KEYS "students:*"
# Should return: (empty list) or new keys after refresh

# 4. Refresh students page in browser → See new scores!
```

### Test 2: Workflow 5 (PDFs)
```bash
# 1. Run N8N Workflow 5 to generate PDF
# 2. Check upload endpoint response includes cache_cleared: true
# 3. Wait max 30 seconds (or refresh immediately)
# 4. See new PDF in reports page!
```

### Test 3: Manual Cache Clear (Testing Only)
```bash
# Clear all cache manually:
docker-compose exec redis redis-cli FLUSHDB

# Refresh any page → Will fetch fresh data from database
```

---

## 📋 Checklist for N8N Configuration

### Workflow 4 (AI Scoring)
- [ ] PostgreSQL node updates `students.pourcentage` ✅
- [ ] PostgreSQL node updates `students.justification` ✅
- [ ] Add HTTP Request node to call `/api/n8n/cache/invalidate` ✅
- [ ] Test: Update a student → Refresh frontend → See new score

### Workflow 5 (PDF Reports)  
- [ ] Gotenberg generates PDF file ✅
- [ ] HTTP Request uploads to `/api/n8n/upload` ✅
- [ ] Backend automatically clears cache (built-in) ✅
- [ ] Test: Generate PDF → Wait 30s → See in reports page

---

## 🎯 Expected Behavior Summary

| Action | Backend Cache | Frontend Cache | User Sees Update |
|--------|---------------|----------------|------------------|
| N8N Workflow 4 runs + calls invalidate | Cleared ✅ | Max 5 min | Immediate on refresh |
| N8N Workflow 5 uploads PDF | Auto-cleared ✅ | Max 30 sec | Within 30 seconds (auto) |
| User clicks refresh button | Bypassed | Bypassed | Immediate |
| Cache expires naturally | Auto-cleared | Refetched | Automatic |

---

## 💡 Best Practices

### For N8N Workflows:
1. ✅ **Always** call `/api/n8n/cache/invalidate` after database updates
2. ✅ Use `/api/n8n/upload` endpoint (has built-in cache clearing)
3. ✅ Add error handling for cache invalidation (non-critical)
4. ✅ Test both workflows end-to-end after setup

### For Frontend Users:
1. ✅ Reports page auto-refreshes every 30 seconds
2. ✅ Students page: Click refresh button (🔄) after N8N runs
3. ✅ Or wait 5 minutes for automatic cache expiration

### For Developers:
1. ✅ Monitor cache hit/miss rates in Redis
2. ✅ Adjust `refetchInterval` if needed (currently 30s)
3. ✅ Adjust `staleTime` if needed (currently 5 min)
4. ✅ Check backend logs for cache operations

---

## 🔧 Troubleshooting

### "I updated data in N8N but frontend doesn't show it"

**Checklist:**
1. Did N8N call `/api/n8n/cache/invalidate`? Check logs
2. Is Redis running? `docker-compose ps redis`
3. Did frontend refetch data? Check browser Network tab
4. Try manual refresh: Click 🔄 button or press F5
5. Clear browser cache if needed (Ctrl+Shift+R)

**Quick Fix:**
```bash
# Clear all cache manually:
docker-compose exec redis redis-cli FLUSHDB

# Refresh frontend → Should show latest data
```

### "Cache invalidation endpoint returns error"

**Check:**
```bash
# Test endpoint directly:
curl -X POST http://localhost:8000/api/n8n/cache/invalidate

# Should return:
{
  "status": "success",
  "message": "Cache invalidated successfully",
  "cleared": ["students", "pdfs"]
}
```

If error, check backend logs:
```bash
docker-compose logs backend --tail=50
```

---

## ✅ Verification Commands

### Check Cache Status
```bash
# List all cached keys:
docker-compose exec redis redis-cli KEYS "*"

# Check specific cache:
docker-compose exec redis redis-cli KEYS "students:*"
docker-compose exec redis redis-cli KEYS "pdfs:*"
```

### Test API Endpoints
```bash
# Get students (should see latest AI scores):
curl http://localhost:8000/api/admin/students?page=1&page_size=10 \
  -H "Authorization: Bearer <token>"

# Get PDFs (should see all uploaded PDFs):
curl http://localhost:8000/api/n8n/pdfs/recent?limit=50

# Clear cache:
curl -X POST http://localhost:8000/api/n8n/cache/invalidate
```

---

## 🎉 Success Criteria

✅ **Workflow 4:** After N8N updates student scores:
- Cache invalidation endpoint called successfully
- Redis cache cleared for students
- Frontend shows new scores on next page load/refresh

✅ **Workflow 5:** After N8N uploads PDF:
- PDF saved to `/storage/pdfs/`
- Database record created in `pdfabsences`
- Cache automatically cleared
- Frontend shows new PDF within 30 seconds (auto-refresh)

✅ **Overall:** Changes made by N8N appear in frontend **without** manual intervention (except optional refresh button click for students page)

---

**📖 Related Documentation:**
- `docs/N8N_NEXT_STEPS.md` - N8N setup guide
- `docs/DYNAMIC_FEATURES_PROOF.md` - Dynamic behavior verification
- `docs/N8N_WORKFLOW_4_5_FRONTEND.md` - Frontend implementation details
