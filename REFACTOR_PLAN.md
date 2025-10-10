# 🚀 Smart Presales Refactoring Plan

## Overview
Systematic refactoring to achieve:
1. **Clean codebase** (remove redundant files)
2. **Standard orchestration** (APScheduler pattern)
3. **Full observability** (LangSmith/LangFuse)
4. **Evaluation framework** (test cases + metrics)
5. **Continuous improvement** (iterate on voice bot)

---

## PHASE 1: CLEANUP (Est: 30 minutes)

### Files to DELETE ❌
```bash
rm add_test_leads.py          # Dashboard has bulk CSV upload
rm check_sheet_data.py         # Dashboard shows all leads
rm verify_sheet.py             # Redundant with src/init_sheet.py
rm initialize_sheet.py         # DUPLICATE of src/init_sheet.py
rm test_flow.py                # Superseded by test_vapi_final.py
```

### Files to KEEP ✅
- `src/init_sheet.py` - First-time setup script
- `setup.py` - Dev environment setup (useful for onboarding)
- `test_vapi_final.py` - Comprehensive test script
- `test_webhook.py` - If it tests unique webhook scenarios; else delete
- `startup.py` - Render-specific credential setup

### Optional: Reorganize Test Scripts
```bash
mkdir tests/
mv test_vapi_final.py tests/
mv test_webhook.py tests/  # if keeping
```

---

## PHASE 2: STANDARDIZE ORCHESTRATION (Est: 2 hours)

### Current Problems
- ❌ Daemon threads (no persistence, no visibility)
- ❌ No retry logic for orchestrator failures
- ❌ Hard to test background jobs
- ❌ Can't scale horizontally

### Solution: APScheduler (Already in requirements!)

#### Step 1: Create `src/scheduler.py`
```python
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from src.call_orchestrator import CallOrchestrator
from src.sheets_manager import SheetsManager
from src.vapi_client import VapiClient
from src.retry_manager import RetryManager
from src.email_inbound import poll_once
from src.app import get_sheets_manager, get_email_client

logger = logging.getLogger(__name__)

def run_call_orchestrator():
    """Job function for call orchestration."""
    try:
        sheets_manager = SheetsManager(
            credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
            sheet_id=os.getenv('LEADS_SHEET_ID')
        )
        vapi_client = VapiClient(api_key=os.getenv('VAPI_API_KEY'))
        retry_intervals = [float(x) for x in os.getenv('RETRY_INTERVALS', '0.5,24').split(',')]
        retry_manager = RetryManager(
            max_retries=int(os.getenv('MAX_RETRY_COUNT', '3')),
            retry_intervals=retry_intervals,
            interval_unit=os.getenv('RETRY_UNITS', 'hours')
        )
        
        orchestrator = CallOrchestrator(
            sheets_manager=sheets_manager,
            vapi_client=vapi_client,
            retry_manager=retry_manager,
            assistant_id=os.getenv('VAPI_ASSISTANT_ID'),
            phone_number_id=os.getenv('VAPI_PHONE_NUMBER_ID')
        )
        
        results = orchestrator.run_once()
        logger.info(f"Orchestrator cycle completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Orchestrator job failed: {e}", exc_info=True)
        # APScheduler will retry on next interval
        raise

def run_email_poller():
    """Job function for email polling."""
    try:
        sm = get_sheets_manager()
        ec = get_email_client()
        auto_reply = os.getenv('AUTO_EMAIL_REPLY', 'false').lower() == 'true'
        ai_func = (lambda lead_uuid, subject, body: None)  # Placeholder for now
        
        res = poll_once(sm, auto_reply=auto_reply, ai_reply_func=ai_func, email_client=ec)
        if res and res.get('processed'):
            logger.info(f"Email poller processed {res.get('processed')} messages")
        return res
    except Exception as e:
        logger.error(f"Email poller job failed: {e}", exc_info=True)
        raise

def create_scheduler():
    """Create and configure the APScheduler instance."""
    jobstores = {'default': MemoryJobStore()}
    executors = {
        'default': ThreadPoolExecutor(max_workers=3)
    }
    job_defaults = {
        'coalesce': True,  # Only run one instance at a time
        'max_instances': 1,
        'misfire_grace_time': 30  # Allow 30s delay if previous job overruns
    }
    
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults
    )
    return scheduler

def start_background_jobs(scheduler):
    """Schedule all background jobs."""
    # Call orchestrator
    interval_seconds = int(os.getenv('ORCHESTRATOR_INTERVAL_SECONDS', '60'))
    scheduler.add_job(
        func=run_call_orchestrator,
        trigger='interval',
        seconds=interval_seconds,
        id='call_orchestrator',
        name='Call Orchestration Job',
        replace_existing=True
    )
    logger.info(f"Scheduled call orchestrator (every {interval_seconds}s)")
    
    # Email poller (if configured)
    if os.getenv('IMAP_HOST') and os.getenv('IMAP_USER'):
        poll_seconds = int(os.getenv('IMAP_POLL_SECONDS', '60'))
        scheduler.add_job(
            func=run_email_poller,
            trigger='interval',
            seconds=poll_seconds,
            id='email_poller',
            name='Email Polling Job',
            replace_existing=True
        )
        logger.info(f"Scheduled email poller (every {poll_seconds}s)")
    
    scheduler.start()
    logger.info("Background scheduler started successfully")
```

