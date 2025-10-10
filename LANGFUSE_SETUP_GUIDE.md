# 🔍 LangFuse Setup Guide - Step by Step

**Complete guide to connect your Smart Presales system with LangFuse observability**

---

## 📋 Overview

LangFuse will give you:
- 📊 Real-time trace of every call (initiation → webhook → completion)
- 🔍 Debug failures with full context
- 📈 Metrics (success rate, qualification accuracy)
- 💬 Full conversation history across channels
- 🎯 Quality scores for continuous improvement

**Time**: 15-20 minutes total  
**Cost**: FREE (50,000 traces/month on free tier)

---

## 🚀 Step-by-Step Setup

### **STEP 1: Create LangFuse Account** (3 minutes)

#### 1.1 Go to LangFuse Cloud
Open your browser and navigate to:
```
https://cloud.langfuse.com
```

#### 1.2 Sign Up
Click **"Sign Up"** button (top right)

**Choose your method**:
- **Option A**: Sign up with GitHub (fastest) ✅ Recommended
- **Option B**: Sign up with Google
- **Option C**: Sign up with email + password

**I recommend GitHub** - fastest and you're already pushing code there.

#### 1.3 Verify Email (if using email signup)
- Check your inbox
- Click verification link
- Return to LangFuse

---

### **STEP 2: Create Your First Project** (2 minutes)

#### 2.1 After Login
You'll see the **"Create Project"** screen

#### 2.2 Create Project
Click **"Create Project"** or **"New Project"**

**Fill in**:
```
Project Name: Smart Presales Production
Description: AI voice bot for student lead qualification
```

Click **"Create"**

#### 2.3 You're In!
You'll see your project dashboard (empty for now - that's normal!)

---

### **STEP 3: Get API Keys** (2 minutes)

#### 3.1 Navigate to Settings
In the left sidebar, click:
```
⚙️ Settings → API Keys
```

#### 3.2 You'll See Two Keys

**Public Key** (starts with `pk-lf-`)
```
pk-lf-1234567890abcdef...
```
- ✅ Safe to expose in client-side code
- Used for reading traces
- We'll use this for our backend too

**Secret Key** (starts with `sk-lf-`)
```
sk-lf-0987654321fedcba...
```
- ⚠️ KEEP SECRET! Never commit to git
- Used for writing traces
- Only store in environment variables

