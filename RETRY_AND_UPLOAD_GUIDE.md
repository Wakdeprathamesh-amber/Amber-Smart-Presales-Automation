# 📋 Retry Mechanism & Bulk Upload Guide

**Date**: October 13, 2025  
**Status**: Complete Reference Guide

---

## 🔄 RETRY MECHANISM EXPLAINED

### **Current Configuration**

**Default Settings** (from code):
```bash
MAX_RETRY_COUNT=3
RETRY_INTERVALS=0.5,24
RETRY_UNITS=hours
```

**What This Means**:
- **Attempt 1**: Initial call
- **Attempt 2**: 0.5 hours (30 minutes) after missed
- **Attempt 3**: 24 hours after 2nd miss
- **After 3 attempts**: Stop calling, trigger WhatsApp/Email fallback

---

### **How It Works**

```
📞 Call Attempt 1 (Initial)
   ↓
   Answered? ✅ → Process call → Done
   ↓
   Missed? ❌
   ↓
⏰ Wait 30 minutes
   ↓
📞 Call Attempt 2 (Retry 1)
   ↓
   Answered? ✅ → Process call → Done
   ↓
   Missed? ❌
   ↓
⏰ Wait 24 hours
   ↓
📞 Call Attempt 3 (Retry 2)
   ↓
   Answered? ✅ → Process call → Done
   ↓
   Missed? ❌
   ↓
🚫 Max retries reached
   ↓
💬 Send WhatsApp fallback
   ↓
📧 Send Email fallback
   ↓
✅ Mark as "missed" (no more retries)
```

---

### **Scheduling System**

**✅ Using APScheduler** (Not Cron)

**Why APScheduler instead of Cron?**
- ✅ Works on any platform (Windows, Mac, Linux, Render)
- ✅ No need for system cron configuration
- ✅ Built into Python application
- ✅ Better error handling and logging
- ✅ Can be monitored via API endpoints

**Jobs Running**:
1. **Call Orchestrator** - Every 60 seconds (checks for pending/retry leads)
2. **Email Poller** - Every 60 seconds (checks for email replies)
3. **Call Reconciliation** - Every 5 minutes (fixes stuck "initiated" calls)
4. **One-time Callbacks** - Scheduled dynamically when requested

**Configuration** (in `.env`):
```bash
ORCHESTRATOR_INTERVAL_SECONDS=60      # How often to check for calls
IMAP_POLL_SECONDS=60                  # How often to check emails
RECONCILIATION_INTERVAL_SECONDS=300   # How often to fix stuck calls
```

---

### **Customizing Retry Behavior**

**Option 1: Change Retry Intervals**

Edit `.env`:
```bash
# Example: Retry after 15 min, then 2 hours, then 24 hours
MAX_RETRY_COUNT=3
RETRY_INTERVALS=0.25,2,24
RETRY_UNITS=hours
```

**Option 2: More Aggressive Retries**
```bash
# Retry 5 times: 5min, 15min, 1hr, 4hr, 24hr
MAX_RETRY_COUNT=5
RETRY_INTERVALS=5,15,60,240,1440
RETRY_UNITS=minutes
```

**Option 3: Conservative Retries**
```bash
# Only 2 retries: 1 hour, then 24 hours
MAX_RETRY_COUNT=2
RETRY_INTERVALS=1,24
RETRY_UNITS=hours
```

---

## 📤 BULK UPLOAD GUIDE

### **Required Format**

**Google Sheets Columns** (in order):

| Column | Required | Format | Example |
|--------|----------|--------|---------|
| `lead_uuid` | ✅ Yes | Auto-generated or custom | `uuid-123-456` or leave empty |
| `number` | ✅ Yes | **+CountryCode + Number** | `+919876543210` |
| `whatsapp_number` | ⚠️ Optional | **+CountryCode + Number** | `+919876543210` |
| `name` | ✅ Yes | First name or full name | `Prathamesh` |
| `email` | ⚠️ Optional | Valid email | `student@example.com` |
| `partner` | ✅ Yes | Partner name | `Physics Wallah` |
| `call_status` | ⚠️ Optional | Leave empty or `pending` | `pending` |
| Other columns | ⚠️ Optional | Leave empty | (system fills these) |

---

### **Phone Number Format** ⚠️ CRITICAL

**✅ CORRECT FORMAT**:
```
+919876543210          ← India (91)
+14155552671           ← USA (1)
+447911123456          ← UK (44)
+61412345678           ← Australia (61)
+16475551234           ← Canada (1)
```

**❌ WRONG FORMAT**:
```
9876543210             ← Missing + and country code
+91 98765 43210        ← Has spaces
+91-9876543210         ← Has dashes
(91) 9876543210        ← Has parentheses
```