#### Step 2: Update `main.py`
```python
# Replace threading code with:
from src.scheduler import create_scheduler, start_background_jobs

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    
    try:
        from startup import setup_credentials
        setup_credentials()
    except Exception as e:
        logger.error(f"Failed to set up credentials: {e}")
    
    # Start APScheduler
    scheduler = create_scheduler()
    start_background_jobs(scheduler)
    
    # Register shutdown handler
    import atexit
    atexit.register(lambda: scheduler.shutdown())
    
    # Start Flask
    port = int(os.getenv('PORT', '5001'))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    logger.info(f"Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=False)
    # Note: use_reloader=False to avoid duplicate scheduler instances
```

#### Step 3: Add Job Status API (Optional but Recommended)
```python
# In src/app.py
@app.route('/api/jobs', methods=['GET'])
def get_job_status():
    """Get status of background jobs."""
    from src.scheduler import scheduler  # Import the global instance
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    return jsonify({"jobs": jobs})
```

---

## PHASE 3: ADD OBSERVABILITY (Est: 3 hours)

### Tool Choice: LangSmith vs LangFuse

| Feature | LangSmith | LangFuse |
|---------|-----------|----------|
| **Pricing** | Free tier: 5K traces/month | Open-source + cloud free tier |
| **Vapi Integration** | Manual instrumentation | Manual instrumentation |
| **LLM Support** | All (via LangChain) | All (provider-agnostic) |
| **Self-hosted** | No | Yes (Docker) |
| **Evals** | Built-in | Built-in |
| **Best for** | LangChain users | Non-LangChain, OSS fans |

**Recommendation**: **LangFuse** (open-source, flexible, easier to self-host if needed)

### Step 1: Install LangFuse
```bash
pip install langfuse
# Add to requirements.txt
```

### Step 2: Create `src/observability.py`
```python
import os
from langfuse import Langfuse
from functools import wraps
import json

# Initialize LangFuse client
langfuse = Langfuse(
    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
    host=os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')  # or self-hosted
)

def trace_vapi_call(func):
    """Decorator to trace Vapi call initiation."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract lead data from args/kwargs
        lead_data = kwargs.get('lead_data') or (args[1] if len(args) > 1 else {})
        lead_uuid = lead_data.get('lead_uuid', 'unknown')
        
        # Create trace
        trace = langfuse.trace(
            name="vapi_outbound_call",
            user_id=lead_uuid,
            metadata={
                "lead_name": lead_data.get('name'),
                "lead_phone": lead_data.get('number'),
                "assistant_id": kwargs.get('assistant_id') or (args[2] if len(args) > 2 else None)
            }
        )
        
        try:
            result = func(*args, **kwargs)
            
            # Log success
            trace.update(
                output=result,
                status_message="Call initiated successfully"
            )
            
            return result
        except Exception as e:
            # Log error
            trace.update(
                output={"error": str(e)},
                status_message=f"Call initiation failed: {str(e)}"
            )
            raise
        finally:
            langfuse.flush()  # Ensure data is sent
    
    return wrapper

def trace_webhook_event(event_type: str, lead_uuid: str, event_data: dict):
    """Trace webhook events (status updates, end-of-call reports)."""
    span = langfuse.span(
        name=f"webhook_{event_type}",
        trace_id=lead_uuid,  # Group by lead
        input=event_data,
        metadata={"event_type": event_type}
    )
    return span

def log_call_analysis(lead_uuid: str, summary: str, success_status: str, structured_data: dict):
    """Log AI analysis results."""
    langfuse.generation(
        name="call_analysis",
        trace_id=lead_uuid,
        model="vapi_assistant",  # Placeholder; Vapi doesn't expose underlying model
        input={"call_id": lead_uuid},
        output={
            "summary": summary,
            "success_status": success_status,
            "structured_data": structured_data
        },
        metadata={"analysis_type": "post_call"}
    )
    langfuse.flush()
```

