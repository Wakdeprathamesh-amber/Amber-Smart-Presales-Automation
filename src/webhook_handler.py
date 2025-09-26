import json
import time
from datetime import datetime
from src.sheets_manager import SheetsManager
from src.retry_manager import RetryManager
from typing import Optional
import os
from src.email_client import EmailClient
from src.vapi_client import VapiClient

class WebhookHandler:
    def __init__(self, sheets_manager, retry_manager, whatsapp_client: Optional[object] = None,
                 whatsapp_followup_template: Optional[str] = None,
                 whatsapp_fallback_template: Optional[str] = None,
                 whatsapp_language: str = "en",
                 whatsapp_enable_followup: bool = True,
                 whatsapp_enable_fallback: bool = True,
                 email_client: Optional[EmailClient] = None,
                 vapi_client: Optional[VapiClient] = None):
        """
        Initialize the webhook handler.
        
        Args:
            sheets_manager (SheetsManager): Instance of SheetsManager
            retry_manager (RetryManager): Instance of RetryManager
        """
        self.sheets_manager = sheets_manager
        self.retry_manager = retry_manager
        self.whatsapp_client = whatsapp_client
        self.whatsapp_followup_template = whatsapp_followup_template
        self.whatsapp_fallback_template = whatsapp_fallback_template
        self.whatsapp_language = whatsapp_language or "en"
        self.whatsapp_enable_followup = bool(whatsapp_enable_followup)
        self.whatsapp_enable_fallback = bool(whatsapp_enable_fallback)
        # Cache to reduce repeated sheet reads when resolving rows by lead_uuid
        self._row_cache = {}
        self.email_client = email_client
        self.vapi_client = vapi_client

    def _resolve_email_settings(self) -> dict:
        """Return subject/body defaults for missed-call follow-up."""
        subject = os.getenv('EMAIL_SUBJECT') or 'Missed Call Follow-Up Email'
        body = os.getenv('EMAIL_TEMPLATE_BODY') or (
            "Hi {name},\n\n"
            "We just tried reaching you over a call but couldn’t get through.\n\n"
            "Could you let us know the best way to stay in touch — WhatsApp, Call, or Email?\n\n"
            "Also, just to confirm — are you a student planning to study in UK, Ireland, France, Germany, Spain, USA, Canada, or Australia?\n\n"
            "If yes, it would be super helpful if you could share:\n"
            "🎓 Country/City/University (if decided)\n"
            "💰 Rough budget in mind\n"
            "⏰ Timeline for moving\n"
            "🛂 Visa status\n\n"
            "Based on these details, our experts will curate the best housing options for you and share them directly.\n\n"
            "Looking forward to helping you,\n"
            "Team Amber\n"
            "🌐 https://amberstudent.com"
        )
        return {"subject": subject, "body": body}

    def _maybe_send_missed_call_email(self, lead_row: int):
        if self.email_client is None:
            return
        try:
            ws = self.sheets_manager.sheet.worksheet("Leads")
            headers = ws.row_values(1)
            row = ws.row_values(lead_row + 2)
            lead = dict(zip(headers, row))
            lead_uuid = lead.get('lead_uuid') or ''
            to_email = (lead.get('email') or '').strip()
            already_sent = str(lead.get('email_sent', 'false')).lower() == 'true'
            name = (lead.get('name') or 'there')
            if not to_email or already_sent:
                return
            settings = self._resolve_email_settings()
            subject = settings['subject']
            body_text = (settings['body'] or '').format(name=name)
            tagged_subject = f"{subject} [Lead:{lead_uuid}]"
            res = self.email_client.send(
                to_email=to_email,
                subject=tagged_subject,
                body_text=body_text,
                extra_headers={'X-Lead-UUID': lead_uuid}
            )
            # Mark email_sent and log conversation
            try:
                self._with_retry(self.sheets_manager.update_fallback_status, lead_row, email_sent=True)
            except Exception:
                pass
            try:
                self.sheets_manager.log_conversation(
                    lead_uuid=lead_uuid,
                    channel='email',
                    direction='out',
                    timestamp=datetime.now().isoformat(),
                    subject=tagged_subject,
                    content=body_text,
                    summary='',
                    metadata=json.dumps({"dry_run": res.get('dry_run', False)}),
                    message_id=res.get('id', ''),
                    status='sent'
                )
            except Exception:
                pass
        except Exception:
            pass

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
                try:
                    # Persist raw ended reason
                    self._with_retry(self.sheets_manager.update_last_ended_reason, lead_row, ended_reason or '')
                except Exception:
                    pass
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
        try:
            worksheet = self.sheets_manager.sheet.worksheet("Leads")
            headers = worksheet.row_values(1)
            row = worksheet.row_values(lead_row + 2)
            lead = dict(zip(headers, row))
            current_retry_count = int(lead.get('retry_count') or 0)
        except Exception:
            current_retry_count = 0
        
        # Attempt to send a missed-call follow-up email once if not already sent
        try:
            self._maybe_send_missed_call_email(lead_row)
        except Exception:
            pass

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
            # Max retries reached: trigger WhatsApp fallback if configured
            self._maybe_send_whatsapp_fallback(lead_row)
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
            # Attempt to fetch transcript if possible
            try:
                call_info = message.get("call", {})
                call_id = (call_info or {}).get("id")
                if not call_id:
                    call_id = (analysis or {}).get("callId")
                if call_id and self.vapi_client is not None:
                    t = self.vapi_client.get_transcription(call_id)
                    transcript_text = ''
                    if isinstance(t, dict):
                        transcript_text = t.get('transcript') or t.get('text') or ''
                        # Some APIs return array of segments
                        if not transcript_text and isinstance(t.get('segments'), list):
                            transcript_text = ' '.join([s.get('text','') for s in t['segments']])
                    if transcript_text:
                        self._with_retry(self.sheets_manager.update_transcript, lead_row, transcript_text)
            except Exception as te:
                print(f"Transcript fetch/store skipped: {te}")
            # Send WhatsApp follow-up if configured
            self._maybe_send_whatsapp_followup(lead_row, message)
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

    def _maybe_send_whatsapp_followup(self, lead_row: int, message: dict):
        """Send WhatsApp follow-up after a successful call if config present."""
        if not self.whatsapp_enable_followup or not self.whatsapp_client or not self.whatsapp_followup_template:
            return
        try:
            # Resolve lead data
            worksheet = self.sheets_manager.sheet.worksheet("Leads")
            headers = worksheet.row_values(1)
            row = worksheet.row_values(lead_row + 2)
            lead = dict(zip(headers, row))
            to_number = (lead.get('whatsapp_number') or lead.get('number') or '').strip()
            name = (lead.get('name') or '').strip()
            if not to_number:
                return
            # Prepare parameters: name and maybe a short status
            params = [name or "there"]
            wa_res = self.whatsapp_client.send_template(
                to_number_e164=to_number,
                template_name=self.whatsapp_followup_template,
                language=self.whatsapp_language,
                body_parameters=params
            )
            # Mark whatsapp_sent = true (non-destructive update)
            self._with_retry(self.sheets_manager.update_fallback_status, lead_row, whatsapp_sent=True)
            # Log conversation
            try:
                # Need lead_uuid for logging; fetch from row
                lead_uuid = lead.get('lead_uuid') or ''
                self.sheets_manager.log_conversation(
                    lead_uuid=lead_uuid,
                    channel='whatsapp',
                    direction='out',
                    timestamp=datetime.now().isoformat(),
                    subject=self.whatsapp_followup_template or 'whatsapp_followup',
                    content=f"Sent WhatsApp template {self.whatsapp_followup_template}",
                    summary='',
                    metadata=json.dumps({"dry_run": wa_res.get('dry_run', False), "language": self.whatsapp_language}),
                    message_id=str(wa_res.get('messages', [{}])[0].get('id', '')) if isinstance(wa_res, dict) else '',
                    status='sent'
                )
            except Exception:
                pass
        except Exception:
            # Keep silent to avoid blocking flow
            pass

    def _maybe_send_whatsapp_fallback(self, lead_row: int):
        """Send WhatsApp fallback message when max retries are reached."""
        if not self.whatsapp_enable_fallback or not self.whatsapp_client or not self.whatsapp_fallback_template:
            return
        try:
            worksheet = self.sheets_manager.sheet.worksheet("Leads")
            headers = worksheet.row_values(1)
            row = worksheet.row_values(lead_row + 2)
            lead = dict(zip(headers, row))
            to_number = (lead.get('whatsapp_number') or lead.get('number') or '').strip()
            name = (lead.get('name') or '').strip()
            if not to_number:
                return
            params = [name or "there"]
            wa_res = self.whatsapp_client.send_template(
                to_number_e164=to_number,
                template_name=self.whatsapp_fallback_template,
                language=self.whatsapp_language,
                body_parameters=params
            )
            self._with_retry(self.sheets_manager.update_fallback_status, lead_row, whatsapp_sent=True)
            try:
                lead_uuid = lead.get('lead_uuid') or ''
                self.sheets_manager.log_conversation(
                    lead_uuid=lead_uuid,
                    channel='whatsapp',
                    direction='out',
                    timestamp=datetime.now().isoformat(),
                    subject=self.whatsapp_fallback_template or 'whatsapp_fallback',
                    content=f"Sent WhatsApp template {self.whatsapp_fallback_template}",
                    summary='',
                    metadata=json.dumps({"dry_run": wa_res.get('dry_run', False), "language": self.whatsapp_language}),
                    message_id=str(wa_res.get('messages', [{}])[0].get('id', '')) if isinstance(wa_res, dict) else '',
                    status='sent'
                )
            except Exception:
                pass
        except Exception:
            pass