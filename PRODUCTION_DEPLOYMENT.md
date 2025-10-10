# 🚀 Production Deployment Guide

**System**: Smart Presales Automation v1.0  
**Architecture**: Hybrid (APScheduler + LangGraph + LangFuse)  
**Status**: ✅ Ready for Production

---

## 📋 Pre-Deployment Checklist

### ✅ Phase 1: Cleanup (Completed)
- [x] Test scripts organized in `tests/`
- [x] Redundant files removed
- [x] Documentation updated

### ✅ Phase 2: Orchestration (Completed)
- [x] APScheduler replacing daemon threads
- [x] LangGraph workflows implemented
- [x] 3 background jobs configured
- [x] `/api/jobs` endpoint for monitoring
- [x] All tests passed (8/8)

### ✅ Phase 3: Observability (Completed)
- [x] LangFuse integration implemented
- [x] All components instrumented
- [x] Graceful degradation if not configured
- [x] Documentation complete

---

## 🎯 Deployment Steps

### Step 1: Get LangFuse Credentials (5 min)

1. Go to https://cloud.langfuse.com
2. Sign up (free tier: 50K traces/month)
3. Create project: "Smart Presales Production"
4. Navigate to Settings → API Keys
5. Copy:
   - Public Key (starts with `pk-lf-`)
   - Secret Key (starts with `sk-lf-`)

---

### Step 2: Configure Environment Variables on Render

Go to your Render dashboard → Your service → Environment

#### Required Variables (Must Set)
```bash
# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_FILE=config/amber-sheets-credentials.json
LEADS_SHEET_ID=your_sheet_id_here

# Vapi
VAPI_API_KEY=your_vapi_key_here
VAPI_ASSISTANT_ID=your_assistant_id_here
VAPI_PHONE_NUMBER_ID=your_phone_id_here

# LangFuse Observability (NEW!)
ENABLE_OBSERVABILITY=true
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
LANGFUSE_HOST=https://cloud.langfuse.com
```

#### Orchestration (Phase 2 - Use Defaults or Customize)
```bash
USE_LANGGRAPH=true
ORCHESTRATOR_INTERVAL_SECONDS=60
RECONCILIATION_INTERVAL_SECONDS=300
MAX_RETRY_COUNT=3
RETRY_INTERVALS=0.5,24
RETRY_UNITS=hours
```

#### Optional (WhatsApp)
```bash
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_DRY_RUN=false  # Set to false for production
WHATSAPP_ENABLE_FOLLOWUP=true
WHATSAPP_ENABLE_FALLBACK=true
WHATSAPP_TEMPLATE_FOLLOWUP=your_template_name
WHATSAPP_TEMPLATE_FALLBACK=your_template_name
WHATSAPP_LANGUAGE=en
```

#### Optional (Email)
```bash
EMAIL_DRY_RUN=false  # Set to false for production
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
FROM_EMAIL=your_email@gmail.com
FROM_NAME=Amber Student
EMAIL_SUBJECT=We tried to reach you!
```

---

### Step 3: Deploy to Render

#### Option A: Auto-Deploy (Recommended)
```bash
# Already pushed to main
git log --oneline -n 5
# Should show:
# a196548 Phase 3: LangFuse Observability
# fe90be1 Phase 2 Testing Complete
# 6e489b2 Phase 2: Hybrid orchestration
```

Render will auto-deploy from GitHub main branch.

#### Option B: Manual Deploy
1. Go to Render dashboard
2. Click "Manual Deploy" → "Deploy latest commit"
3. Wait for build (~3-5 min)

---

### Step 4: Verify Deployment

#### 4.1 Check Health
```bash
curl https://your-app.onrender.com/health
# Expected: {"status": "healthy"}
```

#### 4.2 Check Scheduled Jobs
```bash
curl https://your-app.onrender.com/api/jobs
```

**Expected Response**:
```json
{
  "scheduler_running": true,
  "job_count": 3,
  "jobs": [
    {
      "id": "call_orchestrator",
      "name": "Call Orchestration Job",
      "next_run": "2025-10-10T14:00:00Z",
      "trigger": "interval[0:01:00]"
    },
    {
      "id": "call_reconciliation",
      "name": "Call Reconciliation Job",
      "next_run": "2025-10-10T14:05:00Z",
      "trigger": "interval[0:05:00]"
    },
    {
      "id": "email_poller",
      "name": "Email Polling Job",
      "next_run": "2025-10-10T14:01:00Z",
      "trigger": "interval[0:01:00]"
    }
  ]
}
```

#### 4.3 Check Render Logs
```bash
# In Render dashboard → Logs tab
# Look for:
✅ Scheduled call orchestrator (every 60s)
✅ Scheduled call reconciliation (every 300s)
✅ Background scheduler started successfully
✅ LangFuse client initialized
✅ Starting web server on port 5001
```

#### 4.4 Configure Vapi Webhook
1. Go to Vapi dashboard → Settings → Webhooks
2. Set webhook URL: `https://your-app.onrender.com/webhook/vapi`
3. Save

---

### Step 5: Monitor LangFuse

1. Go to https://cloud.langfuse.com
2. Select your project: "Smart Presales Production"
3. Wait for first call (or trigger manually via dashboard)
4. You should see:
   - **Traces**: One per lead showing full journey
   - **Metrics**: Calls initiated, success rate
   - **Sessions**: Grouped by lead_uuid

---

## 📊 Post-Deployment Monitoring

### First 24 Hours

