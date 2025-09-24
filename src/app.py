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
_CACHE_TTL_SECONDS = 15


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
            whatsapp_enable_fallback=os.getenv('WHATSAPP_ENABLE_FALLBACK', 'true').lower() == 'true'
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
    """Return digits-only phone string. Removes spaces and non-digits."""
    if not raw:
        return ''
    return re.sub(r"\D+", "", str(raw))

def _is_valid_phone(digits_only: str) -> bool:
    """Basic validation: 10-15 digits (international)."""
    try:
        n = len(digits_only or '')
        return 10 <= n <= 15
    except Exception:
        return False

# Dashboard routes
@app.route('/')
def index():
    """Render the dashboard homepage."""
    return render_template('index.html')

# API routes
@app.route('/api/leads', methods=['GET'])
def get_leads():
    """Get all leads from Google Sheets."""
    try:
        # Serve from cache if fresh
        from time import time
        now = time()
        if _leads_cache["data"] is not None and (now - _leads_cache["ts"]) < _CACHE_TTL_SECONDS:
            return jsonify(_leads_cache["data"]) 
        # Get the worksheet
        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        
        # Check if sheet is empty or has no data rows
        values = worksheet.get_values()
        if len(values) <= 1:  # Only header row or empty
            logger.info("Sheet is empty or has only headers")
            return jsonify([])
            
        # Get all records
        leads = worksheet.get_all_records()
        
        # Add ID to each lead (row index for simplicity)
        for idx, lead in enumerate(leads):
            lead['id'] = str(idx)
        
        _leads_cache["data"] = leads
        _leads_cache["ts"] = now
        return jsonify(leads)
    except Exception as e:
        # Serve stale cache if available to avoid blank dashboard during quota spikes
        if _leads_cache["data"] is not None:
            logger.warning(f"Sheets read failed, serving cached leads: {e}")
            return jsonify(_leads_cache["data"]) 
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
        
        # Headers must match initialize_sheet schema order
        number_norm = _normalize_phone(lead_data.get('number', ''))
        whatsapp_norm = _normalize_phone(lead_data.get('number', ''))
        if not _is_valid_phone(number_norm):
            return jsonify({"error": "Invalid phone number. Please enter 10-15 digits."}), 400
        new_lead = [
            lead_uuid,                          # lead_uuid
            number_norm,                            # number
            whatsapp_norm,                          # whatsapp_number (same as number by default)
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
        
        # Record call initiation time
        call_time = datetime.now().isoformat()
        
        # Initiate call
        call_result = get_vapi_client().initiate_outbound_call(
            lead_data=lead_data,
            assistant_id=assistant_id,
            phone_number_id=phone_number_id
        )
        
        if "error" in call_result:
            return jsonify({"error": call_result["error"]}), 500
        
        # Update lead status and call time
        get_sheets_manager().update_lead_call_initiated(row_index_0, "initiated", call_time)
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
                lead_uuid = str(uuid.uuid4())
                new_lead = [
                    lead_uuid,
                    number,
                    whatsapp_number or number,
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
                worksheet.append_row(new_lead)
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
                created += 1
            except Exception as e:
                errors.append({"row": idx + 2, "error": str(e)})

        return jsonify({"success": True, "created": created, "errors": errors}), 200
    except Exception as e:
        logger.error(f"Error in bulk upload: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/bulk-call', methods=['POST'])
def bulk_call():
    """Initiate calls for multiple leads. Body: { lead_uuids?: [...], status?: [pending,missed,failed], limit?: n }"""
    try:
        data = request.get_json(silent=True) or {}
        lead_uuids = data.get('lead_uuids') or []
        status_filter = set(data.get('status') or ['pending', 'missed', 'failed'])
        limit = int(data.get('limit') or 50)

        worksheet = get_sheets_manager().sheet.worksheet("Leads")
        leads = worksheet.get_all_records()

        eligible = []
        if lead_uuids:
            # Pick by uuid
            uuid_set = set(lead_uuids)
            for i, lead in enumerate(leads):
                if lead.get('lead_uuid') in uuid_set and lead.get('call_status') in status_filter:
                    eligible.append((i, lead))
        else:
            for i, lead in enumerate(leads):
                if lead.get('call_status') in status_filter:
                    eligible.append((i, lead))

        initiated = []
        errors = []
        assistant_id = os.getenv('VAPI_ASSISTANT_ID')
        phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID')

        for i, (row_index_0, lead) in enumerate(eligible[:limit]):
            try:
                lead_uuid = lead.get('lead_uuid')
                number = lead.get('number')
                if not lead_uuid or not number:
                    errors.append({"lead_uuid": lead_uuid or '?', "error": "Missing uuid or number"})
                    continue
                call_time = datetime.now().isoformat()
                result = get_vapi_client().initiate_outbound_call(
                    lead_data={"lead_uuid": lead_uuid, "number": number, "name": lead.get('name'), "email": lead.get('email')},
                    assistant_id=assistant_id,
                    phone_number_id=phone_number_id
                )
                if "error" in result:
                    errors.append({"lead_uuid": lead_uuid, "error": result["error"]})
                    continue
                # update status and vapi id
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

        return jsonify({"success": True, "initiated": initiated, "errors": errors, "requested": len(eligible[:limit])}), 200
    except Exception as e:
        logger.error(f"Error in bulk call: {e}", exc_info=True)
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
            timestamp_now = datetime.now().isoformat()
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False)