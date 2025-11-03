import os
import json
import logging
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template, url_for
import csv
from io import StringIO
from dotenv import load_dotenv
import uuid
from src.sheets_manager import SheetsManager
from src.vapi_client import VapiClient
from src.retry_manager import RetryManager
from src.whatsapp_client import WhatsAppClient
from src.email_client import EmailClient
from src.webhook_handler import WebhookHandler
from src.utils import get_ist_timestamp, get_ist_now

# Load environment variables
load_dotenv()

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize components lazily to avoid import-time errors
sheets_manager = None
retry_manager = None
vapi_client = None
webhook_handler = None
whatsapp_client = None
email_client = None

# Simple in-memory caches
_leads_cache = {"data": None, "ts": 0}
_details_cache = {}
_CACHE_TTL_SECONDS = 10  # Short cache for real-time updates (was 60s, too long for production)
_CACHE_STALE_OK_SECONDS = 300  # Serve stale cache for up to 5 minutes during rate limit errors


def _invalidate_leads_cache():
    """Invalidate the leads cache to force refresh on next request."""
    global _leads_cache
    _leads_cache["data"] = None
    _leads_cache["ts"] = 0
    logger.debug("🔄 Leads cache invalidated")


def _resolve_email_settings() -> dict:
    """Return current email subject/body applying Eshwari defaults and overriding legacy placeholders."""
    default_subject = 'Missed Call Follow-Up Email'
    default_body = (
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
    env_subject = os.getenv('EMAIL_SUBJECT')
    env_body = os.getenv('EMAIL_TEMPLATE_BODY')
    legacy_subject = 'Welcome to Amber'
    legacy_body_prefix = 'Hi {name},\n\nAmber helps with student housing'
    subject = env_subject if env_subject else default_subject
    body = env_body if env_body else default_body
    if (subject.strip() == legacy_subject) or (env_body and env_body.strip().startswith(legacy_body_prefix)):
        subject = default_subject
        body = default_body
    return {"subject": subject, "body": body}

def get_sheets_manager():
    """Get or create sheets manager instance."""
    global sheets_manager
    if sheets_manager is None:
        credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
        sheet_id = os.getenv('LEADS_SHEET_ID')
        
        if not credentials_file or not sheet_id:
            logger.error("Missing GOOGLE_SHEETS_CREDENTIALS_FILE or LEADS_SHEET_ID environment variables")
            raise ValueError("Google Sheets credentials not configured")
        
        if not os.path.exists(credentials_file):
            logger.error(f"Credentials file not found: {credentials_file}")
            raise ValueError(f"Credentials file not found: {credentials_file}")
        
        sheets_manager = SheetsManager(
            credentials_file=credentials_file,
            sheet_id=sheet_id
        )
    return sheets_manager

def get_retry_manager():
    """Get or create retry manager instance."""
    global retry_manager
    if retry_manager is None:
        retry_intervals_env = os.getenv('RETRY_INTERVALS', '0.5,24')
        retry_units_env = os.getenv('RETRY_UNITS', 'hours')
        retry_intervals = []
        try:
            retry_intervals = [float(x.strip()) for x in retry_intervals_env.split(',') if x.strip()]
        except Exception:
            retry_intervals = [0.5, 24]
        
        retry_manager = RetryManager(
            max_retries=int(os.getenv('MAX_RETRY_COUNT', '3')),
            retry_intervals=retry_intervals,
            interval_unit=retry_units_env
        )
    return retry_manager

def get_vapi_client():
    """Get or create Vapi client instance."""
    global vapi_client
    if vapi_client is None:
        api_key = os.getenv('VAPI_API_KEY')
        if not api_key:
            logger.error("Missing VAPI_API_KEY environment variable")
            raise ValueError("Vapi API key not configured")
        vapi_client = VapiClient(api_key=api_key)
    return vapi_client

def get_webhook_handler():
    """Get or create webhook handler instance."""
    global webhook_handler
    if webhook_handler is None:
        webhook_handler = WebhookHandler(
            sheets_manager=get_sheets_manager(),
            retry_manager=get_retry_manager(),
            whatsapp_client=get_whatsapp_client(optional=True),
            whatsapp_followup_template=os.getenv('WHATSAPP_TEMPLATE_FOLLOWUP'),
            whatsapp_fallback_template=os.getenv('WHATSAPP_TEMPLATE_FALLBACK'),
            whatsapp_language=os.getenv('WHATSAPP_LANGUAGE', 'en'),
            whatsapp_enable_followup=os.getenv('WHATSAPP_ENABLE_FOLLOWUP', 'true').lower() == 'true',
            whatsapp_enable_fallback=os.getenv('WHATSAPP_ENABLE_FALLBACK', 'true').lower() == 'true',
            email_client=get_email_client(),
            vapi_client=get_vapi_client()
        )
        
    return webhook_handler

def get_whatsapp_client(optional: bool = False):
    """Get or create WhatsApp client instance."""
    global whatsapp_client
    if whatsapp_client is None:
        access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        dry_run = os.getenv('WHATSAPP_DRY_RUN', 'false').lower() == 'true'
        if (not access_token or not phone_number_id) and not dry_run:
            if optional:
                return None
            logger.error("Missing WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID")
            raise ValueError("WhatsApp API not configured")
        whatsapp_client = WhatsAppClient(access_token=access_token or 'DUMMY', phone_number_id=phone_number_id or '0', dry_run=dry_run)
    return whatsapp_client

def get_email_client():
    global email_client
    if email_client is None:
        # For POC default to dry-run on
        email_client = EmailClient(dry_run=os.getenv('EMAIL_DRY_RUN', 'true').lower() == 'true')
    return email_client

# Create Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')
# Utility
def _normalize_phone(raw: str) -> str:
    """
    Normalize phone number using advanced sanitization.
    Handles spaces, dashes, parentheses, and ensures proper format.
    
    Args:
        raw: Raw phone number input
        
    Returns:
        str: Sanitized E.164 format (e.g., "+919876543210")
    """
    from src.utils import sanitize_phone_number
    return sanitize_phone_number(raw)

def _is_valid_phone(phone: str) -> bool:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate (should be sanitized first)
        
    Returns:
        bool: True if valid, False otherwise
    """
    from src.utils import validate_phone_number
    is_valid, error_msg = validate_phone_number(phone)
    if not is_valid:
        logger.warning(f"Phone validation failed: {error_msg}")
    return is_valid

# Dashboard routes
@app.route('/')
def index():
    """Render the dashboard homepage."""
    return render_template('index.html')

@app.route('/api/version', methods=['GET'])
def get_version():
    """Get current deployment version."""
    try:
        from src.version import VERSION, LAST_UPDATED, RECENT_FIXES
        from src.utils import sanitize_phone_number
        
        # Test phone sanitization
        test_result = sanitize_phone_number("91 9876543210")
        has_double_plus_bug = test_result.startswith("++")
        
        return jsonify({
            "version": VERSION,
            "last_updated": LAST_UPDATED,
            "recent_fixes": RECENT_FIXES,
            "phone_sanitization_test": {
                "input": "91 9876543210",
                "output": test_result,
                "has_double_plus_bug": has_double_plus_bug,
                "status": "BROKEN" if has_double_plus_bug else "FIXED"
            }
        })
    except Exception as e:
        return jsonify({"error": str(e), "version": "unknown"}), 500

# API routes
@app.route('/api/leads', methods=['GET'])
def get_leads():
    """Get all leads from Google Sheets."""
    try:
        # Check for cache-busting parameter
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        # Serve from cache if fresh (unless force refresh)
        from time import time
        now = time()
        if not force_refresh and _leads_cache["data"] is not None and (now - _leads_cache["ts"]) < _CACHE_TTL_SECONDS:
            logger.debug(f"Serving leads from fresh cache (age: {now - _leads_cache['ts']:.1f}s)")
            return jsonify(_leads_cache["data"]) 
        
        # Try to fetch from Sheets
        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        
        # Check if sheet is empty or has no data rows
        values = worksheet.get_values()
        if len(values) <= 1:  # Only header row or empty
            logger.info("Sheet is empty or has only headers")
            _leads_cache["data"] = []
            _leads_cache["ts"] = now
            return jsonify([])
            
        # Get all records
        leads = worksheet.get_all_records()
        
        # Add ID to each lead (row index for simplicity)
        for idx, lead in enumerate(leads):
            lead['id'] = str(idx)
        
        # Update cache with fresh data
        _leads_cache["data"] = leads
        _leads_cache["ts"] = now
        logger.debug(f"Fetched {len(leads)} leads from Sheets, cache updated")
        return jsonify(leads)
        
    except Exception as e:
        # Check if error is rate limiting (429)
        error_msg = str(e)
        is_rate_limit = '429' in error_msg or 'RATE_LIMIT_EXCEEDED' in error_msg
        
        # Serve stale cache if available (even if old) during rate limits
        if _leads_cache["data"] is not None:
            cache_age = time() - _leads_cache["ts"]
            
            if is_rate_limit:
                logger.warning(f"⚠️  Google Sheets rate limit hit! Serving stale cache (age: {cache_age:.1f}s)")
            elif cache_age < _CACHE_STALE_OK_SECONDS:
                logger.warning(f"Sheets read failed, serving stale cache (age: {cache_age:.1f}s): {e}")
            else:
                logger.error(f"Sheets read failed and cache too old ({cache_age:.1f}s), serving anyway: {e}")
            
            return jsonify(_leads_cache["data"])
        
        # No cache available at all
        if is_rate_limit:
            logger.error(f"⚠️  Google Sheets rate limit and no cache! Returning empty. Wait 60s before retry.")
        else:
            logger.error(f"Error getting leads and no cache available: {e}", exc_info=True)
        
        return jsonify([])

@app.route('/api/leads', methods=['POST'])
def add_lead():
    """Add a new lead to Google Sheets."""
    try:
        lead_data = request.json
        
        # Validate required fields
        if not lead_data.get('number') or not lead_data.get('name'):
            return jsonify({"error": "Name and phone number are required"}), 400
        
        # Get the worksheet
        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        
        # Prepare the new lead row with stable UUID
        lead_uuid = str(uuid.uuid4())
        
        # Sanitize and validate phone numbers
        number_e164 = _normalize_phone(lead_data.get('number', ''))
        whatsapp_input = lead_data.get('whatsapp_number', '') or lead_data.get('number', '')
        whatsapp_e164 = _normalize_phone(whatsapp_input) if whatsapp_input else number_e164
        
        # Validate phone number
        if not _is_valid_phone(number_e164):
            return jsonify({
                "error": "Invalid phone number format. Use format: +919876543210 or 91 9876543210 or 919876543210"
            }), 400
        new_lead = [
            lead_uuid,                          # lead_uuid
            number_e164,                            # number (E.164)
            whatsapp_e164,                          # whatsapp_number (E.164)
            lead_data.get('name', ''),             # name
            lead_data.get('email', ''),            # email
            'pending',                             # call_status
            '0',                                   # retry_count
            '',                                    # next_retry_time
            'false',                               # whatsapp_sent
            'false',                               # email_sent
            '',                                    # summary
            '',                                    # success_status
            '',                                    # structured_data
            '',                                    # last_call_time
            '',                                    # vapi_call_id
            ''                                     # last_analysis_at
        ]
        
        # Add the new lead
        worksheet.append_row(new_lead)
        # Optional partner field
        try:
            partner = (lead_data.get('partner') or '').strip()
            if partner:
                headers = worksheet.row_values(1)
                if 'partner' not in headers:
                    worksheet.update_cell(1, len(headers) + 1, 'partner')
                    headers.append('partner')
                partner_col = headers.index('partner') + 1
                # Find the newly appended row and write partner
                new_row_index_0 = get_sheets_manager().find_row_by_lead_uuid(lead_uuid)
                if new_row_index_0 is not None:
                    worksheet.update_cell(new_row_index_0 + 2, partner_col, partner)
        except Exception:
            pass
        
        # Invalidate cache to show new lead immediately
        _invalidate_leads_cache()
        
        return jsonify({"success": True, "message": "Lead added successfully", "lead_uuid": lead_uuid})
    except Exception as e:
        logger.error(f"Error adding lead: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<lead_uuid>/call', methods=['POST'])
def initiate_call(lead_uuid):
    """Initiate a call to a specific lead."""
    try:
        # Locate row by lead_uuid
        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        row_index_0 = get_sheets_manager().find_row_by_lead_uuid(lead_uuid)
        if row_index_0 is None:
            return jsonify({"error": "Lead not found"}), 404
        leads = worksheet.get_all_records()
        lead = leads[row_index_0]
        
        # Allow manual call at any status; backend will record initiation time
        
        # Prepare lead data
        lead_data = {
            "lead_uuid": lead_uuid,
            "number": lead.get('number'),
            "name": lead.get('name'),
            "email": lead.get('email'),
            "partner": lead.get('partner')
        }
        
        # Get Vapi assistant ID and phone number ID
        assistant_id = os.getenv('VAPI_ASSISTANT_ID')
        phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID')
        if not assistant_id or not phone_number_id:
            logger.error("Missing VAPI_ASSISTANT_ID or VAPI_PHONE_NUMBER_ID")
            return jsonify({
                "error": "Vapi configuration missing",
                "details": "Set VAPI_ASSISTANT_ID and VAPI_PHONE_NUMBER_ID in environment"
            }), 500
        
        # Record call initiation time
        call_time = get_ist_timestamp()
        
        # Initiate call
        call_result = get_vapi_client().initiate_outbound_call(
            lead_data=lead_data,
            assistant_id=assistant_id,
            phone_number_id=phone_number_id
        )
        
        if "error" in call_result:
            # Surface Vapi response body for debugging (if present)
            return jsonify({
                "error": call_result.get("error"),
                "details": call_result.get("body")
            }), 500
        
        # Extract Vapi call ID
        vapi_call_id = call_result.get('id', '')
        
        # Update lead status, call time, and call ID in one batch
        get_sheets_manager().update_lead_fields(row_index_0, {
            "call_status": "initiated",
            "vapi_call_id": vapi_call_id,
            "last_call_time": call_time
        })
        # Increment retry_count for manual initiation, regardless of previous status
        try:
            current_retry = int(str(lead.get('retry_count') or '0'))
        except Exception:
            current_retry = 0
        next_retry_time = ''
        try:
            get_sheets_manager().update_lead_retry(row_index_0, current_retry + 1, next_retry_time)
        except Exception:
            pass
        # Send first-contact email if not already sent
        try:
            if str(lead.get('email_sent', 'false')).lower() != 'true' and lead.get('email'):
                # Build email from settings
                settings = _resolve_email_settings()
                subject = settings["subject"]
                template_body = settings["body"]
                body_text = template_body.format(name=lead.get('name') or 'there')
                tagged_subject = f"{subject} [Lead:{lead_uuid}]"
                em_res = get_email_client().send(
                    to_email=lead.get('email'),
                    subject=tagged_subject,
                    body_text=body_text,
                    extra_headers={
                        'X-Lead-UUID': lead_uuid,
                        'References': lead.get('vapi_call_id', '') or ''
                    }
                )
                # Mark email_sent
                get_sheets_manager().update_fallback_status(row_index_0, email_sent=True)
                # Log conversation
                try:
                    get_sheets_manager().log_conversation(
                        lead_uuid=lead_uuid,
                        channel='email',
                        direction='out',
                        timestamp=call_time,
                        subject=tagged_subject,
                        content=body_text,
                        summary='',
                        metadata=json.dumps({"dry_run": em_res.get('dry_run', False)}),
                        message_id=em_res.get('id', ''),
                        status='sent'
                    )
                except Exception:
                    pass
        except Exception:
            pass
        # Store vapi_call_id if available
        try:
            vapi_call_id = call_result.get('id')
            if vapi_call_id:
                headers = worksheet.row_values(1)
                if 'vapi_call_id' in headers:
                    col = headers.index('vapi_call_id') + 1
                    worksheet.update_cell(row_index_0 + 2, col, vapi_call_id)
        except Exception:
            pass
        
        # Invalidate cache to show updated status immediately
        _invalidate_leads_cache()
        
        return jsonify({
            "success": True,
            "message": "Call initiated successfully",
            "call_id": call_result.get('id'),
            "call_time": call_time
        })
    except Exception as e:
        logger.error(f"Error initiating call: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<lead_uuid>', methods=['DELETE'])
def delete_lead(lead_uuid):
    """Delete a lead by lead_uuid."""
    try:
        deleted = get_sheets_manager().delete_lead_by_uuid(lead_uuid)
        if not deleted:
            return jsonify({"error": "Lead not found"}), 404
        
        # Invalidate cache to remove deleted lead immediately
        _invalidate_leads_cache()
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting lead {lead_uuid}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Webhook endpoint
@app.route('/webhook/vapi', methods=['POST'])
def vapi_webhook():
    """Endpoint for Vapi webhooks."""
    try:
        event_data = request.json
        logger.info(f"Received webhook event: {json.dumps(event_data)}")
        
        result = get_webhook_handler().handle_event(event_data)
        
        # Invalidate cache after webhook updates (call status changes, etc.)
        _invalidate_leads_cache()
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<lead_uuid>/details', methods=['GET'])
def get_lead_details(lead_uuid):
    """Get detailed information for a specific lead."""
    try:
        # Serve from cache if fresh
        from time import time
        now = time()
        cached = _details_cache.get(lead_uuid)
        if cached and (now - cached.get("ts", 0)) < _CACHE_TTL_SECONDS:
            return jsonify(cached["data"])
        # Get the worksheet
        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        
        # Check if sheet is empty or has no data rows
        values = worksheet.get_values()
        if len(values) <= 1:  # Only header row or empty
            logger.info("Sheet is empty or has only headers")
            return jsonify({"error": "No leads found in sheet"}), 404
            
        # Get all records
        row_index_0 = get_sheets_manager().find_row_by_lead_uuid(lead_uuid)
        if row_index_0 is None:
            return jsonify({"error": "Lead not found"}), 404
        leads = worksheet.get_all_records()
        lead = leads[row_index_0]
        lead['lead_uuid'] = lead_uuid
        
        # Parse structured data if it exists
        if lead.get('structured_data') and lead['structured_data']:
            try:
                lead['structured_data'] = json.loads(lead['structured_data'])
            except json.JSONDecodeError:
                # If not valid JSON, keep as is
                lead['structured_data'] = {}
        
        # Get call history if available
        try:
            call_history = get_sheets_manager().get_call_history(row_index_0)
            lead['call_history'] = call_history
            conv = get_sheets_manager().get_conversations_by_lead(lead_uuid)
            lead['conversations'] = conv
        except Exception as e:
            logger.warning(f"Error getting call history: {e}")
            lead['call_history'] = []
            lead['conversations'] = []
        
        _details_cache[lead_uuid] = {"data": lead, "ts": now}
        return jsonify(lead)
    except Exception as e:
        # Serve stale cached details if available
        cached = _details_cache.get(lead_uuid)
        if cached and cached.get("data"):
            logger.warning(f"Sheets read failed, serving cached details for {lead_uuid}: {e}")
            return jsonify(cached["data"]) 
        # Fallback to minimal data from leads cache to avoid 500 during quota spikes
        if _leads_cache.get("data"):
            try:
                for candidate in _leads_cache["data"] or []:
                    if candidate.get('lead_uuid') == lead_uuid:
                        minimal = dict(candidate)
                        # Ensure keys expected by details view exist
                        minimal.setdefault('structured_data', {})
                        minimal.setdefault('call_history', [])
                        minimal.setdefault('conversations', [])
                        return jsonify(minimal)
            except Exception:
                pass
        logger.error(f"Error getting lead details and no cache available: {e}", exc_info=True)
        return jsonify({"error": "Failed to get lead details"}), 500

@app.route('/api/retry-config', methods=['GET'])
def get_retry_config():
    """Get the current retry configuration."""
    try:
        config = {
            "max_retries": get_retry_manager().max_retries,
            "retry_intervals": get_retry_manager().retry_intervals
        }
        return jsonify(config)
    except Exception as e:
        logger.error(f"Error getting retry config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/retry-config', methods=['POST'])
def update_retry_config():
    """Update the retry configuration."""
    try:
        data = request.get_json(silent=True) or {}
        rm = get_retry_manager()
        max_retries = int(data.get('max_retries', rm.max_retries))
        intervals = data.get('retry_intervals') or rm.retry_intervals
        units = (data.get('interval_unit') or rm.interval_unit).lower()

        # Normalize intervals to floats
        intervals = [float(x) for x in intervals]

        rm.max_retries = max_retries
        rm.retry_intervals = intervals
        rm.interval_unit = 'minutes' if units == 'minutes' else 'hours'

        # Reflect in process env (for consistency if other modules read it later)
        os.environ['MAX_RETRY_COUNT'] = str(max_retries)
        os.environ['RETRY_INTERVALS'] = ','.join([str(x) for x in intervals])
        os.environ['RETRY_UNITS'] = rm.interval_unit

        return jsonify({
            "success": True,
            "message": "Retry configuration updated successfully",
            "config": {
                "max_retries": rm.max_retries,
                "retry_intervals": rm.retry_intervals,
                "interval_unit": rm.interval_unit
            }
        })
    except Exception as e:
        logger.error(f"Error updating retry config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/bulk-upload', methods=['POST'])
def bulk_upload_leads():
    """Upload leads via CSV (columns: number,name,email,whatsapp_number(optional),partner(optional))."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "CSV file is required with key 'file'"}), 400
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "Empty file"}), 400

        content = file.read().decode('utf-8')
        reader = csv.DictReader(StringIO(content))
        required_cols = {'number', 'name'}
        if not required_cols.issubset(set([c.strip() for c in reader.fieldnames or []])):
            return jsonify({"error": "CSV must include at least 'number' and 'name' headers"}), 400

        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        created = 0
        errors = []
        batch_rows = []
        BATCH_SIZE = 50
        for idx, row in enumerate(reader):
            try:
                number = _normalize_phone((row.get('number') or '').strip())
                name = (row.get('name') or '').strip()
                email = (row.get('email') or '').strip()
                whatsapp_number = _normalize_phone((row.get('whatsapp_number') or number).strip())
                partner = (row.get('partner') or '').strip()
                if not name:
                    errors.append({"row": idx + 2, "error": "Missing name"})
                    continue
                if not number:
                    errors.append({"row": idx + 2, "error": "Missing number"})
                    continue
                if not _is_valid_phone(number):
                    errors.append({"row": idx + 2, "error": "Invalid number after normalization (need 10-15 digits)"})
                    continue
                if whatsapp_number and not _is_valid_phone(whatsapp_number):
                    errors.append({"row": idx + 2, "error": "Invalid whatsapp_number after normalization (need 10-15 digits)"})
                    continue
                # Already normalized to E.164 format with single + prefix
                number_e164 = number
                whatsapp_e164 = whatsapp_number if whatsapp_number else number_e164
                lead_uuid = str(uuid.uuid4())
                new_lead = [
                    lead_uuid,
                    number_e164,
                    whatsapp_e164,
                    name,
                    email,
                    'pending',
                    '0',
                    '',
                    'false',
                    'false',
                    '',
                    '',
                    '',
                    '',
                    '',
                    ''
                ]
                batch_rows.append(new_lead)
                # Flush in batches to reduce rate limits
                if len(batch_rows) >= BATCH_SIZE:
                    worksheet.append_rows(batch_rows, value_input_option='RAW')
                    created += len(batch_rows)
                    batch_rows = []
                # Write partner if provided
                if partner:
                    headers = worksheet.row_values(1)
                    if 'partner' not in headers:
                        worksheet.update_cell(1, len(headers) + 1, 'partner')
                        headers.append('partner')
                    partner_col = headers.index('partner') + 1
                    # Find row just appended
                    row_index_0 = get_sheets_manager().find_row_by_lead_uuid(lead_uuid)
                    if row_index_0 is not None:
                        worksheet.update_cell(row_index_0 + 2, partner_col, partner)
                
            except Exception as e:
                errors.append({"row": idx + 2, "error": str(e)})

        # Flush remaining rows
        if batch_rows:
            worksheet.append_rows(batch_rows, value_input_option='RAW')
            created += len(batch_rows)
            batch_rows = []

        # Invalidate leads cache so UI sees new rows immediately
        _leads_cache["data"] = None
        _leads_cache["ts"] = 0

        return jsonify({"success": True, "created": created, "errors": errors}), 200
    except Exception as e:
        logger.error(f"Error in bulk upload: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/bulk-call', methods=['POST'])
def bulk_call():
    """
    Initiate batch calling with automatic pacing.
    
    Body: { 
        lead_uuids?: [...],  # Optional: specific leads to call
        status?: [pending,missed,failed],  # Filter by status
        use_batch_worker?: true,  # Use batch worker (default: true)
        parallel_calls?: 5,  # Calls per batch (default: 5)
        interval_seconds?: 240  # Wait between batches in seconds (default: 240 = 4 min)
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        lead_uuids = data.get('lead_uuids') or []
        status_filter = set(data.get('status') or ['pending', 'missed', 'failed'])
        use_batch_worker = data.get('use_batch_worker', True)
        parallel_calls = int(data.get('parallel_calls', 5))
        interval_seconds = int(data.get('interval_seconds', 240))

        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        leads = worksheet.get_all_records()

        eligible = []
        if lead_uuids:
            # Pick by uuid
            uuid_set = set(lead_uuids)
            for i, lead in enumerate(leads):
                if lead.get('lead_uuid') in uuid_set and lead.get('call_status') in status_filter:
                    eligible.append({"row_index_0": i, "lead": lead})
        else:
            for i, lead in enumerate(leads):
                if lead.get('call_status') in status_filter:
                    eligible.append({"row_index_0": i, "lead": lead})

        if not eligible:
            return jsonify({"success": True, "message": "No eligible leads found", "total_eligible": 0}), 200

        # Use batch worker for automatic pacing (recommended for 10+ leads)
        if use_batch_worker:
            from src.batch_caller import get_batch_worker
            import uuid as uuid_lib
            
            job_id = str(uuid_lib.uuid4())
            assistant_id = os.getenv('VAPI_ASSISTANT_ID')
            phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID')
            
            if not assistant_id or not phone_number_id:
                return jsonify({"error": "Vapi configuration missing (VAPI_ASSISTANT_ID, VAPI_PHONE_NUMBER_ID)"}), 500
            
            worker = get_batch_worker()
            job = worker.start_job(
                job_id=job_id,
                leads=eligible,
                vapi_client=get_vapi_client(),
                sheets_manager=get_sheets_manager(),
                assistant_id=assistant_id,
                phone_number_id=phone_number_id,
                parallel_calls=parallel_calls,
                interval_seconds=interval_seconds
            )
            
            # Invalidate cache to force refresh
            _invalidate_leads_cache()
            
            # Calculate accurate estimated duration
            # Total batches = ceiling(total_leads / parallel_calls)
            # Time = (batches - 1) * interval + avg_call_duration
            total_batches = (len(eligible) + parallel_calls - 1) // parallel_calls
            estimated_seconds = (total_batches - 1) * interval_seconds + 180  # +3 min avg call time
            estimated_minutes = int(estimated_seconds / 60)
            
            return jsonify({
                "success": True,
                "batch_mode": True,
                "job_id": job_id,
                "total_eligible": len(eligible),
                "parallel_calls": parallel_calls,
                "interval_seconds": interval_seconds,
                "estimated_duration_minutes": estimated_minutes,
                "total_batches": total_batches
            }), 200
        
        # Legacy synchronous mode (not recommended for bulk, kept for compatibility)
        else:
            initiated = []
            errors = []
            assistant_id = os.getenv('VAPI_ASSISTANT_ID')
            phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID')

            for item in eligible[:25]:  # Limit to 25 for sync mode
                try:
                    row_index_0 = item['row_index_0']
                    lead = item['lead']
                    lead_uuid = lead.get('lead_uuid')
                    number = lead.get('number')
                    if not lead_uuid or not number:
                        errors.append({"lead_uuid": lead_uuid or '?', "error": "Missing uuid or number"})
                        continue
                    call_time = get_ist_timestamp()
                    result = get_vapi_client().initiate_outbound_call(
                        lead_data={"lead_uuid": lead_uuid, "number": number, "name": lead.get('name'), "email": lead.get('email')},
                        assistant_id=assistant_id,
                        phone_number_id=phone_number_id
                    )
                    if "error" in result:
                        errors.append({"lead_uuid": lead_uuid, "error": result["error"]})
                        continue
                    get_sheets_manager().update_lead_call_initiated(row_index_0, "initiated", call_time)
                    try:
                        vapi_call_id = result.get('id')
                        if vapi_call_id:
                            headers = worksheet.row_values(1)
                            if 'vapi_call_id' in headers:
                                col = headers.index('vapi_call_id') + 1
                                worksheet.update_cell(row_index_0 + 2, col, vapi_call_id)
                    except Exception:
                        pass
                    initiated.append({"lead_uuid": lead_uuid, "call_id": result.get('id'), "call_time": call_time})
                except Exception as e:
                    errors.append({"lead_uuid": lead.get('lead_uuid') or '?', "error": str(e)})

            _invalidate_leads_cache()
            return jsonify({"success": True, "batch_mode": False, "initiated": initiated, "errors": errors, "requested": len(eligible[:25])}), 200
            
    except Exception as e:
        logger.error(f"Error in bulk call: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/batch-call/status', methods=['GET'])
def get_batch_call_status():
    """Get status of active or specific batch calling job."""
    try:
        from src.batch_caller import get_batch_worker
        
        job_id = request.args.get('job_id')
        worker = get_batch_worker()
        
        if job_id:
            job = worker.get_job(job_id)
        else:
            job = worker.get_active_job()
        
        if not job:
            return jsonify({"status": "no_active_job"}), 404
        
        return jsonify(job.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting batch call status: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/batch-call/cancel', methods=['POST'])
def cancel_batch_call():
    """Cancel an active batch calling job."""
    try:
        from src.batch_caller import get_batch_worker
        
        data = request.get_json(silent=True) or {}
        job_id = data.get('job_id')
        
        if not job_id:
            return jsonify({"error": "job_id is required"}), 400
        
        worker = get_batch_worker()
        cancelled = worker.cancel_job(job_id)
        
        if cancelled:
            return jsonify({"success": True, "message": f"Job {job_id} cancelled"}), 200
        else:
            return jsonify({"error": "Job not found or already completed"}), 404
            
    except Exception as e:
        logger.error(f"Error cancelling batch call: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Email settings endpoints
@app.route('/api/settings/email', methods=['GET'])
def get_email_settings():
    try:
        data = _resolve_email_settings()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting email settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings/email', methods=['POST'])
def update_email_settings():
    try:
        data = request.get_json(silent=True) or {}
        # Defaults used if resetting
        default_subject = 'Missed Call Follow-Up Email'
        default_body = (
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

        if data.get('reset_defaults'):
            os.environ['EMAIL_SUBJECT'] = default_subject
            os.environ['EMAIL_TEMPLATE_BODY'] = default_body
        else:
            if 'subject' in data:
                os.environ['EMAIL_SUBJECT'] = data['subject'] or default_subject
            if 'body' in data:
                os.environ['EMAIL_TEMPLATE_BODY'] = data['body'] or default_body
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating email settings: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# WhatsApp settings endpoints (no dry-run toggle exposed)
@app.route('/api/settings/whatsapp', methods=['GET'])
def get_whatsapp_settings():
    try:
        data = {
            "enable_followup": os.getenv('WHATSAPP_ENABLE_FOLLOWUP', 'true').lower() == 'true',
            "enable_fallback": os.getenv('WHATSAPP_ENABLE_FALLBACK', 'true').lower() == 'true',
            "template_followup": os.getenv('WHATSAPP_TEMPLATE_FOLLOWUP') or "",
            "template_fallback": os.getenv('WHATSAPP_TEMPLATE_FALLBACK') or "",
            "language": os.getenv('WHATSAPP_LANGUAGE', 'en')
        }
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting WhatsApp settings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings/whatsapp', methods=['POST'])
def update_whatsapp_settings():
    try:
        data = request.get_json(silent=True) or {}
        # Update in-process env so changes take effect without restart
        if 'enable_followup' in data:
            os.environ['WHATSAPP_ENABLE_FOLLOWUP'] = 'true' if data['enable_followup'] else 'false'
        if 'enable_fallback' in data:
            os.environ['WHATSAPP_ENABLE_FALLBACK'] = 'true' if data['enable_fallback'] else 'false'
        if 'template_followup' in data:
            os.environ['WHATSAPP_TEMPLATE_FOLLOWUP'] = data['template_followup'] or ''
        if 'template_fallback' in data:
            os.environ['WHATSAPP_TEMPLATE_FALLBACK'] = data['template_fallback'] or ''
        if 'language' in data:
            os.environ['WHATSAPP_LANGUAGE'] = data['language'] or 'en'

        # Rebuild handler to apply new flags/templates
        global webhook_handler
        webhook_handler = None
        get_webhook_handler()

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating WhatsApp settings: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<lead_uuid>/whatsapp', methods=['POST'])
def send_manual_whatsapp(lead_uuid):
    """Send a manual WhatsApp template to a lead. Body: { template?: name, language?: code, params?: [] }"""
    try:
        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        row_index_0 = get_sheets_manager().find_row_by_lead_uuid(lead_uuid)
        if row_index_0 is None:
            return jsonify({"error": "Lead not found"}), 404
        headers = worksheet.row_values(1)
        row = worksheet.row_values(row_index_0 + 2)
        lead = dict(zip(headers, row))
        to_number = (lead.get('whatsapp_number') or lead.get('number') or '').strip()
        if not to_number:
            return jsonify({"error": "Lead has no whatsapp_number/number"}), 400

        data = request.get_json(silent=True) or {}
        template = data.get('template') or os.getenv('WHATSAPP_TEMPLATE_FOLLOWUP')
        language = data.get('language') or os.getenv('WHATSAPP_LANGUAGE', 'en')
        params = data.get('params') or [(lead.get('name') or 'there')]

        client = get_whatsapp_client()
        result = client.send_template(
            to_number_e164=to_number,
            template_name=template,
            language=language,
            body_parameters=params
        )
        if 'error' in result:
            return jsonify(result), 502
        # Mark whatsapp_sent
        get_sheets_manager().update_fallback_status(row_index_0, whatsapp_sent=True)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.error(f"Error sending manual WhatsApp: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<lead_uuid>/email', methods=['POST'])
def send_manual_email(lead_uuid):
    """Send a manual email to a lead using current template settings."""
    try:
        # Prefer cached lead data to avoid read quota
        lead = None
        cached_details = _details_cache.get(lead_uuid)
        if cached_details and cached_details.get("data"):
            lead = cached_details["data"]
        if not lead and _leads_cache.get("data"):
            for candidate in _leads_cache["data"] or []:
                if candidate.get('lead_uuid') == lead_uuid:
                    lead = candidate
                    break

        row_index_0 = None
        to_email = ''
        if lead:
            to_email = (lead.get('email') or '').strip()
        # Fallback to minimal sheet lookups only if absolutely necessary
        if not to_email:
            try:
                row_index_0 = get_sheets_manager().find_row_by_lead_uuid(lead_uuid)
                if row_index_0 is None:
                    return jsonify({"error": "Lead not found"}), 404
                # Avoid fetching entire sheet; just pull the email cell via headers mapping if available
                worksheet = get_sheets_manager().sheet.worksheet("Leads")
                headers = worksheet.row_values(1)
                row = worksheet.row_values(row_index_0 + 2)
                lead = dict(zip(headers, row))
                to_email = (lead.get('email') or '').strip()
            except Exception:
                # If quota errors prevent reads and we still don't have an email, bail gracefully
                logger.error("Unable to resolve lead email due to Sheets read limits", exc_info=True)
                return jsonify({"error": "Unable to resolve lead email (Sheets quota). Try again shortly."}), 503
        if not to_email:
            return jsonify({"error": "Lead has no email"}), 400

        data = request.get_json(silent=True) or {}
        # Always prefer resolved settings unless explicit overrides are passed in body
        settings = _resolve_email_settings()
        subject = data.get('subject') or settings["subject"]
        template_body = data.get('body') or settings["body"]
        body_text = template_body.format(name=(lead.get('name') if lead else None) or 'there')

        tagged_subject = f"{subject} [Lead:{lead_uuid}]"
        em_res = get_email_client().send(
            to_email=to_email,
            subject=tagged_subject,
            body_text=body_text,
            extra_headers={
                'X-Lead-UUID': lead_uuid,
                'References': (lead.get('vapi_call_id') if lead else '') or ''
            }
        )
        if 'error' in em_res:
            return jsonify(em_res), 502

        # Mark email_sent and log conversation
        try:
            if row_index_0 is None:
                try:
                    row_index_0 = get_sheets_manager().find_row_by_lead_uuid(lead_uuid)
                except Exception:
                    row_index_0 = None
            if row_index_0 is not None:
                get_sheets_manager().update_fallback_status(row_index_0, email_sent=True)
            timestamp_now = get_ist_timestamp()
            # Attempt to persist to Sheets
            try:
                get_sheets_manager().log_conversation(
                    lead_uuid=lead_uuid,
                    channel='email',
                    direction='out',
                    timestamp=timestamp_now,
                    subject=tagged_subject,
                    content=body_text,
                    summary='',
                    metadata=json.dumps({"dry_run": em_res.get('dry_run', False)}),
                    message_id=em_res.get('id', ''),
                    status='sent'
                )
            except Exception as log_err:
                logger.warning(f"Failed to write conversation to Sheets, will still update cache: {log_err}")
            # Update in-memory details cache so UI reflects immediately
            conv_entry = {
                "lead_uuid": lead_uuid,
                "channel": "email",
                "direction": "out",
                "timestamp": timestamp_now,
                "subject": tagged_subject,
                "content": body_text,
                "summary": "",
                "metadata": json.dumps({"dry_run": em_res.get('dry_run', False)}),
                "message_id": em_res.get('id', ''),
                "status": "sent"
            }
            cached = _details_cache.get(lead_uuid)
            if cached and cached.get("data"):
                data_obj = cached["data"]
                # Ensure conversations array exists
                if not isinstance(data_obj.get("conversations"), list):
                    data_obj["conversations"] = []
                data_obj["conversations"].append(conv_entry)
                # mark email_sent in cached lead too
                data_obj["email_sent"] = 'true'
                cached["ts"] = cached.get("ts") or 0  # keep ts as is
                _details_cache[lead_uuid] = cached
            # Also update the leads cache row if present
            if _leads_cache.get("data"):
                for l in _leads_cache["data"]:
                    if l.get('lead_uuid') == lead_uuid:
                        l['email_sent'] = 'true'
                        break
        except Exception:
            pass

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error sending manual email: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy"})

@app.route('/api/jobs', methods=['GET'])
def get_job_status():
    """Get status of background jobs."""
    try:
        from src.scheduler import get_scheduler
        scheduler = get_scheduler()
        
        if not scheduler or not scheduler.running:
            return jsonify({"error": "Scheduler not running"}), 503
        
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "pending": job.pending
            })
        
        return jsonify({
            "scheduler_running": scheduler.running,
            "jobs": jobs,
            "job_count": len(jobs)
        })
    except Exception as e:
        logger.error(f"Error getting job status: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/jobs/<job_id>/trigger', methods=['POST'])
def trigger_job_manually(job_id):
    """Manually trigger a specific job (for testing)."""
    try:
        from src.scheduler import get_scheduler
        scheduler = get_scheduler()
        
        if not scheduler or not scheduler.running:
            return jsonify({"error": "Scheduler not running"}), 503
        
        job = scheduler.get_job(job_id)
        if not job:
            return jsonify({"error": f"Job '{job_id}' not found"}), 404
        
        # Trigger the job immediately
        job.modify(next_run_time=get_ist_now())
        
        return jsonify({
            "success": True,
            "message": f"Job '{job_id}' triggered successfully",
            "job_id": job_id
        })
    except Exception as e:
        logger.error(f"Error triggering job: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/schedule-bulk-calls', methods=['POST'])
def schedule_bulk_calls_endpoint():
    """Schedule bulk calls to multiple leads at a specific time."""
    try:
        data = request.json
        
        # Validate input
        lead_uuids = data.get('lead_uuids', [])
        start_time_str = data.get('start_time')
        parallel_calls = int(data.get('parallel_calls', 5))
        call_interval = int(data.get('call_interval', 60))
        
        if not lead_uuids:
            return jsonify({"error": "No leads selected"}), 400
        
        if not start_time_str:
            return jsonify({"error": "Start time not provided"}), 400
        
        # Parse start time
        from src.utils import parse_ist_timestamp, get_ist_now
        start_time = parse_ist_timestamp(start_time_str)
        
        if start_time is None:
            return jsonify({"error": "Invalid start time format"}), 400
        
        # Validate start time is in future
        if start_time < get_ist_now():
            return jsonify({"error": "Start time must be in the future"}), 400
        
        # Validate parallel_calls
        if parallel_calls < 1 or parallel_calls > 20:
            return jsonify({"error": "Parallel calls must be between 1 and 20"}), 400
        
        # Schedule the bulk calls
        from src.scheduler import schedule_bulk_calls
        result = schedule_bulk_calls(lead_uuids, start_time, parallel_calls, call_interval)
        
        if result.get('error'):
            return jsonify(result), 500
        
        logger.info(f"✅ Scheduled bulk calls: {len(lead_uuids)} leads at {start_time}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error scheduling bulk calls: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/scheduled-bulk-calls', methods=['GET'])
def get_scheduled_bulk_calls_endpoint():
    """Get all scheduled bulk call jobs."""
    try:
        from src.scheduler import get_scheduled_bulk_calls
        bulk_jobs = get_scheduled_bulk_calls()
        
        return jsonify({
            "success": True,
            "scheduled_batches": bulk_jobs,
            "total_batches": len(bulk_jobs)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting scheduled bulk calls: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/cancel-bulk-schedule', methods=['POST'])
def cancel_bulk_schedule_endpoint():
    """Cancel scheduled bulk call jobs."""
    try:
        data = request.json
        job_id_prefix = data.get('job_id_prefix', 'bulk_call_batch_')
        
        from src.scheduler import cancel_bulk_schedule
        result = cancel_bulk_schedule(job_id_prefix)
        
        if result.get('error'):
            return jsonify(result), 500
        
        logger.info(f"✅ Cancelled bulk schedule: {result.get('cancelled_count')} jobs")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error cancelling bulk schedule: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False)