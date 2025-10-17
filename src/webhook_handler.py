import json
import time
from datetime import datetime, timedelta
from src.sheets_manager import SheetsManager
from src.retry_manager import RetryManager
from typing import Optional
import os
import re
from src.email_client import EmailClient
from src.vapi_client import VapiClient
from src.observability import trace_webhook_event, log_call_analysis, log_conversation_message
from src.utils import get_ist_timestamp, parse_ist_timestamp, get_ist_now, add_hours_ist

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
                    timestamp=get_ist_timestamp(),
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
        
        # Extract lead_uuid for tracing (do this early)
        try:
            call_metadata = event_data.get("call", {}).get("metadata", {})
            if not call_metadata:
                call_metadata = event_data.get("message", {}).get("call", {}).get("metadata", {})
            lead_uuid = call_metadata.get("lead_uuid") or call_metadata.get("lead_id")
        except Exception:
            lead_uuid = "unknown"
        
        # Create LangFuse span for this webhook event
        webhook_span = trace_webhook_event(message_type, lead_uuid, event_data)
        
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
            
            # Treat explicit answered immediately (single write)
            if status == "answered":
                self._with_retry(self.sheets_manager.update_lead_fields, lead_row, {"call_status": "answered"})
                return {"status": "success", "action": "call_status_updated", "new_status": "answered"}

            # Handle missed/failed explicitly
            if status in ("missed", "failed"):
                return self._handle_missed_call(lead_row, event_data)

            # On ended, decide based on reason
            if status == "ended":
                reason = (ended_reason or "").lower()
                # Persist raw ended reason in the same write where possible
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
            # Default: treat as completed and store ended reason (single write)
            self._with_retry(self.sheets_manager.update_lead_fields, lead_row, {
                "call_status": "completed",
                "last_ended_reason": ended_reason or ''
            })
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
        # We'll update status and retry fields together below when possible
        
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
            # Increment retry count and calculate next retry time
            new_retry_count = current_retry_count + 1
            next_retry_time = self.retry_manager.get_next_retry_time(current_retry_count)
            # Single batched write for status + retry fields
            self._with_retry(
                self.sheets_manager.update_lead_fields,
                lead_row,
                {
                    "call_status": "missed",
                    "retry_count": str(new_retry_count),
                    "next_retry_time": next_retry_time
                }
            )
            return {
                "status": "success",
                "action": "call_scheduled_for_retry",
                "retry_count": new_retry_count,
                "next_retry_time": next_retry_time
            }
        else:
            # Max retries reached: persist missed + clear next_retry_time and trigger WhatsApp fallback
            try:
                self._with_retry(
                    self.sheets_manager.update_lead_fields,
                    lead_row,
                    {
                        "call_status": "missed",
                        "next_retry_time": ""
                    }
                )
            except Exception:
                pass
            self._maybe_send_whatsapp_fallback(lead_row)
            return {"status": "success", "action": "max_retries_reached"}
    
    def _handle_call_report(self, lead_row, message):
        """
        Handle an end-of-call report event with full tracking and validation.
        
        Args:
            lead_row (int): Row index of the lead
            message (dict): Message data from Vapi webhook
            
        Returns:
            dict: Result of handling the event
        """
        print(f"[CallReport] Processing end-of-call report for lead_row {lead_row}")
        
        # Extract AI analysis data
        analysis = message.get("analysis", {})
        call_info = message.get("call", {})
        
        # Extract summary
        summary = analysis.get("summary", "")
        print(f"[CallReport] Summary: {summary[:100]}...")
        
        # Extract qualification status
        success_status = analysis.get("successEvaluation", "")
        print(f"[CallReport] Success Status: {success_status}")
        
        # Extract structured data
        structured_data_dict = analysis.get("structuredData", {})
        structured_data = json.dumps(structured_data_dict)
        print(f"[CallReport] Structured Data: {structured_data[:100]}...")
        
        # Extract call metadata
        call_id = call_info.get("id") or analysis.get("callId")
        call_duration = call_info.get("duration")  # Duration in seconds
        recording_url = message.get("artifact", {}).get("recordingUrl")
        ended_reason = call_info.get("endedReason", "")
        
        print(f"[CallReport] Call ID: {call_id}, Duration: {call_duration}s, Recording: {recording_url is not None}")
        
        # Parse structured data fields for easier dashboard filtering
        country = structured_data_dict.get("country", "")
        university = structured_data_dict.get("university", "")
        course = structured_data_dict.get("course", "")
        intake = structured_data_dict.get("intake", "")
        visa_status = structured_data_dict.get("visa_status", "")
        budget = structured_data_dict.get("budget", "")
        housing_type = structured_data_dict.get("housing_type", "")
        
        try:
            # Prepare comprehensive update with all tracking fields
            analysis_timestamp = get_ist_timestamp()
            update_fields = {
                # Core analysis
                "summary": summary,
                "success_status": success_status,
                "structured_data": structured_data,
                "analysis_received_at": analysis_timestamp,
                "call_status": "completed",
                
                # Call tracking
                "call_duration": str(call_duration) if call_duration else "",
                "recording_url": recording_url or "",
                "last_ended_reason": ended_reason,
                
                # Parsed analysis fields (for dashboard filtering)
                "country": country,
                "university": university,
                "course": course,
                "intake": intake,
                "visa_status": visa_status,
                "budget": budget,
                "housing_type": housing_type
            }
            
            # Update the sheet with the AI analysis in a single batched write
            print(f"[CallReport] Updating sheet with {len(update_fields)} fields for lead at row {lead_row}")
            self._with_retry(
                self.sheets_manager.update_lead_fields,
                lead_row,
                update_fields
            )
            print(f"✅ [CallReport] Analysis saved successfully for lead_row {lead_row}")
        except Exception as update_error:
            print(f"❌ [CallReport] Failed to save analysis for lead_row {lead_row}: {update_error}")
            # Don't fail the entire webhook, just log the error
            return {"error": f"Failed to update AI analysis: {str(update_error)}"}
        
        # Get lead_uuid for LangFuse tracing
        try:
            worksheet = self.sheets_manager.sheet.worksheet("Leads")
            headers = worksheet.row_values(1)
            row_data = worksheet.row_values(lead_row + 2)
            lead = dict(zip(headers, row_data))
            lead_uuid_for_trace = lead.get('lead_uuid', 'unknown')
        except Exception:
            lead_uuid_for_trace = 'unknown'
        
        # Attempt to fetch transcript and log everything to LangFuse
        transcript_text = ''
        try:
            # call_id already extracted above
            if call_id and self.vapi_client is not None:
                print(f"[CallReport] Fetching transcript for call_id: {call_id}")
                t = self.vapi_client.get_transcription(call_id)
                print(f"[CallReport] Transcript API response type: {type(t)}, keys: {t.keys() if isinstance(t, dict) else 'N/A'}")
                
                if isinstance(t, dict):
                    # Try different possible transcript formats
                    transcript_text = t.get('transcript') or t.get('text') or t.get('content') or ''
                    
                    # Check if error in response
                    if t.get('error'):
                        print(f"[CallReport] Transcript API error: {t.get('error')}")
                    
                    # Some APIs return array of segments
                    if not transcript_text and isinstance(t.get('segments'), list):
                        transcript_text = ' '.join([s.get('text','') for s in t['segments']])
                    
                    # Check if it's in 'messages' array (common Vapi format)
                    if not transcript_text and isinstance(t.get('messages'), list):
                        messages = []
                        for msg in t['messages']:
                            role = msg.get('role', 'unknown')
                            content = msg.get('message', '') or msg.get('content', '')
                            if content:
                                messages.append(f"{role}: {content}")
                        transcript_text = '\n\n'.join(messages)
                    
                    print(f"[CallReport] Extracted transcript length: {len(transcript_text)} chars")
                else:
                    print(f"[CallReport] Transcript response is not a dict: {t}")
                
                if transcript_text:
                    # Store transcript in sheet
                    self._with_retry(self.sheets_manager.update_transcript, lead_row, transcript_text)
                    print(f"[CallReport] ✅ Transcript stored successfully ({len(transcript_text)} chars)")
                else:
                    print(f"[CallReport] ⚠️  No transcript text found in response")
        except Exception as te:
            print(f"[CallReport] ❌ Transcript fetch/store failed: {te}")
            import traceback
            traceback.print_exc()
        
        # Log complete analysis to LangFuse with all details
        try:
            log_call_analysis(
                lead_uuid=lead_uuid_for_trace,
                summary=summary,
                success_status=success_status,
                structured_data=json.loads(structured_data) if isinstance(structured_data, str) else structured_data,
                call_id=call_id,
                transcript=transcript_text,
                call_duration=call_duration,
                recording_url=recording_url
            )
            print(f"[CallReport] Analysis logged to LangFuse")
        except Exception as lf_error:
            print(f"[CallReport] LangFuse logging failed: {lf_error}")
        
        # Check for callback request in summary or structured data
        try:
            callback_time = self._extract_callback_request(summary, structured_data, lead_uuid_for_trace)
            if callback_time:
                self._schedule_callback(lead_uuid_for_trace, lead_row, callback_time)
        except Exception as ce:
            print(f"Callback scheduling failed: {ce}")
        
        # Send WhatsApp follow-up if configured
        self._maybe_send_whatsapp_followup(lead_row, message)
        print(f"✅ [CallReport] Sheet updated successfully for lead at row {lead_row}")
        
        return {
            "status": "success", 
            "action": "call_analysis_processed",
            "lead_row": lead_row,
            "success_status": success_status
        }

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
                    timestamp=get_ist_timestamp(),
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
                    timestamp=get_ist_timestamp(),
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
    
    def _extract_callback_request(self, summary: str, structured_data_json: str, lead_uuid: str) -> Optional[datetime]:
        """
        Extract callback request from call summary or structured data.
        
        Args:
            summary: Call summary text
            structured_data_json: JSON string of structured data
            lead_uuid: Lead UUID for logging
            
        Returns:
            datetime object if callback requested, None otherwise
        """
        # Check for callback keywords
        callback_keywords = [
            "call back", "callback", "call me back", "call later", 
            "call tomorrow", "call at", "reach out later"
        ]
        
        summary_lower = summary.lower()
        has_callback_request = any(keyword in summary_lower for keyword in callback_keywords)
        
        if not has_callback_request:
            return None
        
        print(f"[Callback] Detected callback request for {lead_uuid}")
        
        # Try to extract time from structured data first
        try:
            structured_data = json.loads(structured_data_json) if isinstance(structured_data_json, str) else structured_data_json
            callback_info = structured_data.get('callback_time') or structured_data.get('preferred_contact_time')
            if callback_info:
                parsed_time = self._parse_callback_time(callback_info)
                if parsed_time:
                    print(f"[Callback] Extracted from structured data: {parsed_time}")
                    return parsed_time
        except Exception as e:
            print(f"[Callback] Could not parse structured data: {e}")
        
        # Fall back to extracting from summary text
        parsed_time = self._parse_callback_time(summary)
        if parsed_time:
            print(f"[Callback] Extracted from summary: {parsed_time}")
            return parsed_time
        
        # Default: schedule for 24 hours from now if no specific time found
        default_time = add_hours_ist(24)
        print(f"[Callback] Using default time (24h from now): {default_time}")
        return default_time
    
    def _parse_callback_time(self, text: str) -> Optional[datetime]:
        """
        Parse callback time from natural language text.
        
        Args:
            text: Text containing time reference
            
        Returns:
            datetime object or None
        """
        text_lower = text.lower()
        now = get_ist_now()
        
        # Pattern: "tomorrow at 5 PM", "tomorrow 5pm", "tomorrow at 17:00"
        tomorrow_match = re.search(r'tomorrow\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_lower)
        if tomorrow_match:
            hour = int(tomorrow_match.group(1))
            minute = int(tomorrow_match.group(2)) if tomorrow_match.group(2) else 0
            period = tomorrow_match.group(3)
            
            if period == 'pm' and hour < 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Pattern: "at 5 PM today", "at 17:00", "5pm today"
        today_match = re.search(r'(?:today\s+)?(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text_lower)
        if today_match:
            hour = int(today_match.group(1))
            minute = int(today_match.group(2)) if today_match.group(2) else 0
            period = today_match.group(3)
            
            if period == 'pm' and hour < 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            
            callback_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # If time has already passed today, schedule for tomorrow
            if callback_time < now:
                callback_time += timedelta(days=1)
            return callback_time
        
        # Pattern: "in 2 hours", "in 30 minutes"
        relative_match = re.search(r'in\s+(\d+)\s+(hour|minute)s?', text_lower)
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(2)
            if unit == 'hour':
                return now + timedelta(hours=amount)
            elif unit == 'minute':
                return now + timedelta(minutes=amount)
        
        # Pattern: "Monday", "Tuesday", etc. (next occurrence)
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days_of_week):
            if day in text_lower:
                current_weekday = now.weekday()
                target_weekday = i
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:  # Same day, schedule for next week
                    days_ahead = 7
                target_date = now + timedelta(days=days_ahead)
                # Default to 10 AM if no time specified
                return target_date.replace(hour=10, minute=0, second=0, microsecond=0)
        
        return None
    
    def _schedule_callback(self, lead_uuid: str, lead_row: int, callback_time: datetime):
        """
        Schedule a callback for the lead.
        
        Args:
            lead_uuid: Lead UUID
            lead_row: Lead row index
            callback_time: When to call back
        """
        try:
            from src.scheduler import schedule_one_time_callback
            
            # Update sheet with callback time
            self._with_retry(
                self.sheets_manager.update_lead_fields,
                lead_row,
                {
                    "callback_requested": "true",
                    "callback_time": callback_time.isoformat(),
                    "call_status": "callback_scheduled"
                }
            )
            
            # Schedule the callback job
            schedule_one_time_callback(lead_uuid, callback_time)
            
            print(f"[Callback] Scheduled callback for {lead_uuid} at {callback_time}")
            
        except Exception as e:
            print(f"[Callback] Failed to schedule callback: {e}")