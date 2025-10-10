"""
Background job scheduler using APScheduler.
Handles time-based triggers for call orchestration, email polling, and reconciliation.
"""

import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None


def create_scheduler():
    """
    Create and configure the APScheduler instance.
    
    Returns:
        BackgroundScheduler: Configured scheduler instance
    """
    jobstores = {
        'default': MemoryJobStore()
    }
    
    executors = {
        'default': ThreadPoolExecutor(max_workers=3)
    }
    
    job_defaults = {
        'coalesce': True,  # If multiple instances are due, only run one
        'max_instances': 1,  # Only one instance of each job at a time
        'misfire_grace_time': 30  # Allow 30s delay if previous job overruns
    }
    
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )
    
    # Add event listeners for logging
    scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)
    scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
    
    return scheduler


def job_executed_listener(event):
    """Log when a job completes successfully."""
    logger.info(f"Job {event.job_id} executed successfully")


def job_error_listener(event):
    """Log when a job fails."""
    logger.error(f"Job {event.job_id} failed with exception: {event.exception}")


def get_scheduler():
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    return _scheduler


# Job functions
def run_call_orchestrator_job():
    """
    Job function for call orchestration with LangGraph integration.
    Processes pending leads and initiates calls or retries using workflow.
    """
    try:
        from src.sheets_manager import SheetsManager
        from src.workflows import get_workflow
        
        logger.info("[Job] Starting LangGraph workflow orchestrator cycle")
        
        use_langgraph = os.getenv('USE_LANGGRAPH', 'true').lower() == 'true'
        
        if not use_langgraph:
            # Fallback to legacy orchestrator
            logger.info("[Job] Using legacy orchestrator (LangGraph disabled)")
            return run_legacy_call_orchestrator()
        
        # Get pending leads
        sheets_manager = SheetsManager(
            credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
            sheet_id=os.getenv('LEADS_SHEET_ID')
        )
        
        pending_leads = sheets_manager.get_pending_leads(only_retry=True)
        
        if not pending_leads:
            logger.info("[Job] No pending leads to process")
            return {"total_leads_processed": 0, "workflows_executed": 0, "errors": 0}
        
        logger.info(f"[Job] Processing {len(pending_leads)} leads with LangGraph workflow")
        
        # Get workflow
        workflow = get_workflow()
        
        workflows_executed = 0
        errors = 0
        
        for lead in pending_leads:
            try:
                lead_uuid = lead.get('lead_uuid')
                if not lead_uuid:
                    logger.warning(f"[Job] Skipping lead without UUID: {lead.get('name')}")
                    continue
                
                # Prepare initial state
                initial_state = {
                    "lead_uuid": lead_uuid,
                    "lead_name": lead.get('name', ''),
                    "lead_number": lead.get('number', ''),
                    "lead_email": lead.get('email', ''),
                    "whatsapp_number": lead.get('whatsapp_number') or lead.get('number', ''),
                    "call_status": lead.get('call_status', 'pending'),
                    "retry_count": int(lead.get('retry_count', 0)),
                    "max_retries": int(os.getenv('MAX_RETRY_COUNT', '3')),
                    "channels_tried": [],
                    "last_channel": "",
                    "conversation_history": [],
                    "qualification_status": "",
                    "structured_data": {},
                    "summary": "",
                    "next_action": "call"
                }
                
                # Execute workflow
                config = {"configurable": {"thread_id": lead_uuid}}
                result = workflow.invoke(initial_state, config)
                
                workflows_executed += 1
                logger.info(f"[Job] Workflow completed for lead {lead_uuid}: status={result.get('call_status')}")
                
            except Exception as e:
                logger.error(f"[Job] Workflow failed for lead {lead.get('lead_uuid', 'unknown')}: {e}")
                errors += 1
        
        logger.info(
            f"[Job] LangGraph orchestrator completed: "
            f"{len(pending_leads)} leads, "
            f"{workflows_executed} workflows executed, "
            f"{errors} errors"
        )
        
        return {
            "total_leads_processed": len(pending_leads),
            "workflows_executed": workflows_executed,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"[Job] LangGraph orchestrator failed: {e}", exc_info=True)
        raise


def run_legacy_call_orchestrator():
    """
    Legacy call orchestrator (pre-LangGraph).
    Used as fallback when USE_LANGGRAPH=false.
    """
    try:
        from src.sheets_manager import SheetsManager
        from src.vapi_client import VapiClient
        from src.retry_manager import RetryManager
        from src.call_orchestrator import CallOrchestrator
        
        logger.info("[Job] Starting legacy call orchestrator cycle")
        
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
        
        results = orchestrator.process_pending_leads(only_retry=True)
        
        logger.info(
            f"[Job] Legacy orchestrator completed: "
            f"{results['total_leads_processed']} leads, "
            f"{results['calls_initiated']} calls initiated, "
            f"{results['errors']} errors"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"[Job] Legacy orchestrator failed: {e}", exc_info=True)
        raise


