import json
import time
from datetime import datetime
from src.sheets_manager import SheetsManager
from src.retry_manager import RetryManager

class WebhookHandler:
    def __init__(self, sheets_manager, retry_manager):
        """
        Initialize the webhook handler.
        
        Args:
            sheets_manager (SheetsManager): Instance of SheetsManager
            retry_manager (RetryManager): Instance of RetryManager
        """
        self.sheets_manager = sheets_manager
        self.retry_manager = retry_manager
        # Cache to reduce repeated sheet reads when resolving rows by lead_uuid
        self._row_cache = {}

    def _with_retry(self, func, *args, **kwargs):
        """Execute a sheets update with exponential backoff to handle 429s/transient errors."""
        max_attempts = 4
        backoff = 0.5
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempt += 1
                if attempt >= max_attempts:
                    print(f"Operation failed after {attempt} attempts: {e}")
                    raise
                sleep_time = backoff * (2 ** (attempt - 1))
                print(f"Transient error on sheets operation: {e}. Retrying in {sleep_time:.2f}s (attempt {attempt}/{max_attempts})")
                time.sleep(sleep_time)
    
    def handle_event(self, event_data):
        """
        Handle a Vapi webhook event.
        
        Args:
            event_data (dict): Event data from Vapi webhook
            
        Returns:
            dict: Result of handling the event
        """
        message_type = event_data.get("message", {}).get("type")
        print(f"Handling webhook event type: {message_type}")
        print(f"Full event data: {json.dumps(event_data, indent=2)[:500]}...")
        
        message = event_data.get("message", {})
        
        # Get the lead ID from metadata
        try:
            # Prefer top-level call metadata (matches real Vapi payloads)
            call_metadata = event_data.get("call", {}).get("metadata", {})
            # Fallback to message.call.metadata (used by our test script)
            if not call_metadata:
                call_metadata = message.get("call", {}).get("metadata", {})
            print(f"Call metadata: {call_metadata}")
            lead_uuid = call_metadata.get("lead_uuid")
            lead_id = call_metadata.get("lead_id")
            print(f"Extracted lead_id: {lead_id}")
            
            if not lead_uuid and not lead_id:
                print("No lead_uuid/lead_id found in webhook data")
                return {"error": "No lead_uuid/lead_id found in webhook data"}
            
            # Resolve row by lead_uuid if available; fallback to integer lead_id for legacy/tests
            lead_row = None
            if lead_uuid:
                # Use cache first
                if lead_uuid in self._row_cache:
                    lead_row = self._row_cache[lead_uuid]
                else:
                    # Resolve from sheet and cache
                    try:
                        row_index_0 = self.sheets_manager.find_row_by_lead_uuid(lead_uuid)
                    except Exception:
                        row_index_0 = None
                    if row_index_0 is not None:
                        lead_row = row_index_0
                        self._row_cache[lead_uuid] = lead_row
            if lead_row is None and lead_id is not None:
                try:
                    lead_row = int(lead_id)
                    print(f"Using lead_row as integer: {lead_row}")
                except ValueError:
                    if lead_id == "test-001":
                        lead_row = 0
                    else:
                        print(f"Could not resolve lead by id: {lead_id}")
                        return {"error": f"Invalid lead reference"}
        except Exception as e:
            print(f"Error extracting lead_id: {e}")
            lead_row = None
        
        if lead_row is None:
            return {"error": f"Could not determine lead row from ID: {lead_id}"}
        
        # Process different event types
        if message_type == "status-update":
            status = message.get("status")
            ended_reason = message.get("endedReason", "")
            # Try to infer if the call was ever answered/connected
            call_info = event_data.get("call", {}) or message.get("call", {})
            answered_at = (call_info or {}).get("answeredAt") or (call_info or {}).get("connectedAt")
            
            print(f"Call status update: {status}, Reason: {ended_reason}")
            
            # Treat explicit answered immediately
            if status == "answered":
                self._with_retry(self.sheets_manager.update_lead_status, lead_row, "answered")
                return {"status": "success", "action": "call_status_updated", "new_status": "answered"}

            # Handle missed/failed explicitly
            if status in ("missed", "failed"):
                return self._handle_missed_call(lead_row, event_data)

            # On ended, decide based on reason
            if status == "ended":
                reason = (ended_reason or "").lower()
                # Consider substrings and common SIP indicators
                missed_keywords = [
                    "no-answer", "noanswer", "rejected", "busy", "timeout", "cancelled", "canceled",
                    "unavailable", "486", "487", "480"
                ]
                failed_keywords = [
                    "failed", "error", "providerfault", "server-error", "503", "500"
                ]
                # If the call was never answered/connected, treat as missed regardless of reason text
                if not answered_at:
                    return self._handle_missed_call(lead_row, event_data)
                if any(k in reason for k in missed_keywords):
                    return self._handle_missed_call(lead_row, event_data)
                if any(k in reason for k in failed_keywords):
                    return self._handle_missed_call(lead_row, event_data)
                # Default: treat as completed
                self._with_retry(self.sheets_manager.update_lead_status, lead_row, "completed")
                return {"status": "success", "action": "call_status_updated", "new_status": "completed"}
        
        elif message_type == "end-of-call-report":
            return self._handle_call_report(lead_row, message)
        
        return {"status": "ignored", "reason": f"Unhandled event type: {message_type}"}
    
    def _handle_missed_call(self, lead_row, event_data):
        """
        Handle a missed call event.
        
        Args:
            lead_row (int): Row index of the lead
            event_data (dict): Event data from Vapi webhook
            
        Returns:
            dict: Result of handling the event
        """
        # Update call status
        self._with_retry(self.sheets_manager.update_lead_status, lead_row, "missed")
        
        # Get current retry count from sheet
        # For simplicity, we'll just use a placeholder value here
        current_retry_count = 0  # In real implementation, get this from the sheet
        
        if self.retry_manager.can_retry(current_retry_count):
            # Increment retry count
            new_retry_count = current_retry_count + 1
            # Calculate next retry time
            next_retry_time = self.retry_manager.get_next_retry_time(current_retry_count)
            
            # Update retry information
            self._with_retry(self.sheets_manager.update_lead_retry, lead_row, new_retry_count, next_retry_time)
            
            return {
                "status": "success", 
                "action": "call_scheduled_for_retry",
                "retry_count": new_retry_count,
                "next_retry_time": next_retry_time
            }
        else:
            # Max retries reached, would trigger fallback here
            return {"status": "success", "action": "max_retries_reached"}
    
    def _handle_call_report(self, lead_row, message):
        """
        Handle an end-of-call report event.
        
        Args:
            lead_row (int): Row index of the lead
            message (dict): Message data from Vapi webhook
            
        Returns:
            dict: Result of handling the event
        """
        print(f"Processing end-of-call report for lead_row {lead_row}")
        
        # Extract AI analysis data
        analysis = message.get("analysis", {})
        
        # Extract summary
        summary = analysis.get("summary", "")
        print(f"Summary: {summary[:100]}...")
        
        # Extract qualification status
        success_status = analysis.get("successEvaluation", "")
        print(f"Success Status: {success_status}")
        
        # Extract structured data
        structured_data = json.dumps(analysis.get("structuredData", {}))
        print(f"Structured Data: {structured_data[:100]}...")
        
        try:
            # Update the sheet with the AI analysis
            print(f"Updating sheet with AI analysis for lead at row {lead_row}")
            self._with_retry(self.sheets_manager.update_ai_analysis, lead_row, summary, success_status, structured_data)
            # Also update call status to completed
            self._with_retry(self.sheets_manager.update_lead_status, lead_row, "completed")
            print(f"Sheet updated successfully for lead at row {lead_row}")
            
            return {
                "status": "success", 
                "action": "call_analysis_processed",
                "lead_row": lead_row,
                "success_status": success_status
            }
        except Exception as e:
            print(f"Error updating AI analysis: {e}")
            return {"error": f"Failed to update AI analysis: {str(e)}"}