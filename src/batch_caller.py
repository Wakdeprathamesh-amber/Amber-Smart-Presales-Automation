"""
Batch Call Worker for Smart Presales Automation

Handles background batch calling with automatic pacing and progress tracking.
"""

import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from src.utils import get_ist_timestamp, get_ist_now

logger = logging.getLogger(__name__)


class BatchCallJob:
    """Represents a batch calling job with progress tracking."""
    
    def __init__(self, job_id: str, total_leads: int, parallel_calls: int, interval_seconds: int):
        self.job_id = job_id
        self.total_leads = total_leads
        self.parallel_calls = parallel_calls
        self.interval_seconds = interval_seconds
        self.status = "running"  # running, completed, failed, cancelled
        self.current_batch = 0
        self.calls_initiated = 0
        self.calls_successful = 0
        self.calls_failed = 0
        self.errors = []
        self.started_at = get_ist_timestamp()
        self.completed_at = None
        self.next_batch_at = None
        self.current_batch_leads = []
        self._lock = threading.Lock()  # Protect state updates
        
    def to_dict(self) -> Dict:
        """Convert job to dictionary for API response (thread-safe)."""
        with self._lock:
            total_batches = (self.total_leads + self.parallel_calls - 1) // self.parallel_calls
            progress_percent = int((self.calls_initiated / self.total_leads) * 100) if self.total_leads > 0 else 0
            
            return {
                "job_id": self.job_id,
                "status": self.status,
                "total_leads": self.total_leads,
                "current_batch": self.current_batch,
                "total_batches": total_batches,
                "calls_initiated": self.calls_initiated,
                "calls_successful": self.calls_successful,
                "calls_failed": self.calls_failed,
                "progress_percent": progress_percent,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "next_batch_at": self.next_batch_at,
                "current_batch_leads": list(self.current_batch_leads),  # Copy list
                "errors": self.errors[-10:] if self.errors else []  # Copy last 10 errors
            }