def run_email_poller_job():
    """
    Job function for email polling.
    Polls IMAP inbox for new emails and processes them.
    """
    try:
        from src.email_inbound import poll_once
        from src.app import get_sheets_manager, get_email_client
        
        logger.info("[Job] Starting email poller cycle")
        
        sheets_manager = get_sheets_manager()
        email_client = get_email_client()
        auto_reply = os.getenv('AUTO_EMAIL_REPLY', 'false').lower() == 'true'
        
        # Placeholder AI reply function
        ai_reply_func = lambda lead_uuid, subject, body: None
        
        result = poll_once(
            sheets_manager,
            auto_reply=auto_reply,
            ai_reply_func=ai_reply_func,
            email_client=email_client
        )
        
        if result and result.get('processed'):
            logger.info(f"[Job] Email poller processed {result.get('processed')} messages")
        else:
            logger.debug("[Job] Email poller: No new messages")
        
        return result
        
    except Exception as e:
        logger.error(f"[Job] Email poller failed: {e}", exc_info=True)
        raise


def run_reconciliation_job():
    """
    Job function for reconciling 'initiated' calls with Vapi.
    Pulls latest status from Vapi API for calls stuck in 'initiated' state.
    """
    try:
        from src.sheets_manager import SheetsManager
        from src.vapi_client import VapiClient
        
        logger.info("[Job] Starting call reconciliation cycle")
        
        sheets_manager = SheetsManager(
            credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
            sheet_id=os.getenv('LEADS_SHEET_ID')
        )
        
        vapi_client = VapiClient(api_key=os.getenv('VAPI_API_KEY'))
        
        # Get all leads in 'initiated' state
        worksheet = sheets_manager.sheet.worksheet("Leads")
        all_leads = worksheet.get_all_records()
        
        initiated_leads = [
            (idx, lead) for idx, lead in enumerate(all_leads)
            if lead.get('call_status') == 'initiated' and lead.get('vapi_call_id')
        ]
        
        if not initiated_leads:
            logger.info("[Job] No initiated calls to reconcile")
            return {"reconciled": 0}
        
        reconciled = 0
        for row_idx, lead in initiated_leads:
            try:
                vapi_call_id = lead.get('vapi_call_id')
                # Fetch call details from Vapi
                call_details = vapi_client.get_call_details(vapi_call_id)
                
                if call_details and 'status' in call_details:
                    actual_status = call_details['status']
                    
                    # Map Vapi status to our status
                    if actual_status in ['completed', 'ended']:
                        new_status = 'completed'
                    elif actual_status in ['failed', 'busy', 'no-answer']:
                        new_status = 'missed'
                    else:
                        continue  # Still in progress, skip
                    
                    # Update the lead status
                    sheets_manager.update_lead_fields(row_idx, {'call_status': new_status})
                    logger.info(f"[Job] Reconciled lead {lead.get('lead_uuid', row_idx)}: initiated → {new_status}")
                    reconciled += 1
                    
            except Exception as e:
                logger.warning(f"[Job] Failed to reconcile lead {row_idx}: {e}")
                continue
        
        logger.info(f"[Job] Reconciliation completed: {reconciled} calls updated")
        return {"reconciled": reconciled}
        
    except Exception as e:
        logger.error(f"[Job] Reconciliation job failed: {e}", exc_info=True)
        raise


def start_background_jobs(scheduler=None):
    """
    Schedule all background jobs.
    
    Args:
        scheduler: APScheduler instance (creates one if None)
    """
    if scheduler is None:
        scheduler = get_scheduler()
    
    # Job 1: Call Orchestrator (processes pending leads and retries)
    orchestrator_interval = int(os.getenv('ORCHESTRATOR_INTERVAL_SECONDS', '60'))
    scheduler.add_job(
        func=run_call_orchestrator_job,
        trigger='interval',
        seconds=orchestrator_interval,
        id='call_orchestrator',
        name='Call Orchestration Job',
        replace_existing=True,
        next_run_time=datetime.now()  # Run immediately on startup
    )
    logger.info(f"✅ Scheduled call orchestrator (every {orchestrator_interval}s)")
    
    # Job 2: Email Poller (if IMAP is configured)
    if os.getenv('IMAP_HOST') and os.getenv('IMAP_USER'):
        poll_interval = int(os.getenv('IMAP_POLL_SECONDS', '60'))
        scheduler.add_job(
            func=run_email_poller_job,
            trigger='interval',
            seconds=poll_interval,
            id='email_poller',
            name='Email Polling Job',
            replace_existing=True
        )
        logger.info(f"✅ Scheduled email poller (every {poll_interval}s)")
    else:
        logger.info("⏭️  Email poller not configured (IMAP settings missing)")
    
    # Job 3: Reconciliation (fixes stuck 'initiated' calls)
    reconciliation_interval = int(os.getenv('RECONCILIATION_INTERVAL_SECONDS', '300'))  # 5 min default
    scheduler.add_job(
        func=run_reconciliation_job,
        trigger='interval',
        seconds=reconciliation_interval,
        id='call_reconciliation',
        name='Call Reconciliation Job',
        replace_existing=True
    )
    logger.info(f"✅ Scheduled call reconciliation (every {reconciliation_interval}s)")
    
    # Start the scheduler
    if not scheduler.running:
        scheduler.start()
        logger.info("🚀 Background scheduler started successfully")
    
    return scheduler


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        logger.info("Shutting down scheduler...")
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down successfully")

