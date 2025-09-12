import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, url_for
import csv
from io import StringIO
from dotenv import load_dotenv
import uuid
from src.sheets_manager import SheetsManager
from src.vapi_client import VapiClient
from src.retry_manager import RetryManager
from src.webhook_handler import WebhookHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize components
sheets_manager = SheetsManager(
    credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
    sheet_id=os.getenv('LEADS_SHEET_ID')
)

# Force default retry intervals to 2, 4, 6 minutes (stored internally as hours)
default_retry_intervals_hours = [2/60.0, 4/60.0, 6/60.0]
retry_manager = RetryManager(
    max_retries=int(os.getenv('MAX_RETRY_COUNT', '3')),
    retry_intervals=default_retry_intervals_hours
)

vapi_client = VapiClient(api_key=os.getenv('VAPI_API_KEY'))

webhook_handler = WebhookHandler(
    sheets_manager=sheets_manager,
    retry_manager=retry_manager
)

# Create Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')

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
        # Get the worksheet
        worksheet = sheets_manager.sheet.worksheet("Leads")
        
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
        
        return jsonify(leads)
    except Exception as e:
        logger.error(f"Error getting leads: {e}", exc_info=True)
        return jsonify([])  # Return empty array instead of error

@app.route('/api/leads', methods=['POST'])
def add_lead():
    """Add a new lead to Google Sheets."""
    try:
        lead_data = request.json
        
        # Validate required fields
        if not lead_data.get('number') or not lead_data.get('name'):
            return jsonify({"error": "Name and phone number are required"}), 400
        
        # Get the worksheet
        worksheet = sheets_manager.sheet.worksheet("Leads")
        
        # Prepare the new lead row with stable UUID
        lead_uuid = str(uuid.uuid4())
        
        # Headers must match initialize_sheet schema order
        new_lead = [
            lead_uuid,                          # lead_uuid
            lead_data.get('number', ''),           # number
            lead_data.get('number', ''),           # whatsapp_number (same as number by default)
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
        return jsonify({"success": True, "message": "Lead added successfully", "lead_uuid": lead_uuid})
    except Exception as e:
        logger.error(f"Error adding lead: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<lead_uuid>/call', methods=['POST'])
def initiate_call(lead_uuid):
    """Initiate a call to a specific lead."""
    try:
        # Locate row by lead_uuid
        worksheet = sheets_manager.sheet.worksheet("Leads")
        row_index_0 = sheets_manager.find_row_by_lead_uuid(lead_uuid)
        if row_index_0 is None:
            return jsonify({"error": "Lead not found"}), 404
        leads = worksheet.get_all_records()
        lead = leads[row_index_0]
        
        # Check if lead status allows calling (pending or missed/failed with retry)
        valid_statuses = ['pending', 'missed', 'failed']
        if lead.get('call_status') not in valid_statuses:
            return jsonify({"error": f"Cannot call lead with status: {lead.get('call_status')}"}), 400
        
        # Prepare lead data
        lead_data = {
            "lead_uuid": lead_uuid,
            "number": lead.get('number'),
            "name": lead.get('name'),
            "email": lead.get('email')
        }
        
        # Get Vapi assistant ID and phone number ID
        assistant_id = os.getenv('VAPI_ASSISTANT_ID')
        phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID')
        
        # Record call initiation time
        call_time = datetime.now().isoformat()
        
        # Initiate call
        call_result = vapi_client.initiate_outbound_call(
            lead_data=lead_data,
            assistant_id=assistant_id,
            phone_number_id=phone_number_id
        )
        
        if "error" in call_result:
            return jsonify({"error": call_result["error"]}), 500
        
        # Update lead status and call time
        sheets_manager.update_lead_call_initiated(row_index_0, "initiated", call_time)
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
        deleted = sheets_manager.delete_lead_by_uuid(lead_uuid)
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
        
        result = webhook_handler.handle_event(event_data)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<lead_uuid>/details', methods=['GET'])
def get_lead_details(lead_uuid):
    """Get detailed information for a specific lead."""
    try:
        # Get the worksheet
        worksheet = sheets_manager.sheet.worksheet("Leads")
        
        # Check if sheet is empty or has no data rows
        values = worksheet.get_values()
        if len(values) <= 1:  # Only header row or empty
            logger.info("Sheet is empty or has only headers")
            return jsonify({"error": "No leads found in sheet"}), 404
            
        # Get all records
        row_index_0 = sheets_manager.find_row_by_lead_uuid(lead_uuid)
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
            call_history = sheets_manager.get_call_history(row_index_0)
            lead['call_history'] = call_history
        except Exception as e:
            logger.warning(f"Error getting call history: {e}")
            lead['call_history'] = []
        
        return jsonify(lead)
    except Exception as e:
        logger.error(f"Error getting lead details: {e}", exc_info=True)
        return jsonify({"error": "Failed to get lead details"}), 500

@app.route('/api/retry-config', methods=['GET'])
def get_retry_config():
    """Get the current retry configuration."""
    try:
        config = {
            "max_retries": retry_manager.max_retries,
            "retry_intervals": retry_manager.retry_intervals
        }
        return jsonify(config)
    except Exception as e:
        logger.error(f"Error getting retry config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/retry-config', methods=['POST'])
def update_retry_config():
    """Update the retry configuration."""
    try:
        # Ignore incoming payload for now; enforce static 2/4/6 minutes and 3 attempts
        retry_manager.max_retries = 3
        retry_manager.retry_intervals = [2/60.0, 4/60.0, 6/60.0]
        os.environ['MAX_RETRY_COUNT'] = '3'
        os.environ['RETRY_INTERVALS'] = ','.join(map(str, retry_manager.retry_intervals))
        
        return jsonify({
            "success": True,
            "message": "Retry configuration updated successfully",
            "config": {
                "max_retries": retry_manager.max_retries,
                "retry_intervals": retry_manager.retry_intervals
            }
        })
    except Exception as e:
        logger.error(f"Error updating retry config: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/bulk-upload', methods=['POST'])
def bulk_upload_leads():
    """Upload leads via CSV (columns: number,name,email,whatsapp_number(optional))."""
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

        worksheet = sheets_manager.sheet.worksheet("Leads")
        created = 0
        errors = []
        for idx, row in enumerate(reader):
            try:
                number = (row.get('number') or '').strip()
                name = (row.get('name') or '').strip()
                email = (row.get('email') or '').strip()
                whatsapp_number = (row.get('whatsapp_number') or number).strip()
                if not number or not name:
                    errors.append({"row": idx + 2, "error": "Missing number or name"})
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

        worksheet = sheets_manager.sheet.worksheet("Leads")
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
                result = vapi_client.initiate_outbound_call(
                    lead_data={"lead_uuid": lead_uuid, "number": number, "name": lead.get('name'), "email": lead.get('email')},
                    assistant_id=assistant_id,
                    phone_number_id=phone_number_id
                )
                if "error" in result:
                    errors.append({"lead_uuid": lead_uuid, "error": result["error"]})
                    continue
                # update status and vapi id
                sheets_manager.update_lead_call_initiated(row_index_0, "initiated", call_time)
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

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False)