**Format Rules**:
1. ✅ Must start with `+`
2. ✅ Country code immediately after `+`
3. ✅ No spaces, dashes, or parentheses
4. ✅ Only digits after `+`

**Common Country Codes**:
- India: `+91`
- USA/Canada: `+1`
- UK: `+44`
- Australia: `+61`
- Ireland: `+353`
- France: `+33`
- Spain: `+34`
- Germany: `+49`

---

### **Bulk Upload Methods**

#### **Method 1: Direct Google Sheets Entry** (Recommended)

1. Open your Google Sheet
2. Go to "Leads" worksheet
3. Add rows with this format:

```
| lead_uuid | number        | whatsapp_number | name       | email              | partner        | call_status |
|-----------|---------------|-----------------|------------|-------------------|----------------|-------------|
|           | +919876543210 | +919876543210   | Prathamesh | p@example.com     | Physics Wallah | pending     |
|           | +918765432109 | +918765432109   | Rahul      | r@example.com     | Leverage Edu   | pending     |
|           | +919988776655 |                 | Priya      | priya@example.com | IDP            | pending     |
```

**Notes**:
- Leave `lead_uuid` empty - system auto-generates
- `whatsapp_number` can be same as `number` or different
- If no WhatsApp, leave `whatsapp_number` empty
- `call_status` should be `pending` for new leads
- All other columns will be filled by system

#### **Method 2: CSV Import to Google Sheets**

1. Create CSV file with headers:
```csv
lead_uuid,number,whatsapp_number,name,email,partner,call_status
,+919876543210,+919876543210,Prathamesh,p@example.com,Physics Wallah,pending
,+918765432109,+918765432109,Rahul,r@example.com,Leverage Edu,pending
,+919988776655,,Priya,priya@example.com,IDP,pending
```

2. Go to Google Sheets → File → Import
3. Upload CSV
4. Select "Append to current sheet"
5. Done!

#### **Method 3: Programmatic Upload** (For Large Batches)

Create a Python script:

```python
# bulk_upload.py
import gspread
from google.oauth2.service_account import Credentials
import uuid

# Authenticate
scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('config/amber-sheets-credentials.json', scopes=scopes)
client = gspread.authorize(creds)

# Open sheet
sheet = client.open_by_key('YOUR_SHEET_ID')
worksheet = sheet.worksheet('Leads')

# Prepare leads data
leads = [
    {
        'number': '+919876543210',
        'whatsapp_number': '+919876543210',
        'name': 'Prathamesh',
        'email': 'p@example.com',
        'partner': 'Physics Wallah'
    },
    {
        'number': '+918765432109',
        'whatsapp_number': '+918765432109',
        'name': 'Rahul',
        'email': 'r@example.com',
        'partner': 'Leverage Edu'
    }
]

# Add leads to sheet
for lead in leads:
    row = [
        str(uuid.uuid4()),              # lead_uuid
        lead['number'],                 # number
        lead.get('whatsapp_number', ''), # whatsapp_number
        lead['name'],                   # name
        lead.get('email', ''),          # email
        lead['partner'],                # partner
        'pending',                      # call_status
        '0',                            # retry_count
        '',                             # next_retry_time
        'false',                        # whatsapp_sent
        'false'                         # email_sent
        # Rest of columns will be empty
    ]
    worksheet.append_row(row)
    print(f"✅ Added: {lead['name']}")

print(f"\n🎉 Uploaded {len(leads)} leads!")
```

---

### **Bulk Upload Validation**

After uploading, verify:
- [ ] All numbers start with `+`
- [ ] All numbers have country code
- [ ] Names are filled
- [ ] Partner is filled
- [ ] call_status is `pending`
- [ ] No duplicate numbers

**Check in Dashboard**:
1. Go to http://localhost:5001 (or production URL)
2. Verify leads appear in table
3. Check "Call Status" shows "pending"

---

## ⏰ SCHEDULING DETAILS

### **APScheduler Configuration**

**Location**: `src/scheduler.py`

**Jobs Configured**:

#### **1. Call Orchestrator Job**
- **Trigger**: Interval (every 60 seconds)
- **Function**: `run_call_orchestrator_job()`
- **Purpose**: Process pending leads and retries
- **Configurable**: `ORCHESTRATOR_INTERVAL_SECONDS` in .env

**What it does**:
1. Checks Google Sheet for leads with:
   - `call_status = 'pending'` (new leads)
   - `call_status = 'missed'` AND `next_retry_time` has passed
2. Initiates calls for eligible leads
3. Updates sheet with call status

#### **2. Email Poller Job** (Optional)
- **Trigger**: Interval (every 60 seconds)
- **Function**: `run_email_poller_job()`
- **Purpose**: Check for email replies from leads
- **Configurable**: `IMAP_POLL_SECONDS` in .env
- **Requires**: IMAP settings in .env