### Step 3: Instrument `vapi_client.py`
```python
# In src/vapi_client.py
from src.observability import trace_vapi_call

class VapiClient:
    # ... existing code ...
    
    @trace_vapi_call  # Add decorator
    def initiate_outbound_call(self, lead_data, assistant_id, phone_number_id):
        # ... existing implementation ...
```

### Step 4: Instrument `webhook_handler.py`
```python
# In src/webhook_handler.py
from src.observability import trace_webhook_event, log_call_analysis

class WebhookHandler:
    def handle_event(self, event_data):
        message_type = event_data.get("message", {}).get("type")
        lead_uuid = ...  # extract lead_uuid as before
        
        # Trace the event
        span = trace_webhook_event(message_type, lead_uuid, event_data)
        
        try:
            # ... existing event handling ...
            
            # If end-of-call-report, log analysis
            if message_type == "end-of-call-report":
                analysis = message.get("analysis", {})
                log_call_analysis(
                    lead_uuid=lead_uuid,
                    summary=analysis.get("summary", ""),
                    success_status=analysis.get("successEvaluation", ""),
                    structured_data=analysis.get("structuredData", {})
                )
            
            span.end(output={"status": "success"})
        except Exception as e:
            span.end(output={"error": str(e)})
            raise
```

### Step 5: Add LangFuse Keys to `.env`
```bash
# LangFuse Observability
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com  # or your self-hosted URL
```

### Step 6: View Traces in LangFuse Dashboard
1. Sign up at https://cloud.langfuse.com (or self-host via Docker)
2. Create a project
3. Copy public/secret keys
4. Run your app and make test calls
5. View traces in LangFuse dashboard → see full call flow, timing, errors

---

## PHASE 4: EVALUATION FRAMEWORK (Est: 4 hours)

### Goal: Measure Voice Bot Quality

#### Key Metrics to Track:
1. **Call Success Rate**: % of calls that reach "completed" vs "missed"/"failed"
2. **Qualification Accuracy**: Does bot correctly identify qualified vs unqualified leads?
3. **Data Extraction Accuracy**: Are structured data fields (country, budget, timeline) filled correctly?
4. **Conversation Quality**: Natural, no repetitions, handles edge cases
5. **User Satisfaction**: Implicit (call duration, completion) + explicit (if you add post-call surveys)

### Step 1: Create Test Dataset
```python
# tests/eval_dataset.py
EVAL_CASES = [
    {
        "id": "qualified_uk_mba",
        "scenario": "Student planning MBA in UK, budget 500-800 GBP/month, needs housing in London",
        "expected_qualification": "qualified",
        "expected_data": {
            "country": "UK",
            "city": "London",
            "course": "MBA",
            "budget_min": 500,
            "budget_max": 800,
            "timeline": "next_3_months"
        }
    },
    {
        "id": "unqualified_not_student",
        "scenario": "Person looking for short-term rental, not a student",
        "expected_qualification": "unqualified",
        "expected_data": None
    },
    {
        "id": "edge_case_undecided",
        "scenario": "Student interested but hasn't decided on country yet",
        "expected_qualification": "needs_followup",
        "expected_data": {
            "countries_considering": ["UK", "USA", "Canada"],
            "timeline": "6_12_months"
        }
    },
    # Add 20-50 more cases covering:
    # - Different countries (USA, Canada, Australia, Germany, etc.)
    # - Budget ranges (low, medium, high)
    # - Timeline variations (urgent, 3 months, 6 months, next year)
    # - Edge cases (language barriers, call drops, unclear responses)
]
```