#### 3.3 Copy Both Keys
Click the **copy icon** next to each key and save them temporarily (we'll add to `.env` next)

**Pro tip**: Keep the browser tab open - we'll need these keys in a moment!

---

### **STEP 4: Add Keys to Your Local Environment** (3 minutes)

#### 4.1 Open Your `.env` File
```bash
cd "/Users/amberuser/Desktop/Presales Automation/Smart Presales Version 1"
open .env  # or use your editor
```

If `.env` doesn't exist, create it:
```bash
cp config/config.example.env .env
```

#### 4.2 Add LangFuse Configuration
**Add these lines to your `.env` file**:

```bash
# ========================================
# LangFuse Observability (Phase 3)
# ========================================
ENABLE_OBSERVABILITY=true
LANGFUSE_PUBLIC_KEY=pk-lf-YOUR-PUBLIC-KEY-HERE
LANGFUSE_SECRET_KEY=sk-lf-YOUR-SECRET-KEY-HERE
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_DEBUG=false
```

**Replace**:
- `pk-lf-YOUR-PUBLIC-KEY-HERE` with your actual public key
- `sk-lf-YOUR-SECRET-KEY-HERE` with your actual secret key

**Example** (with fake keys):
```bash
ENABLE_OBSERVABILITY=true
LANGFUSE_PUBLIC_KEY=pk-lf-1a2b3c4d5e6f7g8h9i0j
LANGFUSE_SECRET_KEY=sk-lf-0j9i8h7g6f5e4d3c2b1a
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_DEBUG=false
```

#### 4.3 Save the File
Save and close your `.env` file

⚠️ **IMPORTANT**: Never commit `.env` to git! It's already in `.gitignore` ✅

---

### **STEP 5: Test Locally** (5 minutes)

#### 5.1 Start Your Local Server
```bash
cd "/Users/amberuser/Desktop/Presales Automation/Smart Presales Version 1"
./venv/bin/python main.py
```

**Look for this in the startup logs**:
```
✅ LangFuse client initialized (host: https://cloud.langfuse.com)
✅ Scheduled call orchestrator (every 60s)
🚀 Background scheduler started successfully
```

If you see ✅ **"LangFuse client initialized"** - you're connected! 🎉

If you see ⚠️ **"LangFuse not configured"** - double-check your keys in `.env`

#### 5.2 Trigger a Test Call (Optional)

**Option A**: Use the dashboard
1. Open http://localhost:5001
2. Click on any lead
3. Click **"Initiate Call"** button
4. This will create a real call and trace it

**Option B**: Use curl to test webhook
```bash
curl -X POST http://localhost:5001/webhook/vapi \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "status-update",
      "status": "answered"
    },
    "call": {
      "metadata": {
        "lead_uuid": "test-123"
      }
    }
  }'
```

This simulates a webhook and should create a trace in LangFuse.

#### 5.3 Check LangFuse Dashboard

1. Go back to https://cloud.langfuse.com
2. Select your project: **"Smart Presales Production"**
3. Click **"Traces"** in the left sidebar

**You should see**:
- A new trace with ID matching your lead_uuid
- Status: "vapi_outbound_call" or "webhook_status-update"
- Click on it to see full details!

**If you see traces** → ✅ **SUCCESS! You're fully connected!**

---

### **STEP 6: Deploy to Production** (5 minutes)

Now let's add LangFuse to your production Render deployment.

#### 6.1 Go to Render Dashboard
Open: https://dashboard.render.com

#### 6.2 Select Your Service
Click on your **Smart Presales** service

#### 6.3 Go to Environment Tab
Click **"Environment"** in the left sidebar

#### 6.4 Add Environment Variables
Click **"Add Environment Variable"** and add these **4 new variables**:

**Variable 1:**
```
Key:   ENABLE_OBSERVABILITY
Value: true
```

**Variable 2:**
```
Key:   LANGFUSE_PUBLIC_KEY
Value: pk-lf-1a2b3c4d5e6f7g8h9i0j  (your actual public key)
```

**Variable 3:**
```
Key:   LANGFUSE_SECRET_KEY
Value: sk-lf-0j9i8h7g6f5e4d3c2b1a  (your actual secret key)
```

**Variable 4:**
```
Key:   LANGFUSE_HOST
Value: https://cloud.langfuse.com
```

**Optional Variable 5** (for debugging):
```
Key:   LANGFUSE_DEBUG
Value: false  (set to 'true' to see detailed LangFuse API logs)
```

#### 6.5 Save Changes
Click **"Save Changes"** button

⚠️ **This will trigger an automatic redeployment** (~3-5 minutes)

#### 6.6 Wait for Deployment
Watch the **"Logs"** tab - you'll see:
```
==> Building...
==> Deploying...
==> Starting service...
✅ LangFuse client initialized
✅ Scheduled call orchestrator
🚀 Background scheduler started successfully
```

**When you see**: `Your service is live 🎉` → You're deployed!

---

## 🔍 Verification & Testing

### **Test 1: Health Check**
```bash
curl https://your-app-name.onrender.com/health
```

**Expected**:
```json
{"status": "healthy"}
```

---

### **Test 2: Check Jobs Are Running**
```bash
curl https://your-app-name.onrender.com/api/jobs
```

**Expected**:
```json
{
  "scheduler_running": true,
  "job_count": 3,
  "jobs": [
    {
      "id": "call_orchestrator",
      "name": "Call Orchestration Job",
      "next_run": "2025-10-10T14:30:00Z"
    },
    ...
  ]
}
```

✅ If you see 3 jobs → Orchestration is working!

---

### **Test 3: Trigger a Test Call**

**Option A**: Through Dashboard
1. Open https://your-app-name.onrender.com
2. Click on a lead
3. Click **"Initiate Call"**
4. Wait ~30 seconds

**Option B**: Via API
```bash
curl -X POST https://your-app-name.onrender.com/api/leads/LEAD_UUID/call
```

---

### **Test 4: Check LangFuse for Trace**

1. Go to https://cloud.langfuse.com
2. Select project: "Smart Presales Production"
3. Click **"Traces"** (left sidebar)
4. You should see a new trace!

**Click on the trace to see**:
- Timeline of events
- Full call lifecycle
- Webhook events
- AI analysis (if call completed)
- Any errors (if something failed)

🎉 **If you see the trace** → Everything is working perfectly!

---

## 📊 What You'll See in LangFuse

### Trace Example for a Completed Call

```
Trace ID: lead-uuid-abc-123
User: John Doe (+1234567890)
Duration: 2m 34s
Status: ✅ Success

Events:
├─ 00:00 - vapi_outbound_call
│  Input: {"lead_name": "John Doe", "lead_number": "+1234567890"}
│  Output: {"call_id": "vapi_xyz123", "status": "initiated"}
│  Duration: 245ms
│  Status: ✅ Success
│
├─ 00:15 - webhook_status-update
│  Input: {"type": "status-update", "status": "answered"}
│  Metadata: {"event_type": "status-update"}
│  Duration: 120ms
│  Status: ✅ Success
│
├─ 02:30 - webhook_end-of-call-report
│  Input: {full webhook payload}
│  Duration: 890ms
│  Status: ✅ Success
│
│  ├─ call_analysis
│  │  Model: vapi_assistant
│  │  Output: {
│  │    "summary": "Student planning MBA in UK, needs housing...",
│  │    "success_status": "qualified",
│  │    "structured_data": {
│  │      "country": "UK",
│  │      "course": "MBA",
│  │      "budget": "500-800 GBP/month"
│  │    }
│  │  }
│  │  Duration: 150ms
│  │
│  └─ message_call_transcript
│     Content: "Hi, this is Amber Student calling about..."
│     Metadata: {"call_id": "vapi_xyz123", "length": 1247}
│     Duration: 95ms
│
└─ 02:35 - message_whatsapp_out
   Content: "Sent template: post_call_followup"
   Metadata: {"template": "post_call_followup", "language": "en"}
   Duration: 340ms
   Status: ✅ Success
```

**This is the power of LangFuse!** 🎯

Every call gets a complete trace showing exactly what happened, when, and whether it succeeded.

---

## 🎓 Understanding the Dashboard

### Main Views

#### 1. **Traces** (Most Important)
- Shows all call lifecycles
- Search by lead_uuid, date, status
- Click any trace to see full details
- Filter by errors only

**Use for**:
- Debugging failed calls
- Understanding call flow
- Finding patterns

#### 2. **Sessions**
- Groups traces by user (lead_uuid)
- See all interactions with a single lead
- Useful for follow-up context

**Use for**:
- Understanding lead journey
- Multi-call scenarios

#### 3. **Generations**
- Shows all AI analysis operations
- See summaries and structured data
- Track qualification accuracy

**Use for**:
- Evaluating AI quality
- Finding qualification patterns

#### 4. **Metrics**
- Aggregate statistics
- Success/error rates
- Performance trends

**Use for**:
- High-level monitoring
- Identifying issues

#### 5. **Users**
- All leads (by lead_uuid)
- Click to see all traces for that lead

**Use for**:
- Per-lead investigation

---

## 🔧 Advanced Configuration (Optional)

### Enable Debug Mode

If you want to see detailed LangFuse API calls in your logs:

```bash
# In .env (local) or Render environment
LANGFUSE_DEBUG=true
```

**Use when**: Troubleshooting LangFuse connection issues  
**Warning**: Very verbose logs!

---

### Disable Observability

If you need to disable LangFuse temporarily:

```bash
# In .env or Render environment
ENABLE_OBSERVABILITY=false
```

**Use when**:
- Testing without traces
- Debugging local issues
- Quota concerns (rare with 50K/month free tier)

The app will work perfectly without LangFuse - all tracing becomes no-ops.

---

### Self-Hosted LangFuse (Advanced)

If you want to self-host LangFuse instead of using cloud:

#### 1. Deploy LangFuse (Docker)
```bash
# Using Docker Compose
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker-compose up -d
```

#### 2. Update Environment
```bash
LANGFUSE_HOST=http://your-server:3000  # Your self-hosted URL
LANGFUSE_PUBLIC_KEY=pk-lf-...  # From your self-hosted instance
LANGFUSE_SECRET_KEY=sk-lf-...  # From your self-hosted instance
```

**Benefit**: Full data control, no external dependency  
**Cost**: Server hosting (~$10-20/month)

---

## 🧪 Testing Your Connection

### Quick Test Script

Create `test_langfuse.py`:

```python
import os
from dotenv import load_dotenv
from src.observability import get_langfuse_client, log_conversation_message

load_dotenv()

# Test connection
client = get_langfuse_client()

if client:
    print("✅ LangFuse connected!")
    
    # Create a test trace
    test_trace = client.trace(
        name="test_connection",
        user_id="test-user-001",
        metadata={"test": True}
    )
    
    print("✅ Test trace created!")
    
    # Create a test message
    log_conversation_message(
        lead_uuid="test-user-001",
        channel="test",
        direction="out",
        content="This is a test message",
        metadata={"test": True}
    )
    
    print("✅ Test message logged!")
    
    # Flush
    client.flush()
    
    print("\n🎉 All tests passed!")
    print("👉 Check LangFuse dashboard - you should see a trace!")
    
else:
    print("❌ LangFuse not configured")
    print("Check your .env file for:")
    print("  - LANGFUSE_PUBLIC_KEY")
    print("  - LANGFUSE_SECRET_KEY")
```

**Run it**:
```bash
./venv/bin/python test_langfuse.py
```

**Expected output**:
```
✅ LangFuse connected!
✅ Test trace created!
✅ Test message logged!

🎉 All tests passed!
👉 Check LangFuse dashboard - you should see a trace!
```

**Then check LangFuse dashboard** → Traces → You should see "test_connection"!

---

## 📊 What Gets Traced (Automatic)

Once connected, these are **automatically traced** (no code changes needed):

### 1. Every Vapi Call
```
When: You click "Initiate Call" or orchestrator runs
Trace: "vapi_outbound_call"
Data:
  - Lead name, number, UUID
  - Call ID from Vapi
  - Success/error status
  - Timestamp
```

### 2. Every Webhook Event
```
When: Vapi sends webhook (status update, end-of-call report)
Trace: "webhook_status-update" or "webhook_end-of-call-report"
Data:
  - Full webhook payload
  - Event type
  - Lead UUID
  - Processing result
```

### 3. AI Call Analysis
```
When: Call completes and Vapi sends analysis
Trace: "call_analysis"
Data:
  - AI summary
  - Qualification status (qualified/unqualified)
  - Structured data (country, course, budget, etc.)
  - Call ID
```

### 4. Workflow Nodes
```
When: LangGraph workflow executes
Traces: "workflow_node_initiate_call", "workflow_node_whatsapp_fallback", etc.
Data:
  - Current state (call_status, retry_count)
  - Node input/output
  - Execution time
```

### 5. Cross-Channel Messages
```
When: WhatsApp or Email sent
Trace: "message_whatsapp_out", "message_email_out"
Data:
  - Message content (truncated)
  - Template used (WhatsApp)
  - Subject (Email)
  - Success/error
```

---

## 🎯 Using LangFuse for Debugging

### Example 1: Debug a Failed Call

**Problem**: Lead shows "initiated" but no further progress

**LangFuse Investigation**:

1. Go to **Traces** → Search for lead_uuid
2. Click on the trace
3. Look at the timeline:
   ```
   ✅ vapi_outbound_call (initiated successfully)
   ❌ No webhook events after this
   ```
4. **Diagnosis**: Webhooks not reaching server
5. **Fix**: Configure Vapi webhook URL

---

### Example 2: Low Qualification Rate

**Problem**: Most calls marked "unqualified"

**LangFuse Investigation**:

1. Go to **Generations** → Filter by name: "call_analysis"
2. Sort by "success_status": "unqualified"
3. Read the summaries:
   ```
   "Student is looking for short-term rental, not studying abroad"
   "Person already has housing, just browsing"
   "Not a student, looking for family housing"
   ```
4. **Pattern identified**: Bot not pre-qualifying "Are you a student?"
5. **Fix**: Update Vapi assistant prompt to ask upfront

---

### Example 3: Retry Loop Not Working

**Problem**: Missed calls not retrying

**LangFuse Investigation**:

1. Search for a missed call trace
2. Look for `workflow_node_check_retry` span
3. Check input state:
   ```json
   {
     "retry_count": 0,
     "max_retries": 3,
     "call_status": "missed"
   }
   ```
4. Check output: Should be "retry"
5. If output is "fallback" → Check `max_retries` configuration

---

## 📈 Metrics You Can Track

### Week 1 Baseline
After deployment, track these in LangFuse:

1. **Call Success Rate**
   - Traces with status="completed" / Total traces
   - **Target**: > 70%

2. **Qualification Rate**
   - Generations with success_status="qualified" / Total
   - **Benchmark**: Industry avg ~30-40%

3. **Average Call Duration**
   - Look at trace durations
   - **Typical**: 2-4 minutes

4. **Error Rate**
   - Traces with level="ERROR"
   - **Target**: < 5%

5. **Multi-Channel Effectiveness**
   - Traces with "message_whatsapp_out" or "message_email_out"
   - Shows fallback engagement rate

---

## 🎓 LangFuse Dashboard Tour

### After Your First Call

Go to LangFuse → Traces → Click on any trace

**You'll see 4 tabs**:

#### Tab 1: **Timeline**
Visual timeline showing:
- When each event happened
- Duration of each operation
- Success/error status
- Click any event to see details

#### Tab 2: **I/O**
Full input/output for each operation:
- Vapi API request/response
- Webhook payloads
- AI analysis results
- Easy copy-paste for debugging

#### Tab 3: **Metadata**
All metadata fields:
- Lead name, number, UUID
- Assistant ID, Phone ID
- Timestamps
- Custom tags

#### Tab 4: **Scores** (Coming in Phase 4)
Quality scores you'll add:
- Call quality (1-5)
- Qualification accuracy (0-1)
- Conversation naturalness (1-5)

---

## 🔐 Security & Privacy

### What Gets Sent to LangFuse

✅ **Safe to send**:
- Lead UUID
- Call status and duration
- AI summaries
- Structured data (country, course, budget)
- Message templates

❌ **NOT sent** (we filter these):
- API keys or passwords
- Full phone numbers (truncated in metadata)
- Sensitive PII (only lead UUID)

### Data Retention

**LangFuse Cloud**:
- Free tier: 30 days retention
- Paid plans: Up to 1 year
- GDPR compliant
- Data deletion on request

**Self-Hosted**:
- You control retention
- Your own database
- Full data ownership

---

## 💰 Pricing (LangFuse Cloud)

### Free Tier (What You Get)
```
✅ 50,000 traces/month
✅ 30 days retention
✅ Unlimited projects
✅ Unlimited team members
✅ Full feature access
✅ Community support
```

**For your use case**:
- ~1000 calls/month = ~3000 traces (call + webhooks + workflows)
- Free tier = **16x headroom** ✅
- Should last you until Scale-up phase

### Paid Tiers (If You Grow)
```
Starter: $39/month
  - 500K traces/month
  - 90 days retention
  
Pro: $199/month
  - 5M traces/month
  - 1 year retention
  - Priority support
```

**When to upgrade**: When you hit 50K traces/month (~15K calls/month)

---

## 🆘 Troubleshooting

### Issue: "LangFuse not configured" in logs

**Cause**: Missing or incorrect API keys

**Fix**:
1. Check `.env` (local) or Render environment (production)
2. Verify keys don't have extra spaces or quotes
3. Confirm keys are from correct project in LangFuse dashboard
4. Restart server

---

### Issue: Traces not appearing in dashboard

**Possible causes**:

**Cause 1**: Keys from wrong project
- **Check**: LangFuse dashboard → Switch to correct project

**Cause 2**: Network blocked
- **Check**: Render logs for "Failed to send to LangFuse"
- **Fix**: Check Render network settings (usually open)

**Cause 3**: Not enough time for sync
- **Wait**: LangFuse batches events, can take 5-10s
- **Force flush**: Restart your app (flushes on shutdown)

---

### Issue: Too many traces / quota concerns

**Solution 1**: Sample traces (trace 10% of calls)
```python
# In src/observability.py
import random

def should_trace():
    return random.random() < 0.1  # 10% sampling

# Use in decorators
if should_trace():
    # Create trace
```

**Solution 2**: Disable non-critical traces
```python
# Only trace errors and completed calls
if state['call_status'] in ['completed', 'failed']:
    # Trace
```

---

## 🎉 You're All Set!

### Final Checklist

- [x] LangFuse account created
- [x] Project created
- [x] API keys copied
- [x] Keys added to `.env` (local)
- [x] Keys added to Render (production)
- [x] Server started successfully
- [x] First trace visible in dashboard

### Next Steps

1. **Deploy to production** (if not already)
2. **Monitor first 24 hours**:
   - Render logs (no errors)
   - LangFuse traces (appearing correctly)
   - Google Sheets (status updates working)
3. **Start collecting data** for Phase 4 (evals)
4. **Iterate on voice bot** based on LangFuse insights

---

## 📞 Quick Reference

### URLs
- **LangFuse Dashboard**: https://cloud.langfuse.com
- **LangFuse Docs**: https://langfuse.com/docs
- **Your App (local)**: http://localhost:5001
- **Your App (production)**: https://your-app.onrender.com

### API Endpoints (for testing)
```bash
# Health
curl https://your-app.onrender.com/health

# Jobs
curl https://your-app.onrender.com/api/jobs

# Trigger job
curl -X POST https://your-app.onrender.com/api/jobs/call_orchestrator/trigger

# Webhook (test)
curl -X POST https://your-app.onrender.com/webhook/vapi \
  -H "Content-Type: application/json" \
  -d '{"message":{"type":"status-update","status":"answered"},"call":{"metadata":{"lead_uuid":"test-123"}}}'
```

### Environment Variables (Required)
```bash
ENABLE_OBSERVABILITY=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 🎊 Success!

**You now have**:
- ✅ Full observability into every call
- ✅ Debug capabilities with complete context
- ✅ Metrics for data-driven decisions
- ✅ Foundation for A/B testing (Phase 4-5)

**Your system went from**:
- Blind operation → Full visibility 👁️
- Manual debugging → Trace-based debugging 🔍
- Guesswork → Data-driven decisions 📊

---

**Need help?** Check these resources:
- LangFuse Docs: https://langfuse.com/docs/get-started
- LangFuse Discord: https://langfuse.com/discord
- Python SDK Docs: https://langfuse.com/docs/sdk/python

**Happy tracing!** 🚀📊