#### Monitor in Render:
1. **Logs**: Watch for errors
   ```bash
   # Look for:
   [Job] Starting LangGraph workflow orchestrator cycle
   [Job] Processing X leads with LangGraph workflow
   [Workflow] Initiating call for lead abc-123
   ✅ LangFuse client initialized
   ```

2. **Metrics**: CPU/Memory usage
   - **Expected**: < 50% CPU, < 512MB RAM

3. **Response Times**:
   - Dashboard: < 500ms
   - API endpoints: < 200ms

#### Monitor in LangFuse:
1. **Traces**: Should see new traces every time orchestrator runs
2. **Errors**: Check "Errors" tab for any failed operations
3. **Performance**: Look for slow operations (> 5s)

#### Monitor in Google Sheets:
1. **Status updates**: Leads moving from "pending" → "initiated" → "answered"/"missed"/"completed"
2. **AI Analysis**: `summary`, `success_status`, `structured_data` populated for completed calls
3. **Retry logic**: `retry_count` and `next_retry_time` updated for missed calls

---

## 🐛 Troubleshooting

### Issue: Jobs not running

**Symptoms**:
- No logs showing `[Job]` messages
- `/api/jobs` returns empty or 503

**Fix**:
1. Check Render logs for scheduler startup errors
2. Verify environment variables are set
3. Restart service: Render dashboard → Manual Deploy

---

### Issue: Calls stuck at "initiated"

**Symptoms**:
- Leads remain "initiated" for > 5 minutes
- No webhook logs in Render

**Diagnosis**:
```bash
# Check if webhooks configured
curl https://your-app.onrender.com/webhook/vapi \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":{"type":"status-update","status":"test"},"call":{"metadata":{"lead_uuid":"test-123"}}}'
```

**Fix**:
1. Verify Vapi webhook URL: `https://your-app.onrender.com/webhook/vapi`
2. Check Render logs for "Received webhook event"
3. If not receiving: Check Vapi dashboard → Webhooks settings

---

### Issue: LangFuse traces not appearing

**Symptoms**:
- LangFuse dashboard empty
- Render logs show: "LangFuse not configured"

**Fix**:
1. Verify environment variables:
   ```bash
   ENABLE_OBSERVABILITY=true
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```
2. Check Render logs for: "✅ LangFuse client initialized"
3. If error: Verify keys are correct in LangFuse dashboard

---

### Issue: High Sheets API quota usage

**Symptoms**:
- Render logs show: `429 Quota exceeded`
- Webhook processing fails

**Fix**:
1. **Short-term**: Our batching + caching (Phase 1 & 2) should help
2. **Medium-term**: Request quota increase in GCP Console
3. **Long-term**: Migrate to PostgreSQL for high volume

---

## 📈 Success Metrics

### Week 1 Targets:
- ✅ **Uptime**: > 99%
- ✅ **Call Success Rate**: > 70% (initiated → completed or answered)
- ✅ **Orchestrator Cycles**: ~1440/day (every 60s)
- ✅ **Webhook Processing**: < 500ms per event
- ✅ **LangFuse Traces**: Match # of initiated calls

### Monitor:
1. **Render Metrics**: CPU, memory, response times
2. **LangFuse Dashboard**: Traces, errors, performance
3. **Google Sheets**: Lead status distribution
4. **Vapi Dashboard**: Call duration, success rate

---

## 🔒 Security Notes

### Credentials Management:
- ✅ All secrets in Render environment variables (never in code)
- ✅ `.gitignore` excludes credentials files
- ✅ LangFuse keys rotatable from dashboard

### API Security:
- ⚠️ **Current**: No authentication on dashboard
- 🚀 **Future**: Add Flask-Login + basic auth (Phase 4+)

---

## 🎯 Next Steps After Deployment

### Immediate (Day 1):
1. [ ] Monitor Render logs for first call
2. [ ] Verify LangFuse trace appears
3. [ ] Check Google Sheets status updates
4. [ ] Test manual call trigger via dashboard

### Week 1:
1. [ ] Review LangFuse metrics daily
2. [ ] Identify any error patterns
3. [ ] Tune retry intervals if needed
4. [ ] Monitor Sheets API quota usage

### Week 2-4:
1. [ ] Build evaluation framework (Phase 4)
2. [ ] A/B test different Vapi prompts
3. [ ] Analyze qualification accuracy
4. [ ] Iterate on voice bot based on real data

---

## 📞 Support

### If Issues Arise:
1. **Check Render Logs**: Most errors visible here
2. **Check LangFuse**: Full trace history for debugging
3. **Check Google Sheets**: Verify data writes
4. **Manual Job Trigger**: Test orchestrator manually
   ```bash
   curl -X POST https://your-app.onrender.com/api/jobs/call_orchestrator/trigger
   ```

### Useful Commands:
```bash
# Health check
curl https://your-app.onrender.com/health

# View jobs
curl https://your-app.onrender.com/api/jobs

# Trigger orchestrator
curl -X POST https://your-app.onrender.com/api/jobs/call_orchestrator/trigger

# Get leads
curl https://your-app.onrender.com/api/leads

# Get retry config
curl https://your-app.onrender.com/api/retry-config
```

---

## 🎉 Deployment Complete!

**Your system now has**:
- ✅ Reliable scheduling (APScheduler)
- ✅ Declarative workflows (LangGraph)
- ✅ Full observability (LangFuse)
- ✅ Auto-retry logic
- ✅ Multi-channel fallback
- ✅ Call reconciliation
- ✅ Production monitoring

**Ready to scale!** 🚀

---

**Deployed**: [Date]  
**Deployed By**: [Your Name]  
**Version**: v1.0 (Phases 1-3 Complete)  
**Next Phase**: Evaluation Framework (Phase 4)