#### **3. Call Reconciliation Job**
- **Trigger**: Interval (every 5 minutes)
- **Function**: `run_reconciliation_job()`
- **Purpose**: Fix calls stuck at "initiated" status
- **Configurable**: `RECONCILIATION_INTERVAL_SECONDS` in .env

**What it does**:
1. Finds leads stuck at "initiated" for > 10 minutes
2. Checks Vapi API for actual call status
3. Updates sheet with correct status

#### **4. One-Time Callback Jobs**
- **Trigger**: Date (specific datetime)
- **Function**: `trigger_callback_call(lead_uuid)`
- **Purpose**: Execute scheduled callbacks
- **Created**: Dynamically when student requests callback

---

### **Why APScheduler (Not Cron)?**

| Feature | Cron | APScheduler |
|---------|------|-------------|
| **Platform** | Linux/Mac only | All platforms ✅ |
| **Configuration** | System-level | Application-level ✅ |
| **Monitoring** | External tools | Built-in API ✅ |
| **Dynamic Jobs** | Difficult | Easy ✅ |
| **Error Handling** | Limited | Comprehensive ✅ |
| **Deployment** | Manual setup | Auto-deployed ✅ |
| **Timezone** | System timezone | Configurable ✅ |

**Result**: APScheduler is better for our use case!

---

## 🎯 MONITORING & CONTROL

### **View Scheduled Jobs**

**API Endpoint**: `GET /api/jobs`

```bash
curl http://localhost:5001/api/jobs
```

**Response**:
```json
{
  "jobs": [
    {
      "id": "call_orchestrator",
      "name": "Call Orchestration Job",
      "next_run_time": "2025-10-13T15:31:00+05:30",
      "trigger": "interval[0:01:00]"
    },
    {
      "id": "email_poller",
      "name": "Email Polling Job",
      "next_run_time": "2025-10-13T15:31:00+05:30",
      "trigger": "interval[0:01:00]"
    },
    {
      "id": "callback_uuid-123_1697198400.0",
      "name": "One-time Callback",
      "next_run_time": "2025-10-14T17:00:00+05:30",
      "trigger": "date[2025-10-14 17:00:00 IST]"
    }
  ]
}
```

### **Manually Trigger a Job**

**API Endpoint**: `POST /api/jobs/<job_id>/trigger`

```bash
# Trigger call orchestrator immediately
curl -X POST http://localhost:5001/api/jobs/call_orchestrator/trigger
```

**Use Case**: Force check for pending leads without waiting for next scheduled run

---

## 📊 RETRY FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    LEAD ADDED TO SHEET                      │
│                   call_status = "pending"                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              APScheduler (Every 60 seconds)                 │
│           Checks: pending leads + retry leads               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Initiate Call  │
                    └─────────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
              ┌──────────┐        ┌──────────┐
              │ Answered │        │  Missed  │
              └──────────┘        └──────────┘
                    │                    │
                    ▼                    ▼
            ┌─────────────┐    ┌──────────────────┐
            │  Process    │    │ retry_count < 3? │
            │  Analysis   │    └──────────────────┘
            └─────────────┘            │
                    │            ┌─────┴──────┐
                    ▼            ▼            ▼
                ┌────────┐   ┌─────┐    ┌─────────┐
                │  Done  │   │ YES │    │   NO    │
                └────────┘   └─────┘    └─────────┘
                                │            │
                                ▼            ▼
                        ┌──────────────┐  ┌──────────┐
                        │ Schedule     │  │ Fallback │
                        │ Next Retry   │  │ WhatsApp │
                        │ (30min/24hr) │  │ + Email  │
                        └──────────────┘  └──────────┘
                                │
                                ▼
                        (Loop back to top)
```

---

## 📋 BULK UPLOAD TEMPLATE

### **Excel/CSV Template**

Download or create this template:

```csv
lead_uuid,number,whatsapp_number,name,email,partner,call_status
,+919876543210,+919876543210,Prathamesh Kumar,prathamesh@example.com,Physics Wallah,pending
,+918765432109,+918765432109,Rahul Sharma,rahul@example.com,Leverage Edu,pending
,+919988776655,,Priya Singh,priya@example.com,IDP,pending
,+447911123456,+447911123456,John Smith,john@example.com,British Council,pending
,+14155552671,+14155552671,Sarah Johnson,sarah@example.com,EducationUSA,pending
```

**Important**:
- ✅ Leave `lead_uuid` empty (auto-generated)
- ✅ `number` must have `+` and country code
- ✅ `whatsapp_number` can be same as `number` or empty
- ✅ `call_status` should be `pending`
- ✅ All other columns will be filled by system

---

### **Phone Number Validation**

**Before uploading, validate numbers**:

```python
# validate_numbers.py
import re