class BatchCallWorker:
    """
    Manages background batch calling with automatic pacing.
    
    Features:
    - Processes leads in parallel batches
    - Automatic interval between batches
    - Progress tracking
    - Error handling and recovery
    """
    
    def __init__(self):
        self.jobs: Dict[str, BatchCallJob] = {}
        self.active_job_id: Optional[str] = None
        self._lock = threading.Lock()
        
    def start_job(
        self,
        job_id: str,
        leads: List[Dict],
        vapi_client,
        sheets_manager,
        assistant_id: str,
        phone_number_id: str,
        parallel_calls: int = 5,
        interval_seconds: int = 240
    ) -> BatchCallJob:
        """
        Start a new batch calling job.
        
        Args:
            job_id: Unique identifier for the job
            leads: List of lead dictionaries with row_index_0 and lead data
            vapi_client: VapiClient instance
            sheets_manager: SheetsManager instance
            assistant_id: Vapi assistant ID
            phone_number_id: Vapi phone number ID
            parallel_calls: Number of calls to make in parallel (default: 5)
            interval_seconds: Seconds to wait between batches (default: 240 = 4 minutes)
            
        Returns:
            BatchCallJob: The created job instance
        """
        old_job = None
        with self._lock:
            # Cancel existing job if any
            if self.active_job_id and self.active_job_id in self.jobs:
                old_job = self.jobs[self.active_job_id]
        
        # Cancel old job outside worker lock but with job lock
        if old_job:
            with old_job._lock:
                if old_job.status == "running":
                    old_job.status = "cancelled"
                    logger.info(f"Cancelled previous job {self.active_job_id}")
        
        with self._lock:
            
            # Create new job
            job = BatchCallJob(job_id, len(leads), parallel_calls, interval_seconds)
            self.jobs[job_id] = job
            self.active_job_id = job_id
            
        # Start worker thread
        thread = threading.Thread(
            target=self._worker,
            args=(job, leads, vapi_client, sheets_manager, assistant_id, phone_number_id),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Started batch call job {job_id} with {len(leads)} leads, "
                   f"{parallel_calls} parallel, {interval_seconds}s interval")
        
        return job
    
    def get_job(self, job_id: str) -> Optional[BatchCallJob]:
        """Get job by ID."""
        with self._lock:
            return self.jobs.get(job_id)
    
    def get_active_job(self) -> Optional[BatchCallJob]:
        """Get currently active job."""
        with self._lock:
            if self.active_job_id:
                return self.jobs.get(self.active_job_id)
        return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        with self._lock:
            job = self.jobs.get(job_id)
        
        if job:
            with job._lock:
                if job.status == "running":
                    job.status = "cancelled"
                    logger.info(f"Cancelled job {job_id}")
                    return True
        return False
    
    def _update_sheet_with_retry(self, sheets_manager, row_index: int, fields: dict):
        """
        Update sheet with exponential backoff retry logic.
        Handles transient errors and rate limits.
        """
        max_attempts = 3
        backoff = 1
        attempt = 0
        while True:
            try:
                sheets_manager.update_lead_fields(row_index, fields)
                return
            except Exception as e:
                attempt += 1
                if attempt >= max_attempts:
                    logger.error(f"Sheet update failed after {attempt} attempts: {e}")
                    raise
                sleep_time = backoff * (2 ** (attempt - 1))
                logger.warning(f"Sheet update transient error (attempt {attempt}/{max_attempts}): {e}. Retrying in {sleep_time}s")
                time.sleep(sleep_time)
    
    def _call_single_lead(self, job, lead_data, vapi_client, sheets_manager, assistant_id, phone_number_id):
        """
        Execute a single call in a separate thread (parallel execution).
        This matches the proven threading pattern from scheduled calls.
        """
        try:
            row_index_0 = lead_data.get('row_index_0')
            lead = lead_data.get('lead')
            lead_uuid = lead.get('lead_uuid')
            number = lead.get('number')
            
            if not lead_uuid or not number:
                with job._lock:
                    job.calls_failed += 1
                    job.calls_initiated += 1
                    job.errors.append({
                        "lead_uuid": lead_uuid or "unknown",
                        "error": "Missing UUID or number"
                    })
                return
            
            # Initiate call via Vapi
            call_time = get_ist_timestamp()
            result = vapi_client.initiate_outbound_call(
                lead_data={
                    "lead_uuid": lead_uuid,
                    "number": number,
                    "name": lead.get('name'),
                    "email": lead.get('email'),
                    "partner": lead.get('partner')
                },
                assistant_id=assistant_id,
                phone_number_id=phone_number_id
            )
            
            # Check result
            if "error" in result:
                with job._lock:
                    job.calls_failed += 1
                    job.calls_initiated += 1
                    job.errors.append({
                        "lead_uuid": lead_uuid,
                        "error": result["error"]
                    })
                logger.warning(f"Call failed for {lead_uuid}: {result['error']}")
            else:
                # Get current retry count and increment
                current_retry_count = int(lead.get('retry_count', 0) or 0)
                
                # Update sheet with call initiated status and incremented retry count
                # Use retry logic to handle transient errors
                try:
                    self._update_sheet_with_retry(
                        sheets_manager,
                        row_index_0,
                        {
                            "call_status": "initiated",
                            "last_call_time": call_time,
                            "vapi_call_id": result.get('id', ''),
                            "retry_count": str(current_retry_count + 1)
                        }
                    )
                    with job._lock:
                        job.calls_successful += 1
                        job.calls_initiated += 1
                    logger.info(f"Call initiated for {lead_uuid}: {result.get('id')}")
                except Exception as sheet_error:
                    # If sheet update fails after retries, log but don't fail the call
                    logger.error(f"Sheet update failed for {lead_uuid} after retries: {sheet_error}")
                    with job._lock:
                        job.calls_successful += 1  # Call still succeeded
                        job.calls_initiated += 1
                        job.errors.append({
                            "lead_uuid": lead_uuid,
                            "error": f"Sheet update failed: {str(sheet_error)}"
                        })
        
        except Exception as e:
            with job._lock:
                job.calls_failed += 1
                job.calls_initiated += 1
                job.errors.append({
                    "lead_uuid": lead.get('lead_uuid', 'unknown'),
                    "error": str(e)
                })
            logger.error(f"Error processing lead: {e}", exc_info=True)
    
    def _worker(
        self,
        job: BatchCallJob,
        leads: List[Dict],
        vapi_client,
        sheets_manager,
        assistant_id: str,
        phone_number_id: str
    ):
        """
        Background worker that processes leads in batches.
        
        This runs in a separate thread and processes leads with automatic pacing.
        """
        try:
            logger.info(f"Worker started for job {job.job_id}")
            
            # Process leads in batches
            for i in range(0, len(leads), job.parallel_calls):
                # Check if job was cancelled
                with job._lock:
                    is_cancelled = job.status == "cancelled"
                if is_cancelled:
                    logger.info(f"Job {job.job_id} cancelled by user")
                    break
                
                # Get next batch
                batch = leads[i:i + job.parallel_calls]
                with job._lock:
                    job.current_batch = (i // job.parallel_calls) + 1
                    job.current_batch_leads = [item.get('lead', {}).get('name', 'Unknown') for item in batch]
                
                logger.info(f"Job {job.job_id}: Processing batch {job.current_batch}, "
                           f"leads {i+1}-{min(i+len(batch), len(leads))}")
                
                # Process each lead in the batch using threading (like scheduled calls)
                # This approach is proven to work reliably without SIP errors
                threads = []
                for lead_data in batch:
                    with job._lock:
                        is_cancelled = job.status == "cancelled"
                    if is_cancelled:
                        break
                    
                    # Start each call in a separate thread for true parallelism
                    thread = threading.Thread(
                        target=self._call_single_lead,
                        args=(job, lead_data, vapi_client, sheets_manager, assistant_id, phone_number_id)
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
                
                # Wait for all threads in this batch to complete (with timeout)
                for thread in threads:
                    thread.join(timeout=30)  # 30 second timeout per call initiation
                
                logger.info(f"✅ Job {job.job_id}: Batch {job.current_batch} complete")
                
                # Wait before next batch (unless this is the last batch)
                with job._lock:
                    is_cancelled = job.status == "cancelled"
                if i + job.parallel_calls < len(leads) and not is_cancelled:
                    from datetime import timedelta
                    next_time = get_ist_now() + timedelta(seconds=job.interval_seconds)
                    with job._lock:
                        job.next_batch_at = next_time.isoformat()
                    
                    logger.info(f"Job {job.job_id}: Waiting {job.interval_seconds}s before next batch")
                    time.sleep(job.interval_seconds)
            
            # Mark job as completed
            with job._lock:
                is_cancelled = job.status == "cancelled"
            if not is_cancelled:
                with job._lock:
                    job.status = "completed"
                    job.completed_at = get_ist_timestamp()
                logger.info(f"Job {job.job_id} completed: {job.calls_successful} successful, "
                           f"{job.calls_failed} failed out of {job.total_leads} total")
            
        except Exception as e:
            with job._lock:
                job.status = "failed"
                job.completed_at = get_ist_timestamp()
            logger.error(f"Job {job.job_id} failed with error: {e}", exc_info=True)
        
        finally:
            # Clear active job reference if this was the active job
            with self._lock:
                if self.active_job_id == job.job_id:
                    self.active_job_id = None


# Global singleton instance
_batch_worker = None

def get_batch_worker() -> BatchCallWorker:
    """Get or create the global batch call worker instance."""
    global _batch_worker
    if _batch_worker is None:
        _batch_worker = BatchCallWorker()
    return _batch_worker