### Step 2: Create Eval Runner
```python
# tests/run_evals.py
import json
from langfuse import Langfuse
from tests.eval_dataset import EVAL_CASES

langfuse = Langfuse(...)

def run_evaluation():
    """Run evaluation on test dataset."""
    results = []
    
    for case in EVAL_CASES:
        # Option A: Simulate call (mock Vapi response)
        # Option B: Make real test calls to Vapi with test phone numbers
        
        # For now, let's assume you have call results stored in LangFuse/Sheets
        # Fetch the actual call result
        actual_result = fetch_call_result(case["id"])
        
        # Compare expected vs actual
        score = evaluate_case(case, actual_result)
        
        results.append({
            "case_id": case["id"],
            "expected": case["expected_qualification"],
            "actual": actual_result.get("qualification"),
            "score": score,
            "details": actual_result
        })
        
        # Log to LangFuse
        langfuse.score(
            trace_id=case["id"],
            name="qualification_accuracy",
            value=score
        )
    
    # Generate report
    avg_score = sum(r["score"] for r in results) / len(results)
    print(f"Evaluation complete: {avg_score:.2%} accuracy")
    
    return results

def evaluate_case(expected, actual):
    """Score a single test case."""
    # Simple scoring logic
    if actual.get("qualification") == expected["expected_qualification"]:
        return 1.0
    elif actual.get("qualification") in ["needs_followup", "unclear"]:
        return 0.5  # Partial credit
    else:
        return 0.0

if __name__ == "__main__":
    run_evaluation()
```

### Step 3: Integrate Evals into LangFuse
LangFuse supports:
- **Human-in-the-loop labeling**: Listen to call recordings, rate quality 1-5
- **Automated scoring**: Compare structured data extraction vs ground truth
- **A/B testing**: Compare two assistant configs side-by-side

---

## PHASE 5: CONTINUOUS IMPROVEMENT (Ongoing)

### Iteration Loop:
1. **Run evals** → Get baseline score (e.g., 72% qualification accuracy)
2. **Analyze failures** → Which edge cases fail? (e.g., bot doesn't handle "I'm still deciding")
3. **Update Vapi assistant prompt** → Add handling for "undecided" scenario
4. **Re-run evals** → New score: 78% ✅
5. **Deploy to prod** → Monitor via LangFuse
6. **Repeat weekly**

### Example Prompt Improvements:
- **Before**: "What country are you planning to study in?"
- **After**: "What country are you planning to study in? If you're considering multiple, feel free to mention them all."

- **Before**: Bot repeats question if user is unclear
- **After**: "I understand you're still deciding. Let me help narrow it down. Are you leaning more towards Europe or North America?"

---

## TIMELINE

| Phase | Estimated Time | Priority |
|-------|---------------|----------|
| **Cleanup** | 30 min | High |
| **APScheduler** | 2 hours | High |
| **LangFuse Setup** | 3 hours | Medium |
| **Eval Framework** | 4 hours | Medium |
| **First Iteration** | Ongoing | High |

**Total initial investment**: ~10 hours
**Long-term ROI**: 10x better bot quality, faster debugging, measurable improvements

---

## NEXT STEPS

1. ✅ **Approve this plan** (or suggest changes)
2. 🧹 **Phase 1: Cleanup** (I'll delete files and commit)
3. 🏗️ **Phase 2: APScheduler** (I'll refactor orchestration)
4. 📊 **Phase 3: LangFuse** (I'll add instrumentation)
5. 🧪 **Phase 4: Evals** (We'll build test cases together based on real use cases)
6. 🔄 **Phase 5: Iterate** (Run weekly eval cycles)

Let me know if you want me to proceed with Phase 1 cleanup now! 🚀

