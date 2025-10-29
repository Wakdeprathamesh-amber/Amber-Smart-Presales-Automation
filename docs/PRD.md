# Amber Smart Presales Automation - Product Requirements Document (PRD)

**Version:** 2.0  
**Last Updated:** January 2025  
**Status:** Production Ready - Phase 1-3 Complete

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Technical Stack](#technical-stack)
4. [Core Components](#core-components)
5. [API Endpoints](#api-endpoints)
6. [Data Models](#data-models)
7. [Integration Details](#integration-details)
8. [Orchestration & Workflows](#orchestration--workflows)
9. [Observability & Monitoring](#observability--monitoring)
10. [Dashboard Features](#dashboard-features)
11. [Error Handling & Resilience](#error-handling--resilience)
12. [Security & Compliance](#security--compliance)
13. [Deployment & Configuration](#deployment--configuration)
14. [Performance & Scalability](#performance--scalability)
15. [Roadmap & Future Enhancements](#roadmap--future-enhancements)

---

## 1. Executive Summary

### 1.1 Problem Statement
- Manual outbound calling by presales team causes delays and missed opportunities
- Inconsistent retry mechanisms for failed calls
- No automated follow-up via WhatsApp/Email
- Limited visibility into call outcomes and lead qualification status
- Lack of structured data capture from conversations

### 1.2 Solution Overview
An AI-powered presales automation system that:
- **Automates outbound calls** using Vapi AI voice assistant
- **Manages lead lifecycle** with intelligent retry logic and fallback mechanisms
- **Captures structured data** from conversations (country, university, intake, budget, etc.)
- **Provides multi-channel follow-up** (WhatsApp, Email, Callback scheduling)
- **Offers real-time dashboard** for monitoring and managing leads
- **Integrates observability** (LangFuse) for LLM tracing and conversation analysis

### 1.3 Key Achievements
✅ **Phase 1:** Codebase cleanup and consolidation  
✅ **Phase 2:** Standardized orchestration (APScheduler + LangGraph)  
✅ **Phase 3:** Full observability integration (LangFuse)  
✅ **Production Ready:** All 10 critical issues resolved  
✅ **Features:** Bulk scheduling, phone sanitization, IST timezone, retry management

### 1.4 Success Metrics
- **Contact Rate:** % of leads with answered calls within 3 attempts
- **Completion Rate:** % of initiated calls that complete with analysis
- **Qualification Rate:** % leads marked Qualified/Potential
- **Time-to-First-Contact:** Average time from lead creation to first call
- **Multi-Channel Engagement:** WhatsApp/Email fallback success rate
- **Call Quality:** Transcript accuracy, conversation sentiment analysis

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Flask Web Dashboard (HTML/CSS/JS)                      │  │
│  │  - Real-time lead management                           │  │
│  │  - Bulk operations UI                                  │  │
│  │  - Call scheduling interface                           │  │
│  │  - Analytics & monitoring                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬──────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Flask REST API (src/app.py)                           │  │
│  │  - GET  /api/leads                                      │  │
│  │  - POST /api/leads/bulk-upload                         │  │
│  │  - POST /api/leads/:uuid/call                          │  │
│  │  - POST /api/schedule-bulk-calls                       │  │
│  │  - POST /webhook/vapi                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬──────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┬──────────────┬────────────┐
         ▼                       ▼              ▼            ▼
┌──────────────┐     ┌──────────────┐  ┌────────────┐  ┌──────────────┐
│  Orchestration│     │ Data Layer   │  │  External  │  │ Observability│
│               │     │              │  │  Services  │  │              │
│ APScheduler   │     │ Google Sheets│  │    Vapi    │  │   LangFuse   │
│ (Time-based)  │     │              │  │            │  │              │
│               │     │              │  │  WhatsApp  │  │   Tracing    │
│ LangGraph     │     │              │  │            │  │   Analysis   │
│ (Workflow)    │     │              │  │   Email    │  │              │
└───────────────┘     └──────────────┘  └────────────┘  └──────────────┘
```

### 2.2 Component Breakdown

#### 2.2.1 Frontend (Static Files)
- **Location:** `src/templates/index.html`, `src/static/css/style.css`, `src/static/js/dashboard.js`
- **Technology:** Vanilla HTML/CSS/JavaScript (no framework)
- **Key Features:**
  - Real-time dashboard with auto-refresh
  - Bulk lead operations (upload, call, delete)
  - Bulk call scheduling with time picker
  - Lead details modal with call history
  - IST timezone display throughout UI

#### 2.2.2 Backend API (Flask)
- **Location:** `src/app.py`
- **Features:**
  - RESTful API endpoints
  - In-memory caching for performance
  - Webhook handling for Vapi events
  - Batch operations with error handling
  - Cache invalidation on data updates

#### 2.2.3 Orchestration Engine
- **Location:** `src/scheduler.py`
- **Technology:** APScheduler + SQLAlchemy (persistent job store)
- **Components:**
  - Time-based scheduling (APScheduler)
  - Stateful workflows (LangGraph)
  - Retry management
  - Bulk call execution
  - Callback scheduling

#### 2.2.4 Data Management
- **Location:** `src/sheets_manager.py`
- **Features:**
  - Optimized Google Sheets API usage
  - Header caching
  - Batched updates
  - UUID-based lookups
  - Multi-field updates in single call

#### 2.2.5 External Integrations
- **Vapi Client:** `src/vapi_client.py` - Voice AI calls
- **WhatsApp Client:** `src/whatsapp_client.py` - Messaging
- **Email Client:** `src/email_client.py` - SMTP/IMAP handling
- **Webhook Handler:** `src/webhook_handler.py` - Event processing

#### 2.2.6 Observability
- **Location:** `src/observability.py`
- **Technology:** LangFuse SDK
- **Features:**
  - LLM call tracing
  - Workflow node instrumentation
  - Conversation logging
  - Call analysis tracking

---

## 3. Technical Stack

### 3.1 Core Technologies
```yaml
Backend:
  - Python: 3.13
  - Framework: Flask 2.3.3
  - Task Scheduler: APScheduler 3.10.4
  - Workflow Engine: LangGraph 0.2.35
  - Database: SQLAlchemy 1.4.53 (for job persistence)
  - HTTP Client: requests 2.31.0

Data Layer:
  - Google Sheets API: gspread 5.12.0
  - OAuth: google-auth-oauthlib 1.2.2

External Integrations:
  - Voice AI: Vapi API
  - Messaging: WhatsApp Cloud API
  - Email: SMTP/IMAP

Observability:
  - LangFuse: 2.20.0
  - LangChain: 0.3.7 (workflow support)

Utilities:
  - Timezone: pytz 2024.1
  - Environment: python-dotenv 1.0.0
```

### 3.2 Infrastructure
- **Hosting:** Render (cloud platform)
- **Database:** SQLite (for APScheduler job store)
- **Storage:** Google Sheets (for lead data)
- **Webhooks:** Vapi, WhatsApp (Cloud API)

---

## 4. Core Components

### 4.1 Sheets Manager (`src/sheets_manager.py`)

**Purpose:** Manages all Google Sheets operations with optimization

#### Key Methods:
```python
class SheetsManager:
    def __init__(self, credentials_file: str, sheet_id: str)
    
    # Core CRUD
    def get_all_leads(self) -> List[dict]
    def add_lead(self, lead_data: dict) -> int  # Returns row index
    def delete_lead(self, lead_uuid: str) -> bool
    
    # Updates
    def update_lead_status(self, row_index: int, status: str)
    def update_lead_fields(self, row_index: int, fields: dict)  # Batch update
    def update_retry_info(self, row_index: int, retry_count: int, next_retry: str)
    def update_call_info(self, row_index: int, call_id: str, call_time: str)
    def update_analysis(self, row_index: int, summary: str, status: str, structured: dict)
    def update_transcript(self, row_index: int, transcript: str)
    
    # Lookup
    def find_row_by_lead_uuid(self, lead_uuid: str) -> int
    def get_lead_by_uuid(self, lead_uuid: str) -> dict
    
    # Optimization
    def _get_headers(self, worksheet_name: str = "Leads") -> List[str]
    def _with_retry(self, func, *args, **kwargs)  # Exponential backoff
```

#### Optimizations:
- **Header Caching:** Prevents repeated header reads
- **Batched Updates:** Multiple cell updates in single API call
- **UUID Lookups:** Reads only `lead_uuid` column for faster searches
- **Retry Logic:** Exponential backoff for 429 (quota exceeded)
- **Multi-field Updates:** Single call to update multiple columns

### 4.2 Vapi Client (`src/vapi_client.py`)

**Purpose:** Handles outbound call initiation via Vapi API

#### Key Methods:
```python
class VapiClient:
    def __init__(self, api_key: str, assistant_id: str, phone_number_id: str)
    
    def initiate_outbound_call(
        self,
        lead_data: dict,
        assistant_id: str = None,
        phone_number_id: str = None
    ) -> dict:
        """
        Initiates an outbound call via Vapi
        
        Returns:
            - {"id": "call_123", "status": "queued", ...}
            - {"error": "message"} on failure
        """
```

#### Features:
- **Phone Number Sanitization:** Automatically removes extra `+` symbols
- **Validation:** Ensures phone number format is correct (E.164)
- **Logging:** Detailed error logging for debugging
- **Observability:** Integrated with LangFuse tracing
- **IST Timestamps:** All times stored in IST timezone

#### Phone Number Handling:
```python
# Removes double ++ and ensures proper format
# ++91 9876543210 → +919876543210
# +919876543210 → +919876543210 (no change)
# 91 9876543210 → +919876543210
```

### 4.3 Webhook Handler (`src/webhook_handler.py`)

**Purpose:** Processes real-time events from Vapi

#### Webhook Event Types:
1. **`status-update`**: Call status changes
   - `queued` → `ringing` → `in-progress` → `ended`
   
2. **`end-of-call-report`**: Call completion data
   - Transcript
   - Analysis (summary, structured data, success evaluation)
   - Metadata (duration, recording URL)

#### Key Methods:
```python
class WebhookHandler:
    def handle_webhook(self, data: dict) -> Response
    
    def _handle_status_update(self, event_data: dict)
    def _handle_call_report(self, event_data: dict)
    
    # Status mapping
    def _map_status_to_db(self, vapi_status: str) -> str:
        """
        Maps Vapi statuses to our database statuses:
        - queued → initiated
        - ringing → initiated
        - in-progress → answered
        - ended → completed/missed/failed
        """
    
    # Analysis handling
    def _store_analysis(self, lead_row: int, analysis: dict)
    def _extract_transcript(self, message: dict) -> str
```

#### Transcript Extraction:
- Filters system prompts
- Removes very long messages (>1000 chars)
- Formats with "Eshwari" and lead's first name
- Stores in `transcript` column in Google Sheets

### 4.4 Orchestration (`src/scheduler.py`)

**Purpose:** Manages background jobs and workflows

#### Scheduler Configuration:
```python
def create_scheduler():
    """
    Creates APScheduler with:
    - SQLAlchemyJobStore (persistent across restarts)
    - IST timezone
    - Job execution configuration
    """
```

#### Background Jobs:
1. **Call Orchestrator** (every 60s)
   - Finds eligible leads (retry due or new)
   - Initiates calls via workflow
   - Updates status immediately

2. **Email Poller** (every 300s)
   - Checks IMAP inbox for replies
   - Processes email responses
   - Updates lead status

3. **Reconciliation Job** (every 3600s)
   - Compares sheet status with Vapi status
   - Handles stuck statuses

#### Workflow Integration:
```python
# Uses LangGraph for stateful workflows
use_langgraph = os.getenv('USE_LANGGRAPH', 'true').lower() == 'true'

if use_langgraph:
    from src.workflows import get_workflow
    workflow = get_workflow()
    
    result = workflow.invoke(initial_state, config)
else:
    # Legacy orchestrator (fallback)
    run_legacy_call_orchestrator()
```

### 4.5 Workflow Engine (`src/workflows/lead_workflow.py`)

**Purpose:** Defines stateful lead engagement workflows

#### Workflow Nodes:
```python
# Node 1: Initiate Call
def initiate_call_node(state: LeadState) -> dict:
    # - Call Vapi API
    # - Store call_id
    # - Update status to "initiated"
    # - Log to LangFuse

# Node 2: Check Retry
def check_retry_node(state: LeadState) -> str:
    # Returns: "retry", "fallback", or "complete"
    # Based on: retry_count, call_status

# Node 3: Increment Retry
def increment_retry_node(state: LeadState) -> dict:
    # - Increment retry_count
    # - Calculate next_retry_time
    # - Exit workflow (don't loop back!)

# Node 4: WhatsApp Fallback
def whatsapp_fallback_node(state: LeadState) -> dict:
    # - Send WhatsApp message
    # - Update whatsapp_sent = True
    # - Log to LangFuse

# Node 5: Email Fallback
def email_fallback_node(state: LeadState) -> dict:
    # - Send Email
    # - Update email_sent = True
    # - Log to LangFuse
```

#### Workflow Graph:
```
START → initiate_call → check_retry
                             ├─→ [retry_count < max] → increment_retry → END
                             ├─→ [retry_count >= max] → whatsapp_fallback → END
                             └─→ [call completed] → END

Note: increment_retry exits to END (no immediate retry loop)
      APScheduler schedules next attempt (1h, 4h, 24h later)
```

### 4.6 Observability (`src/observability.py`)

**Purpose:** LLM tracing and conversation monitoring

#### Features:
```python
# LangFuse Client
def get_langfuse_client() -> Langfuse:
    """
    Initializes LangFuse client with:
    - Public/Secret keys from env
    - Host region (US/EU)
    - Debug mode option
    """

# Decorators
@trace_vapi_call
def initiate_call(...):
    # Automatically traces Vapi API calls

@trace_workflow_node("node_name")
def workflow_node(state):
    # Automatically traces workflow execution

@trace_webhook_event("event_type", lead_uuid, data)
def handle_webhook(...):
    # Traces incoming webhooks

# Manual Logging
def log_call_analysis(lead_uuid, summary, status, structured_data):
    # Logs post-call analysis

def log_conversation_message(lead_uuid, channel, direction, content):
    # Logs WhatsApp/Email messages
```

#### Traces Collected:
1. **Vapi Calls**: Request/response, phone number, call result
2. **Workflow Nodes**: State transitions, retry logic, fallbacks
3. **Webhooks**: Event types, status changes, analysis received
4. **Conversations**: WhatsApp/Email sent and received
5. **Call Analysis**: Summary, qualification, structured data

### 4.7 Utilities (`src/utils.py`)

**Purpose:** Common utilities for timezone, phone numbers, names

#### Timezone Functions:
```python
def get_ist_timestamp() -> str
def get_ist_now() -> datetime
def parse_ist_timestamp(timestamp: str) -> datetime
def add_hours_ist(hours: int) -> str
```

#### Phone Number Functions:
```python
def sanitize_phone_number(phone: str) -> str:
    """Removes extra + and spaces, ensures E.164 format"""
    
def validate_phone_number(phone: str) -> bool:
    """Validates phone number format"""
    
def format_phone_display(phone: str) -> str:
    """Formats for display in UI"""
```

#### Name Functions:
```python
def extract_first_name(full_name: str) -> str:
    """Extracts first name for greetings
    
    Examples:
    - "DINESH BASKARAN SHANTHI" → "DINESH"
    - "Nikhila Abbarla" → "Nikhila"
    - "ANIRUDH REDDY KOMMULA" → "ANIRUDH"
    """
```

---

## 5. API Endpoints

### 5.1 Dashboard
```
GET /
Description: Serves the main dashboard HTML
Response: HTML page
```

### 5.2 Leads Management

#### Get All Leads
```http
GET /api/leads
Query Parameters:
  - refresh: boolean (default: false) - Force cache refresh

Response:
{
  "leads": [
    {
      "lead_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "name": "John Doe",
      "number": "+919876543210",
      "email": "john@example.com",
      "whatsapp_number": "+919876543210",
      "partner": "Physics wallah",
      "call_status": "initiated",
      "success_status": "Qualified",
      "retry_count": 1,
      "next_retry_time": "2025-01-15T14:00:00+05:30",
      "last_call_time": "2025-01-15T10:00:00+05:30",
      "vapi_call_id": "call_123",
      "call_duration": "120s",
      "recording_url": "https://...",
      "summary": "Student interested in studying in USA...",
      "structured_data": {
        "country": "USA",
        "university": "MIT",
        "intake": "Fall 2025",
        "visa_status": "Applying",
        "budget": "$1500/month"
      },
      "transcript": "Eshwari: Hi Prathamesh...\nPrathamesh: I'm looking to study...",
      "whatsapp_sent": false,
      "email_sent": false,
      "created_at": "2025-01-15T09:00:00+05:30"
    }
  ]
}
```

#### Get Lead Details
```http
GET /api/leads/:lead_uuid/details
Response:
{
  "lead_uuid": "...",
  "contact_info": {...},
  "call_history": [...],
  "analysis": {...},
  "messages": [...]
}
```

#### Add Lead
```http
POST /api/leads
Body:
{
  "name": "John Doe",
  "number": "+919876543210",
  "email": "john@example.com",
  "whatsapp_number": "+919876543210",
  "partner": "Physics wallah"
}

Response:
{
  "success": true,
  "lead_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "row_index": 2
}
```

#### Delete Lead
```http
DELETE /api/leads/:lead_uuid
Response:
{
  "success": true,
  "lead_uuid": "..."
}
```

### 5.3 Call Operations

#### Initiate Single Call
```http
POST /api/leads/:lead_uuid/call
Response:
{
  "success": true,
  "call_id": "call_123",
  "status": "queued"
}
```

#### Bulk Call
```http
POST /api/leads/bulk-call
Body:
{
  "lead_uuids": ["uuid1", "uuid2", "uuid3"]
}

Response:
{
  "success": true,
  "calls_initiated": 3,
  "errors": []
}
```

### 5.4 Bulk Scheduling

#### Schedule Bulk Calls
```http
POST /api/schedule-bulk-calls
Body:
{
  "lead_uuids": ["uuid1", "uuid2", "uuid3"],
  "schedule_time": "2025-01-15T14:30:00+05:30",
  "parallel_calls": 5,
  "batch_interval": 120
}

Response:
{
  "success": true,
  "schedule_id": "schedule_123",
  "total_leads": 50,
  "estimated_completion": "2025-01-15T15:40:00+05:30"
}
```

#### Get Scheduled Calls
```http
GET /api/scheduled-bulk-calls
Response:
{
  "schedules": [
    {
      "schedule_id": "schedule_123",
      "created_at": "2025-01-15T10:00:00+05:30",
      "scheduled_time": "2025-01-15T14:30:00+05:30",
      "total_leads": 50,
      "parallel_calls": 5,
      "batch_interval": 120,
      "status": "pending"
    }
  ]
}
```

#### Cancel Scheduled Calls
```http
POST /api/cancel-bulk-schedule/:schedule_id
Response:
{
  "success": true,
  "cancelled": true
}
```

### 5.5 Bulk Upload

#### Upload CSV
```http
POST /api/leads/bulk-upload
Body: multipart/form-data
  - file: CSV file with columns: number, name, email, whatsapp_number, partner

Response:
{
  "success": true,
  "rows_added": 50,
  "errors": []
}
```

**CSV Format:**
```csv
number,name,email,whatsapp_number,partner
+919876543210,John Doe,john@example.com,+919876543210,Physics wallah
+919876543211,Jane Smith,jane@example.com,,Career Mosaic
```

**Phone Number Handling:**
- Spaces automatically removed
- Missing `+` automatically added
- Extra `++` symbols removed
- Validated before storage

### 5.6 Webhooks

#### Vapi Webhook
```http
POST /webhook/vapi
Body:
{
  "message": {
    "type": "status-update" | "end-of-call-report",
    "call": {...},
    "status": "queued" | "ringing" | "in-progress" | "ended",
    "artifact": {
      "transcript": [...],
      "analysis": {...}
    }
  }
}

Response: 200 OK
```

#### WhatsApp Webhook (Future)
```http
POST /webhook/whatsapp
Body:
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [...],
        "statuses": [...]
      }
    }]
  }]
}
```

### 5.7 System Endpoints

#### Health Check
```http
GET /health
Response:
{
  "status": "ok",
  "timestamp": "2025-01-15T10:00:00+05:30"
}
```

#### Version Info
```http
GET /api/version
Response:
{
  "version": "2.0",
  "last_updated": "2025-01-15",
  "recent_fixes": [
    "Fixed immediate retry loop",
    "Added phone sanitization",
    "Implemented IST timezone"
  ],
  "phone_sanitization_test": {
    "input": "91 9876543210",
    "output": "+919876543210",
    "has_double_plus_bug": false,
    "status": "FIXED"
  }
}
```

#### Job Status
```http
GET /api/jobs
Response:
{
  "jobs": [
    {
      "id": "call_orchestrator",
      "next_run": "2025-01-15T10:01:00+05:30",
      "status": "scheduled"
    }
  ]
}
```

---

## 6. Data Models

### 6.1 Google Sheets Structure

#### Leads Sheet
**Sheet Name:** `Leads`

**Columns (30 total):**
```python
columns = [
    # Identity
    "lead_uuid",           # UUID v4 identifier
    "number",              # E.164 format phone number
    
    # Contact Info
    "name",                # Full name or first name
    "email",               # Email address
    "whatsapp_number",     # WhatsApp number (defaults to number)
    "partner",             # Partner/source name
    
    # Call Status
    "call_status",         # pending | initiated | answered | missed | failed | completed
    
    # Retry Management
    "retry_count",         # Integer (0, 1, 2, 3, ...)
    "next_retry_time",     # ISO timestamp (IST)
    "max_retry_count",    # Integer (default: 3)
    
    # Call Tracking
    "vapi_call_id",        # Vapi call ID
    "last_call_time",      # ISO timestamp (IST)
    "call_duration",       # Seconds (e.g., "120")
    "recording_url",       # Vapi recording URL
    
    # Analysis
    "summary",             # AI-generated summary
    "success_status",      # Qualified | Potential | Not Qualified
    "structured_data",     # JSON string
    "country",             # Parsed from structured_data
    "university",          # Parsed from structured_data
    "intake",              # Parsed from structured_data
    "visa_status",         # Parsed from structured_data
    "budget",              # Parsed from structured_data
    "transcript",          # Conversation transcript
    "analysis_received_at", # ISO timestamp (IST)
    
    # Channels
    "whatsapp_sent",       # Boolean (true/false)
    "email_sent",          # Boolean (true/false)
    
    # Metadata
    "created_at",          # ISO timestamp (IST)
    "last_updated_at"      # ISO timestamp (IST)
]
```

#### Conversations Sheet (Future)
**Sheet Name:** `Conversations`

**Columns:**
```python
[
    "message_uuid",
    "lead_uuid",
    "channel",            # whatsapp | email | call
    "direction",          # outbound | inbound
    "content",
    "timestamp",
    "status",             # sent | delivered | read | error
    "metadata"            # JSON (delivery receipts, etc.)
]
```

### 6.2 State Models

#### LeadState (Workflow)
```python
class LeadState(TypedDict):
    lead_uuid: str
    lead_number: str
    lead_name: str
    lead_email: str
    lead_whatsapp: str
    partner: str
    
    call_status: str
    retry_count: int
    max_retry_count: int
    
    vapi_call_id: Optional[str]
    call_result: Optional[dict]
    
    next_action: str  # call | retry | fallback | complete
```

#### CallAnalysis (Webhook)
```python
class CallAnalysis(TypedDict):
    summary: str
    success_status: str  # Qualified | Potential | Not Qualified
    structured_data: dict
    transcript: str
    duration: int  # seconds
    recording_url: str
```

### 6.3 Job Store (SQLAlchemy)

**Database:** `jobs.sqlite`

**Tables:**
- `apscheduler_jobs` - Scheduled jobs (APScheduler internal)
- Persistent across server restarts

---

## 7. Integration Details

### 7.1 Vapi Integration

#### Configuration
```env
VAPI_API_KEY=sk-...
VAPI_ASSISTANT_ID=asst-123
VAPI_PHONE_NUMBER_ID=1ff83ff6-11c9-4d73-8d0b-35c7037d77ea
VAPI_CONCURRENT_LIMIT=5  # Max concurrent calls
```

#### API Calls
```python
# Initiate Call
POST https://api.vapi.ai/call
Headers:
  Authorization: Bearer {VAPI_API_KEY}
Body:
{
  "assistantId": "{ASSISTANT_ID}",
  "phoneNumberId": "{PHONE_NUMBER_ID}",
  "customer": {
    "number": "+919876543210"
  },
  "customVariables": {
    "name": "Prathamesh",  # First name only
    "partner": "Physics wallah"
  }
}

Response:
{
  "id": "call_123",
  "status": "queued",
  "createdAt": "2025-01-15T10:00:00Z"
}
```

#### Webhooks Received
- `status-update`: Call status changes (queued, ringing, in-progress, ended)
- `end-of-call-report`: Analysis, transcript, metadata

#### Error Handling
- **403 Forbidden (SIP)**: Vapi credits, phone config, carrier issue
- **400 Bad Request**: Invalid phone number format
- **429 Rate Limit**: Too many concurrent calls

### 7.2 WhatsApp Cloud API Integration

#### Configuration
```env
WHATSAPP_CLOUD_ACCESS_TOKEN=EAA...
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_WABA_ID=123456789012345
```

#### Sending Messages
```python
POST https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages
Headers:
  Authorization: Bearer {WHATSAPP_CLOUD_ACCESS_TOKEN}
Body:
{
  "messaging_product": "whatsapp",
  "to": "+919876543210",
  "type": "template",
  "template": {
    "name": "lead_followup",
    "language": {"code": "en"},
    "components": [{
      "type": "body",
      "parameters": [
        {"type": "text", "text": "Prathamesh"},
        {"type": "text", "text": "https://amberstudent.com/book"}
      ]
    }]
  }
}
```

#### Template Names
- `lead_followup` - After completed call
- `retry_fallback` - Max retries reached
- `callback_available` - Callback request

### 7.3 Email Integration (SMTP/IMAP)

#### Configuration
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-specific-password

IMAP_HOST=imap.gmail.com
IMAP_PORT=993
```

#### Sending Emails
```python
# SMTP
smtplib.SMTP(host, port).sendmail(from, to, msg)

# Templates
templates/
  - lead_followup.html
  - retry_fallback.html
```

#### Polling for Replies
- Every 300s (5 minutes)
- Checks IMAP inbox
- Updates lead status on reply

### 7.4 Google Sheets Integration

#### API Usage Optimization
1. **Header Caching:** Cache headers to avoid repeated reads
2. **Batched Updates:** Multiple cells updated in single API call
3. **Column-specific Reads:** Read only needed columns (e.g., for UUID lookups)
4. **Exponential Backoff:** For 429 (quota exceeded) errors
5. **Batch Processing:** Group multiple updates into batches

#### Rate Limits
- **Quota:** 600 requests per minute per project
- **Strategy:** Cache + batch operations

#### Authentication
```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}
```

---

## 8. Orchestration & Workflows

### 8.1 APScheduler Configuration

#### Job Store
```python
SQLAlchemyJobStore(
    url='sqlite:///jobs.sqlite',
    tablename='apscheduler_jobs'
)
```

**Benefits:**
- Jobs persist across server restarts
- Can view/manage jobs manually
- Reliable schedule execution

#### Jobs Defined

**1. Call Orchestrator (60s interval)**
```python
def run_call_orchestrator_job():
    # Find eligible leads
    pending_leads = find_pending_leads()
    
    # Process each lead
    for lead in pending_leads:
        if USE_LANGGRAPH:
            # Use LangGraph workflow
            workflow.invoke(initial_state, config)
        else:
            # Use legacy orchestrator
            initiate_call(lead)
```

**2. Email Poller (300s interval)**
```python
def run_email_poller_job():
    # Check IMAP inbox for replies
    emails = check_inbox()
    
    # Update leads
    for email in emails:
        update_lead_from_email(email)
```

**3. Reconciliation Job (3600s interval)**
```python
def run_call_reconciliation_job():
    # Compare sheet status with Vapi status
    stuck_calls = find_stuck_calls()
    
    # Update or reschedule
    for call in stuck_calls:
        update_status_or_reschedule(call)
```

### 8.2 LangGraph Workflow

#### State Definition
```python
class LeadState(TypedDict):
    lead_uuid: str
    lead_number: str
    lead_name: str
    # ... other fields
    next_action: str
```

#### Nodes
```python
# Node 1: Initiate Call
@trace_workflow_node("initiate_call")
def initiate_call_node(state: LeadState) -> dict:
    # - Call Vapi
    # - Store call_id
    # - Update status
    # - Return new state

# Node 2: Check Retry (Conditional)
def check_retry_node(state: LeadState) -> str:
    if retry_count < max_retry_count:
        return "retry"
    elif retry_count >= max_retry_count:
        return "fallback"
    else:
        return "complete"

# Node 3: Increment Retry
def increment_retry_node(state: LeadState) -> dict:
    # - Increment retry_count
    # - Calculate next_retry_time
    # - EXIT workflow (no immediate loop!)

# Node 4: WhatsApp Fallback
@trace_workflow_node("whatsapp_fallback")
def whatsapp_fallback_node(state: LeadState) -> dict:
    # - Send WhatsApp
    # - Log conversation
    # - Return final state

# Node 5: Email Fallback
@trace_workflow_node("email_fallback")
def email_fallback_node(state: LeadState) -> dict:
    # - Send Email
    # - Log conversation
    # - Return final state
```

#### Workflow Graph
```
START
  ↓
initiate_call
  ↓
check_retry (conditional)
  ├─→ retry → increment_retry → END
  ├─→ fallback → whatsapp_fallback → END
  └─→ complete → END

Note: increment_retry does NOT loop back to initiate_call
      Instead, APScheduler schedules next attempt later
```

#### Critical Fix: No Immediate Retry Loop
```python
# BEFORE (WRONG):
workflow.add_edge("increment_retry", "initiate_call")
# This creates an immediate retry loop!
# Result: 3 calls in 10 seconds → Over Concurrency Limit

# AFTER (CORRECT):
workflow.add_edge("increment_retry", END)
# This exits workflow
# APScheduler schedules next attempt (1h, 4h, 24h later)
```

### 8.3 Retry Mechanism

#### Configuration
```env
MAX_RETRY_COUNT=3
RETRY_INTERVALS=1,4,24  # hours
RETRY_UNITS=hours
```

#### Retry Logic
```python
# After failed call:
retry_count = 0  → next retry in 1 hour
retry_count = 1  → next retry in 4 hours
retry_count = 2  → next retry in 24 hours
retry_count = 3  → max retries reached, trigger WhatsApp fallback
```

#### Retry Scenarios
1. **Missed Call** (no answer, voicemail)
2. **Failed Call** (carrier error, SIP error)
3. **Timeout** (call rings out)

#### No Retry For:
- Call completed successfully
- Student explicitly declined

### 8.4 Callback Scheduling

#### Trigger
Student requests callback during conversation:
> "Can you call me back at 3 PM today?"

#### Scheduling
```python
def schedule_one_time_callback(lead_uuid: str, callback_time: str):
    """
    Schedules a one-time callback
    
    Args:
        lead_uuid: Lead identifier
        callback_time: ISO timestamp (IST)
    """
    scheduler.add_job(
        func=trigger_callback_call,
        trigger='date',
        run_date=callback_time,
        args=[lead_uuid],
        id=f'callback_{lead_uuid}_{timestamp}'
    )
```

#### Execution
When callback time arrives:
1. Lookup lead from Google Sheets
2. Check lead status (not called recently)
3. Initiate call via workflow
4. Update `callback_scheduled` field

---

## 9. Observability & Monitoring

### 9.1 LangFuse Integration

#### Setup
1. Create account at https://us.cloud.langfuse.com
2. Get public key and secret key
3. Set environment variables:
```env
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
LANGFUSE_DEBUG=false
```

#### Tracing Implementation

**1. Vapi Calls**
```python
@trace_vapi_call
def initiate_outbound_call(...):
    # Automatically creates trace for Vapi API calls
    # Includes: request, response, phone number, call result
```

**2. Workflow Nodes**
```python
@trace_workflow_node("initiate_call")
def initiate_call_node(state):
    # Creates span for each workflow node execution
    # Includes: state, decision, outcome
```

**3. Webhooks**
```python
@trace_webhook_event("status-update", lead_uuid, data)
def handle_webhook(...):
    # Traces webhook events
    # Includes: event type, payload, processing time
```

**4. Conversations**
```python
log_conversation_message(
    lead_uuid="...",
    channel="whatsapp",
    direction="outbound",
    content="Hello Prathamesh...",
    metadata={"template": "lead_followup"}
)
```

#### Unified Trace Per Lead
```python
# Creates one trace per lead for their entire journey
trace_id = f"lead_call_journey_{lead_uuid}"

# All events go into this trace:
# - Vapi call initiation
# - Workflow execution
# - Webhooks
# - WhatsApp/Email messages
# - Call analysis
```

### 9.2 What's Tracked

#### Call Initiation
- Timestamp
- Phone number
- Vapi call ID
- Result (success/error)

#### Workflow Execution
- State transitions
- Node execution times
- Decisions made (retry/fallback)
- Error handling

#### Webhook Events
- Event type
- Call status changes
- Analysis received
- Transcript extraction

#### Conversations
- Channel (WhatsApp/Email/Call)
- Direction (outbound/inbound)
- Content (truncated)
- Status (sent/delivered/read)

#### Call Analysis
- Summary
- Qualification status
- Structured data
- Duration
- Recording URL

### 9.3 Dashboard Features

#### Metrics Shown
- **Total Leads:** All leads in system
- **Pending:** Not yet called
- **Initiated:** Calls in progress
- **Completed:** Successful calls
- **Failed:** Max retries reached

#### Filters
- Status (pending, initiated, completed, failed)
- Success Status (Qualified, Potential, Not Qualified)
- Partner/Source
- Date range

#### Actions
- View details
- Delete lead
- Retry call
- Send WhatsApp (manual)
- Schedule callback

---

## 10. Dashboard Features

### 10.1 Real-Time Updates

#### Cache Invalidation
```javascript
// After any lead modification:
fetch('/api/leads?refresh=true')  // Force cache refresh
```

#### Auto-Refresh
```javascript
// Refresh every 10s if active calls
if (hasActiveCalls) {
    setInterval(() => fetchLeads(), 10000)
}
```

### 10.2 Bulk Operations

#### Upload CSV
- Drag & drop file upload
- Validation (phone format, required fields)
- Preview before import
- Error reporting

#### Schedule Bulk Calls
- Lead selection (checkboxes)
- Time picker (IST)
- Parallel call configuration
- Batch interval selection (2 minutes recommended)
- Real-time summary
- Cancel scheduled calls

### 10.3 Lead Details Modal

**Sections:**
1. **Contact Information**
   - Name, Phone, Email, WhatsApp, Partner
   
2. **Call Status**
   - Current status, Retry count, Next retry time
   
3. **Call History**
   - All calls made (timestamps, durations, recordings)
   
4. **Analysis**
   - Summary, Success status, Structured data
   - Transcript (formatted with "Eshwari" and lead's first name)
   
5. **Recordings**
   - Recording URL (click to listen)

### 10.4 Phone Number Display

#### Formatting
```javascript
// In UI, display: +91 98765 43210
formatPhoneDisplay(phone) {
    // Format for readability
    // Groups digits with spaces
}
```

#### Validation Badges
- ✅ Valid (green)
- ⚠️ Invalid format (yellow)
- ❌ Missing (red)

### 10.5 Timezone Handling

#### All Times in IST
```python
# Backend: Always use IST
from src.utils import get_ist_timestamp
timestamp = get_ist_timestamp()

# Frontend: Display with IST label
Date: 2025-01-15 10:00 AM IST
```

#### Time Picker
```javascript
// Frontend time picker uses IST
<input type="datetime-local" data-timezone="IST">

// JavaScript explicitly constructs IST date
const istTime = new Date(`${date}T${time}+05:30`);
```

---

## 11. Error Handling & Resilience

### 11.1 Retry Mechanisms

#### Google Sheets API
```python
@backoff.on_exception(
    backoff.expo,
    (gspread.exceptions.APIError),
    max_tries=3
)
def _with_retry(func, *args, **kwargs):
    """
    Exponential backoff for 429 (quota exceeded)
    
    Attempt 1: Immediate
    Attempt 2: After 1s
    Attempt 3: After 2s
    """
```

#### Vapi API
- No automatic retry (called synchronously)
- Error logged and reported to user
- Call marked as "failed"

#### WhatsApp Cloud API
- Retry on 429 (rate limit)
- Retry on 500 (server error)
- Max 3 attempts

### 11.2 Error Classification

#### Call Statuses
```python
status_map = {
    "queued": "initiated",
    "ringing": "initiated",
    "in-progress": "answered",
    "ended": "completed",  # Or "missed" or "failed" based on reason
    "failed": "failed",
    "no-answer": "missed",
    "busy": "missed",
    "timeout": "missed"
}
```

#### Webhook Error Handling
```python
try:
    # Process webhook
    handle_webhook(data)
except Exception as e:
    # Log error
    logger.error(f"Webhook processing failed: {e}")
    # Return 200 (don't cause Vapi to retry)
    return Response(status=200)
```

### 11.3 Graceful Degradation

#### If Google Sheets is Slow
- Cache results for 10s
- Show "Refreshing..." indicator
- Allow force refresh

#### If Vapi is Down
- Queue calls for later
- Show error notification
- Don't lose leads

#### If Observability is Off
- Continue normal operation
- Log warnings (no blocking)

---

## 12. Security & Compliance

### 12.1 Environment Variables

#### Secrets Management
```env
# Never commit these files!
.env                    # Local development
config/prod.env         # Production (Render)
config/credentials-*.json  # Service account keys
```

#### Required Variables
```env
# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_FILE=config/credentials.json
LEADS_SHEET_ID=1xxx...

# Vapi
VAPI_API_KEY=sk-...
VAPI_ASSISTANT_ID=asst-...
VAPI_PHONE_NUMBER_ID=1ff83ff6-...

# WhatsApp (Optional)
WHATSAPP_CLOUD_ACCESS_TOKEN=EAA...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_WABA_ID=...

# Observability
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://us.cloud.langfuse.com

# Configuration
MAX_RETRY_COUNT=3
RETRY_INTERVALS=1,4,24
RETRY_UNITS=hours
VAPI_CONCURRENT_LIMIT=5
USE_LANGGRAPH=true
ENABLE_OBSERVABILITY=true
```

### 12.2 API Security

#### Rate Limiting (Future)
```python
# Add rate limiting
from flask_limiter import Limiter

limiter = Limiter(
    app=app,
    default_limits=["200 per day", "50 per hour"]
)
```

#### CORS (if needed)
```python
from flask_cors import CORS
CORS(app)
```

### 12.3 Data Privacy

#### No PII in Logs
```python
# Log UUID, not phone number
logger.info(f"Call initiated for {lead_uuid}")

# Sanitize phone numbers in logs
phone_display = phone[:3] + "..." + phone[-3:]
```

#### GDPR Considerations (Future)
- Right to delete
- Data export
- Consent management

### 12.4 WhatsApp Compliance

#### 24-Hour Window
```python
# Can only send template messages outside 24h window
# Can send free-form messages within 24h after last message

def is_within_24h_window(lead_uuid: str) -> bool:
    last_message = get_last_message_time(lead_uuid)
    return (datetime.now() - last_message).total_seconds() < 86400
```

#### STOP Handling
```python
# Handle "STOP" keyword in inbound messages
if message.lower() == "stop":
    mark_lead_as_opted_out(lead_uuid)
    send_confirmation_message(lead_uuid, "You've been unsubscribed.")
```

---

## 13. Deployment & Configuration

### 13.1 Render Deployment

#### Build Configuration
```yaml
# render.yaml
services:
  - type: web
    name: smart-presales
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: FLASK_ENV
        value: production
      - key: PORT
        fromService:
          type: web
          name: smart-presales
          property: port
```

#### Environment Variables (Render)
Set all variables from `.env` in Render dashboard:
```
Settings → Environment → Add Environment Variable
```

#### Service Account Setup
1. Download credentials JSON from Google Cloud
2. Upload to Render: **Secret Files** → Upload `config/credentials.json`
3. Update path in env vars

### 13.2 Local Development

#### Setup
```bash
# Clone repository
git clone <repo>

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp config/config.example.env .env
# Edit .env with your credentials

# Run app
python main.py
```

#### Ngrok (for local webhooks)
```bash
# Install ngrok
# Start ngrok
ngrok http 5000

# Copy URL to Vapi webhook settings
# https://xxx.ngrok.io/webhook/vapi
```

### 13.3 Database Setup

#### APScheduler Job Store
```python
# SQLite database created automatically
# Location: jobs.sqlite
# Table: apscheduler_jobs

# Jobs persist across restarts
```

### 13.4 Monitoring

#### Render Logs
```bash
# View logs in Render dashboard
# Settings → Logs
```

#### Log Levels
```python
# In production
LOG_LEVEL=INFO

# For debugging
LOG_LEVEL=DEBUG
```

---

## 14. Performance & Scalability

### 14.1 Caching Strategy

#### In-Memory Cache (Lead Data)
```python
_leads_cache = {
    "data": None,
    "ts": 0
}
_CACHE_TTL_SECONDS = 10  # 10 seconds
```

#### Cache Invalidation
```python
# After any data modification
_invalidate_leads_cache()
```

#### Force Refresh
```javascript
// Frontend can force refresh
fetch('/api/leads?refresh=true')
```

### 14.2 API Optimizations

#### Google Sheets
1. **Header Caching:** Cache headers, don't re-read every time
2. **Batched Updates:** Update multiple cells in single API call
3. **Column-Specific Reads:** Read only needed columns
4. **Exponential Backoff:** For 429 errors

#### Example: Batch Update
```python
# BEFORE: 3 API calls
update_cell(row, col_name, value1)
update_cell(row, col_name2, value2)
update_cell(row, col_name3, value3)

# AFTER: 1 API call
update_lead_fields(row_index, {
    "col_name": value1,
    "col_name2": value2,
    "col_name3": value3
})
```

### 14.3 Concurrent Call Management

#### Vapi Limits
```env
VAPI_CONCURRENT_LIMIT=5  # Max concurrent calls
```

#### Bulk Call Batching
```python
# Schedule bulk calls with batching
parallel_calls = 5        # 5 calls at once
batch_interval = 120     # 2 minutes between batches

# 50 leads → 10 batches → ~20 minutes total
```

#### Job Scheduling
```python
# Don't overload Vapi
for i, lead in enumerate(leads):
    schedule_time = base_time + (i // parallel_calls) * batch_interval
    scheduler.add_job(..., run_date=schedule_time)
```

### 14.4 Scalability Considerations

#### Current Limits (Google Sheets)
- **Max Leads:** ~10,000 (reasonable)
- **Concurrent Users:** ~10 (dashboard reads)
- **API Quota:** 600 req/min

#### Migration Path (Future)
When to migrate from Sheets to DB:
- **Triggers:**
  - >10,000 leads
  - >50 concurrent users
  - Frequent 429 errors
  - Need for transactions

**Migration Steps:**
1. Choose DB (PostgreSQL recommended)
2. Export data from Sheets
3. Import to DB
4. Update code to use SQLAlchemy instead of gspread
5. Deploy with both systems (duality)
6. Switch over gradually

---

## 15. Roadmap & Future Enhancements

### 15.1 Phase 4: Evaluation Framework

#### Test Cases
```python
# Create test dataset
test_leads = [
    {
        "name": "John Doe",
        "number": "+919876543210",
        "expected_status": "Qualified",
        "scenario": "Interested in USA, MIT, Fall 2025"
    },
    # ... more test cases
]

# Run automated tests
def test_call_flow(lead):
    result = workflow.invoke(lead)
    assert result["success_status"] == lead["expected_status"]
```

#### Metrics Tracking
- Success rate by scenario
- Average call duration
- Qualification accuracy
- Error frequency

### 15.2 Phase 5: Advanced Features

#### A/B Testing
```python
# Test different prompts
prompt_variant_a = "..."
prompt_variant_b = "..."

# Randomly assign leads to variant
variant = random.choice(["a", "b"])
assign_prompt(lead_uuid, variant)
```

#### Lead Scoring
```python
def calculate_lead_score(lead: dict) -> float:
    """
    Score 0-100 based on:
    - Call success
    - Response time
    - Engagement level
    - Budget alignment
    """
    score = 0
    if lead["success_status"] == "Qualified":
        score += 50
    # ... more factors
    return score
```

#### Agent Routing
```python
def route_lead_to_agent(lead_uuid: str):
    """
    Route high-value leads to experienced agents
    Route low-value leads to junior agents
    """
    score = calculate_lead_score(get_lead(lead_uuid))
    
    if score > 80:
        assign_to_agent(lead_uuid, "senior")
    else:
        assign_to_agent(lead_uuid, "junior")
```

### 15.3 WhatsApp AI Assistant

#### Two-Way Conversation
```python
async def handle_whatsapp_message(message: dict):
    """
    Continue qualification over WhatsApp chat
    """
    # Get conversation history
    history = get_conversation_history(message["from"])
    
    # Get lead data
    lead = get_lead_by_phone(message["from"])
    
    # Generate AI response
    response = ai_agent.chat(
        message=message["text"],
        context=lead,
        history=history
    )
    
    # Send response
    send_whatsapp_message(message["from"], response)
    
    # Store in conversation history
    save_conversation(lead_uuid, "whatsapp", response)
```

#### Context Awareness
```python
def build_context_for_ai(lead_uuid: str) -> dict:
    """
    Build rich context for AI
    """
    return {
        "lead": get_lead(lead_uuid),
        "call_history": get_call_history(lead_uuid),
        "conversation_history": get_conversation_history(lead_uuid),
        "call_analysis": get_latest_analysis(lead_uuid)
    }
```

### 15.4 Advanced Analytics

#### Funnel Tracking
```python
funnel = {
    "leads_uploaded": 1000,
    "calls_initiated": 800,    # 80%
    "calls_answered": 600,       # 60%
    "calls_completed": 500,    # 50%
    "qualified": 300,          # 30%
    "booked": 100              # 10%
}
```

#### Cohort Analysis
```python
cohorts = [
    {
        "date": "2025-01-01",
        "leads": 100,
        "qualified": 30,
        "qualified_rate": 0.30
    }
]
```

#### Performance by Partner
```python
partner_stats = {
    "Physics wallah": {
        "total_leads": 500,
        "qualified_rate": 0.35,
        "avg_call_duration": 120
    }
}
```

### 15.5 Knowledge Base Integration

#### RAG (Retrieval-Augmented Generation)
```python
def query_knowledge_base(query: str) -> str:
    """
    Query internal knowledge base
    """
    # Vector search
    results = vector_search(query, k=5)
    
    # Generate response using retrieved context
    response = llm.generate(
        query=query,
        context=results
    )
    
    return response
```

#### Use Cases
- University information
- Housing options
- Visa requirements
- Budget calculators

### 15.6 Multi-Language Support

#### Language Detection
```python
def detect_language(text: str) -> str:
    # Detect language
    # Return: "en", "hi", "es", etc.
    pass
```

#### Multi-Language Prompts
```python
prompts = {
    "en": "Hi, I'm Eshwari from Amber...",
    "hi": "नमस्ते, मैं एश्वरी हूं...",
    "es": "Hola, soy Eshwari de Amber..."
}
```

### 15.7 Integration Enhancements

#### CRM Integration
```python
# Sync with Salesforce
def sync_lead_to_crm(lead: dict):
    salesforce_client.create_lead(lead)
```

#### Webhook Extensions
```python
# Custom webhooks
@app.route('/webhook/custom', methods=['POST'])
def handle_custom_webhook(data):
    # Process external webhooks
    # Trigger custom workflows
    pass
```

---

## 16. Appendix

### 16.1 File Structure
```
/
├── src/
│   ├── app.py                  # Flask app + API endpoints
│   ├── scheduler.py            # APScheduler configuration
│   ├── sheets_manager.py       # Google Sheets operations
│   ├── vapi_client.py         # Vapi API client
│   ├── webhook_handler.py     # Webhook processing
│   ├── whatsapp_client.py     # WhatsApp API client
│   ├── email_client.py        # Email operations
│   ├── retry_manager.py        # Retry logic
│   ├── orchestrator.py        # Legacy orchestrator
│   ├── observability.py       # LangFuse integration
│   ├── utils.py               # Utilities (timezone, phone, names)
│   ├── version.py             # Version info
│   ├── workflows/
│   │   ├── __init__.py
│   │   └── lead_workflow.py   # LangGraph workflow
│   ├── templates/
│   │   └── index.html         # Dashboard UI
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── dashboard.js
├── config/
│   ├── config.example.env     # Environment variables template
│   └── credentials.json       # Google service account (gitignored)
├── main.py                     # Entry point
├── requirements.txt            # Python dependencies
├── Procfile                    # Render deployment config
├── render.yaml                 # Render build config
├── runtime.txt                # Python version
└── docs/
    └── PRD.md                  # This file
```

### 16.2 Environment Variables Reference

#### Required
```env
# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_FILE=config/credentials.json
LEADS_SHEET_ID=1xxx...

# Vapi
VAPI_API_KEY=sk-...
VAPI_ASSISTANT_ID=asst-...
VAPI_PHONE_NUMBER_ID=1ff83ff6-...
```

#### Optional (with defaults)
```env
MAX_RETRY_COUNT=3
RETRY_INTERVALS=1,4,24
RETRY_UNITS=hours
VAPI_CONCURRENT_LIMIT=5
USE_LANGGRAPH=true
ENABLE_OBSERVABILITY=true
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

#### WhatsApp (Phase 2)
```env
WHATSAPP_CLOUD_ACCESS_TOKEN=EAA...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_WABA_ID=...
```

### 16.3 API Rate Limits Reference

#### Google Sheets
- **Quota:** 600 requests/minute/project
- **Strategy:** Cache + batch operations

#### Vapi
- **Concurrent Calls:** Plan-dependent (5, 10, 20, etc.)
- **Strategy:** Batch scheduling, respect limit

#### WhatsApp Cloud API
- **Rate Limit:** Varies by tier
- **Strategy:** Queue messages, implement backoff

### 16.4 Troubleshooting Guide

#### Issue: Dashboard not updating
**Solution:**
1. Check cache: `?refresh=true`
2. Check logs for 429 errors
3. Wait for quota reset

#### Issue: SIP 403 Forbidden
**Solution:**
1. Check Vapi dashboard for credits
2. Verify phone number format
3. Check Vapi phone number configuration
4. Wait 15 minutes (carrier blocks)

#### Issue: Double `++` in phone numbers
**Solution:**
1. Fixed in v1.2.0
2. Upload CSV with proper format
3. System auto-sanitizes on upload

#### Issue: LangFuse not showing data
**Solution:**
1. Check API keys in Render
2. Verify `LANGFUSE_HOST` (US vs EU)
3. Check Render logs for auth errors

---

## 17. Changelog

### v2.0 (January 2025)
- ✅ Fixed immediate retry loop (Over Concurrency Limit)
- ✅ Added phone number sanitization
- ✅ Implemented IST timezone throughout
- ✅ Added bulk call scheduling with UI
- ✅ Enhanced observability (LangFuse)
- ✅ Added transcript storage and display
- ✅ Fixed 10 critical issues

### v1.0 (Initial Release)
- ✅ Basic call functionality
- ✅ Google Sheets integration
- ✅ Vapi integration
- ✅ Dashboard UI
- ✅ Retry mechanism
- ✅ Webhook handling

---

## 18. Support & Contact

For issues or questions:
- **Documentation:** This PRD and inline code comments
- **Logs:** Render dashboard → Logs
- **Monitoring:** LangFuse dashboard
- **Version Check:** `GET /api/version`

---

**END OF DOCUMENT**