def validate_phone(number):
    """Validate phone number format"""
    # Must start with + followed by 10-15 digits
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, number))

# Test
numbers = [
    '+919876543210',    # ✅ Valid
    '9876543210',       # ❌ Missing +
    '+91 9876543210',   # ❌ Has space
    '+91-9876543210'    # ❌ Has dash
]

for num in numbers:
    print(f"{num}: {'✅ Valid' if validate_phone(num) else '❌ Invalid'}")
```

---

### **Bulk Upload Checklist**

Before uploading leads:

- [ ] All numbers have `+` prefix
- [ ] All numbers have country code
- [ ] No spaces or special characters in numbers
- [ ] Names are filled (required)
- [ ] Partner is filled (required)
- [ ] Email is valid format (if provided)
- [ ] call_status is `pending` (or empty)
- [ ] No duplicate numbers

After uploading:

- [ ] Verify leads appear in dashboard
- [ ] Check first lead shows "pending" status
- [ ] Wait 60 seconds (orchestrator runs)
- [ ] Verify first call is initiated
- [ ] Check Google Sheet for status updates

---

## ⚙️ ADVANCED CONFIGURATION

### **Change Orchestrator Frequency**

**Current**: Checks every 60 seconds

**To change**:
```bash
# Check every 30 seconds (more aggressive)
ORCHESTRATOR_INTERVAL_SECONDS=30

# Check every 2 minutes (less aggressive)
ORCHESTRATOR_INTERVAL_SECONDS=120
```

**Recommendation**: Keep at 60 seconds (good balance)

---

### **Disable Retries** (Not Recommended)

If you want to disable retries:
```bash
MAX_RETRY_COUNT=1
```

This means:
- Only 1 call attempt
- If missed, immediately trigger WhatsApp/Email fallback
- No retries

---

### **Change Fallback Behavior**

**Current**: After max retries → WhatsApp → Email

**To disable WhatsApp fallback**:
```bash
WHATSAPP_ENABLE_FALLBACK=false
```

**To disable Email fallback**:
```bash
# Don't set IMAP credentials
# Or set EMAIL_SUBJECT to empty
```

---

## 📊 MONITORING RETRIES

### **In Dashboard**

Each lead shows:
- **Call Status**: pending, initiated, missed, completed
- **Retry Count**: 0, 1, 2, 3
- **Next Retry Time**: When next call will be attempted (IST)

### **In Google Sheets**

Columns to monitor:
- `call_status`: Current status
- `retry_count`: How many attempts made
- `next_retry_time`: When next retry scheduled (IST format)
- `last_call_time`: When last attempt was made (IST)
- `last_ended_reason`: Why last call ended

### **In Logs**

```bash
# Render logs or local logs/app.log
[Scheduler] Found 5 leads due for retry
[Scheduler] Processing lead: Prathamesh (retry 2/3)
[CallReport] Call missed, scheduling retry 3 in 24 hours
[CallReport] Max retries reached, triggering WhatsApp fallback
```

---

## ✅ SUMMARY

### **Retry Mechanism**
- ✅ **System**: APScheduler (better than cron)
- ✅ **Default**: 3 attempts (30min, 24hr intervals)
- ✅ **Configurable**: Via .env variables
- ✅ **Fallback**: WhatsApp + Email after max retries
- ✅ **Monitoring**: API endpoints + dashboard

### **Bulk Upload**
- ✅ **Format**: CSV or direct Google Sheets
- ✅ **Phone**: Must be +CountryCode + Number (no spaces)
- ✅ **Required**: number, name, partner
- ✅ **Optional**: whatsapp_number, email
- ✅ **Validation**: Check format before uploading

### **Scheduling**
- ✅ **System**: APScheduler (not cron)
- ✅ **Jobs**: 4 types (orchestrator, email, reconciliation, callbacks)
- ✅ **Frequency**: Every 60 seconds (configurable)
- ✅ **Timezone**: IST throughout
- ✅ **Control**: API endpoints for monitoring

---

## 🎯 RECOMMENDATIONS

### **For Retry Intervals**
**Current**: 30min, 24hr (good for most cases)

**If leads are urgent**: 15min, 2hr, 24hr
**If leads are patient**: 1hr, 4hr, 48hr

### **For Bulk Upload**
1. **Start small**: Upload 5-10 leads first to test
2. **Validate format**: Check phone numbers carefully
3. **Monitor**: Watch first batch complete before uploading more
4. **Batch size**: Upload 50-100 leads at a time (not 1000s)

### **For Scheduling**
- **Keep default**: 60 seconds is optimal
- **Don't go below 30s**: Too aggressive, wastes resources
- **Don't go above 120s**: Leads wait too long

---

**You're all set with retry mechanism and bulk upload!** 🚀

Any questions about retry intervals or upload format?
