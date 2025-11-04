import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from src.utils import get_ist_timestamp, get_ist_now
import uuid

class SheetsManager:
    def __init__(self, credentials_file, sheet_id):
        """
        Initialize the SheetsManager with Google Sheets credentials and sheet ID.
        
        Args:
            credentials_file (str): Path to the Google Sheets credentials JSON file
            sheet_id (str): ID of the Google Sheet to use
        """
        self.credentials_file = credentials_file
        self.sheet_id = sheet_id
        self.client = self._authenticate()
        self.sheet = self._get_sheet()
        # Simple headers cache per worksheet name to reduce header reads
        self._headers_cache = {}
        # Worksheet object cache to prevent repeated metadata fetches (429 rate limit)
        self._worksheet_cache = {}
    
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(
            self.credentials_file, 
            scopes=scopes
        )
        
        return gspread.authorize(credentials)
    
    def _get_sheet(self):
        """Get the specific Google Sheet."""
        return self.client.open_by_key(self.sheet_id)

    def _get_worksheet(self, worksheet_name: str):
        """Return cached worksheet object to prevent repeated metadata fetches (rate limit optimization)."""
        if worksheet_name in self._worksheet_cache:
            return self._worksheet_cache[worksheet_name]
        ws = self.sheet.worksheet(worksheet_name)
        self._worksheet_cache[worksheet_name] = ws
        return ws
    
    def _get_headers(self, worksheet_name: str):
        """Return cached headers for a worksheet, fetching once when missing."""
        if worksheet_name in self._headers_cache and isinstance(self._headers_cache[worksheet_name], list):
            return self._headers_cache[worksheet_name]
        ws = self._get_worksheet(worksheet_name)
        headers = ws.row_values(1)
        self._headers_cache[worksheet_name] = headers
        return headers

    def _invalidate_headers(self, worksheet_name: str):
        self._headers_cache.pop(worksheet_name, None)
    
    def get_pending_leads(self, only_retry=False):
        """
        Get leads that are pending calls or due for retry.
        
        Args:
            only_retry (bool): If True, only return leads due for retry, not new pending leads
            
        Returns:
            list: List of lead dictionaries with their data
        """
        try:
            worksheet = self._get_worksheet("Leads")
            # Check if sheet is empty or has no data rows (cheap range)
            values = worksheet.get_values('A1:A2')
            if len(values) <= 1:  # Only header row or empty
                print("Sheet is empty or has only headers")
                return []
                
            all_leads = worksheet.get_all_records()
            if not all_leads:
                print("No leads found in sheet")
                return []
            
            now_dt = get_ist_now()
            
            # Filter for leads that are pending or due for retry
            pending_leads = []
            for index, lead in enumerate(all_leads):
                # Add row index as ID
                lead['id'] = str(index)
                
                # New leads (pending) - only if not only_retry mode
                if lead.get('call_status') == 'pending' and not only_retry:
                    pending_leads.append(lead)
                
                # Retry leads (missed/failed) that are due for retry
                elif lead.get('call_status') in ['missed', 'failed']:
                    next_retry = lead.get('next_retry_time')
                    if next_retry:
                        try:
                            next_dt = datetime.fromisoformat(next_retry)
                            if next_dt <= now_dt:
                                pending_leads.append(lead)
                        except Exception:
                            # If invalid timestamp, consider it due to avoid getting stuck
                            pending_leads.append(lead)
            
            return pending_leads
            
        except Exception as e:
            print(f"Error getting pending leads: {e}")
            return []
    
    def update_lead_status(self, row_index, status):
        """
        Update the status of a lead.
        
        Args:
            row_index (int): Row index in the sheet (0-based)
            status (str): New status (pending, initiated, answered, missed, failed, completed)
        """
        worksheet = self.sheet.worksheet("Leads")
        headers = self._get_headers("Leads")
        status_col_idx = headers.index('call_status') + 1
        sheet_row = row_index + 2
        # Single-call update via update_cells
        worksheet.update_cells([gspread.Cell(row=sheet_row, col=status_col_idx, value=status)])
        print(f"Updated lead status at row {row_index + 2} to: {status}")

    def update_last_ended_reason(self, row_index: int, reason: str):
        """Update the last_ended_reason column, creating it if missing."""
        worksheet = self.sheet.worksheet("Leads")
        headers = self._get_headers("Leads")
        sheet_row = row_index + 2
        if 'last_ended_reason' not in headers:
            worksheet.update_cell(1, len(headers) + 1, 'last_ended_reason')
            headers = headers + ['last_ended_reason']
            self._headers_cache["Leads"] = headers
        col_idx = headers.index('last_ended_reason') + 1
        worksheet.update_cells([gspread.Cell(row=sheet_row, col=col_idx, value=reason or '')])
        print(f"Updated last_ended_reason at row {sheet_row} -> {reason}")

    def update_transcript(self, row_index: int, transcript_text: str):
        """Update transcript text column, creating it if missing."""
        worksheet = self.sheet.worksheet("Leads")
        headers = self._get_headers("Leads")
        sheet_row = row_index + 2
        if 'transcript' not in headers:
            worksheet.update_cell(1, len(headers) + 1, 'transcript')
            headers = headers + ['transcript']
            self._headers_cache["Leads"] = headers
        col_idx = headers.index('transcript') + 1
        worksheet.update_cells([gspread.Cell(row=sheet_row, col=col_idx, value=transcript_text or '')])
        print(f"Updated transcript at row {sheet_row} (len={len(transcript_text or '')})")
    
    def update_lead_retry(self, row_index, retry_count, next_retry_time):
        """
        Update retry information for a lead.
        
        Args:
            row_index (int): Row index in the sheet (0-based)
            retry_count (int): Updated retry count
            next_retry_time (str): ISO format timestamp for next retry
        """
        worksheet = self.sheet.worksheet("Leads")
        headers = self._get_headers("Leads")
        
        # Get column indices
        retry_count_col_idx = headers.index('retry_count') + 1
        next_retry_col_idx = headers.index('next_retry_time') + 1
        
        # Row index conversion (0-based to 1-based + header row)
        sheet_row = row_index + 2
        
        # Update both cells
        updates = [
            gspread.Cell(row=sheet_row, col=retry_count_col_idx, value=str(retry_count)),
            gspread.Cell(row=sheet_row, col=next_retry_col_idx, value=next_retry_time)
        ]
        worksheet.update_cells(updates)
        print(f"Updated retry info at row {sheet_row}: count={retry_count}, next={next_retry_time}")
    
    def update_ai_analysis(self, row_index, summary, success_status, structured_data):
        """
        Update AI analysis fields for a completed call.
        
        Args:
            row_index (int): Row index in the sheet (0-based)
            summary (str): AI-generated call summary
            success_status (str): Qualification status
            structured_data (str): JSON string of structured data
        """
        worksheet = self.sheet.worksheet("Leads")
        headers = self._get_headers("Leads")
        
        # Row index conversion (0-based to 1-based + header row)
        sheet_row = row_index + 2
        
        # Create batched cell updates
        cell_updates = []
        
        # Find column indices
        for field, value in [
            ('summary', summary),
            ('success_status', success_status),
            ('structured_data', structured_data)
        ]:
            try:
                col_idx = headers.index(field) + 1
                cell_updates.append(gspread.Cell(row=sheet_row, col=col_idx, value=value))
            except ValueError:
                print(f"Warning: Column '{field}' not found in sheet")
        
        # Update the cells in batches
        if cell_updates:
            worksheet.update_cells(cell_updates)
            print(f"Updated AI analysis for row {sheet_row}")
        else:
            print("No fields to update")
    
    def update_fallback_status(self, row_index, whatsapp_sent=None, email_sent=None):
        """
        Update fallback communication status.
        
        Args:
            row_index (int): Row index in the sheet (0-based)
            whatsapp_sent (bool): Whether WhatsApp message was sent
            email_sent (bool): Whether email was sent
        """
        worksheet = self.sheet.worksheet("Leads")
        headers = self._get_headers("Leads")
        sheet_row = row_index + 2
        updates = []
        if whatsapp_sent is not None:
            whatsapp_col_idx = headers.index('whatsapp_sent') + 1
            updates.append(gspread.Cell(row=sheet_row, col=whatsapp_col_idx, value=str(whatsapp_sent).lower()))
        if email_sent is not None:
            email_col_idx = headers.index('email_sent') + 1
            updates.append(gspread.Cell(row=sheet_row, col=email_col_idx, value=str(email_sent).lower()))
        if updates:
            worksheet.update_cells(updates)

    def find_row_by_lead_uuid(self, lead_uuid):
        """
        Find the 0-based row index for a given lead_uuid. Returns None if not found.
        """
        worksheet = self.sheet.worksheet("Leads")
        headers = self._get_headers("Leads")
        if 'lead_uuid' not in headers:
            return None
        uuid_col_idx_1 = headers.index('lead_uuid') + 1
        # Read only the UUID column to minimize read units
        uuids = worksheet.col_values(uuid_col_idx_1)
        # uuids[0] is header, data starts at index 1
        for i in range(1, len(uuids)):
            if uuids[i] == lead_uuid:
                return i - 1
        return None

    def delete_lead_by_uuid(self, lead_uuid):
        """
        Delete a lead row identified by lead_uuid. Returns True if deleted, False if not found.
        """
        worksheet = self.sheet.worksheet("Leads")
        row_index_0 = self.find_row_by_lead_uuid(lead_uuid)
        if row_index_0 is None:
            return False
        # Sheet is 1-based with header, so delete row_index_0 + 2
        worksheet.delete_rows(row_index_0 + 2)
        return True
    
    def update_lead_call_initiated(self, row_index, status, call_time, vapi_call_id=None):
        """
        Update lead status and record call initiation time.
        
        Args:
            row_index (int): Row index in the sheet (0-based)
            status (str): New status (typically 'initiated')
            call_time (str): ISO format timestamp of call initiation
        """
        worksheet = self.sheet.worksheet("Leads")
        headers = self._get_headers("Leads")
        sheet_row = row_index + 2
        
        updates = []
        # Update status
        status_col_idx = headers.index('call_status') + 1
        updates.append(gspread.Cell(row=sheet_row, col=status_col_idx, value=status))
        
        # Ensure columns exist
        if 'last_call_time' not in headers:
            worksheet.update_cell(1, len(headers) + 1, 'last_call_time')
            headers = headers + ['last_call_time']
            self._headers_cache["Leads"] = headers
        if 'vapi_call_id' not in headers:
            worksheet.update_cell(1, len(headers) + 1, 'vapi_call_id')
            headers = headers + ['vapi_call_id']
            self._headers_cache["Leads"] = headers

        call_time_col_idx = headers.index('last_call_time') + 1
        updates.append(gspread.Cell(row=sheet_row, col=call_time_col_idx, value=call_time))
        if vapi_call_id:
            vapi_col_idx = headers.index('vapi_call_id') + 1
            updates.append(gspread.Cell(row=sheet_row, col=vapi_col_idx, value=vapi_call_id))
        if updates:
            worksheet.update_cells(updates)
        
        print(f"Updated lead status to {status} and recorded call time at row {sheet_row}")
    
    def get_call_history(self, row_index):
        """
        Get call history for a specific lead.
        This is a placeholder for a more robust call history implementation.
        In a production system, call history would likely be stored in a separate table/sheet.
        
        Args:
            row_index (int): Row index in the sheet (0-based)
            
        Returns:
            list: List of call history entries
        """
        worksheet = self.sheet.worksheet("Leads")
        lead_row = worksheet.row_values(row_index + 2)  # +2 for 0-based index and header row
        headers = self._get_headers("Leads")
        
        # Create a dictionary of the lead data
        lead_data = dict(zip(headers, lead_row))
        
        # Extract relevant call information
        call_history = []
        
        # If we have a last call time, create a history entry
        if 'last_call_time' in lead_data and lead_data['last_call_time']:
            history_entry = {
                "time": lead_data['last_call_time'],
                "status": lead_data['call_status'],
                "retry_count": lead_data.get('retry_count', '0')
            }
            # Include last_ended_reason if available
            if lead_data.get('last_ended_reason'):
                history_entry["ended_reason"] = lead_data['last_ended_reason']
            # Add summary if available
            if lead_data.get('summary'):
                history_entry["summary"] = lead_data['summary']
            # Add success status if available
            if lead_data.get('success_status'):
                history_entry["success_status"] = lead_data['success_status']
            call_history.append(history_entry)
        
        return call_history

    # Conversations sheet helpers
    def _get_or_create_conversations_sheet(self):
        try:
            return self._get_worksheet("Conversations")
        except gspread.exceptions.WorksheetNotFound:
            ws = self.sheet.add_worksheet(title="Conversations", rows=1000, cols=12)
            ws.update('A1:L1', [[
                'lead_uuid','timestamp','channel','direction','subject','content','summary','metadata','message_id','status','agent_id','attachment'
            ]])
            return ws

    def log_conversation(self, lead_uuid: str, channel: str, direction: str, timestamp: str,
                         subject: str = '', content: str = '', summary: str = '', metadata: str = '',
                         message_id: str = '', status: str = '', agent_id: str = '', attachment: str = ''):
        ws = self._get_or_create_conversations_sheet()
        row = [lead_uuid, timestamp, channel, direction, subject, content, summary, metadata, message_id, status, agent_id, attachment]
        ws.append_row(row)

    def get_conversations_by_lead(self, lead_uuid: str):
        ws = self._get_or_create_conversations_sheet()
        values = ws.get_all_values()
        if not values:
            return []
        headers = values[0]
        items = []
        for r in values[1:]:
            if len(r) > 0 and r[0] == lead_uuid:
                items.append(dict(zip(headers, r)))
        return items
    
    def update_retry_config(self, max_retries, retry_intervals):
        """
        Update retry configuration in a settings worksheet.
        Creates the worksheet if it doesn't exist.
        
        Args:
            max_retries (int): Maximum number of retries
            retry_intervals (list): List of hours between retries
        """
        # Check if Settings worksheet exists, create if not
        try:
            settings_sheet = self._get_worksheet("Settings")
        except gspread.exceptions.WorksheetNotFound:
            settings_sheet = self.sheet.add_worksheet(title="Settings", rows=10, cols=5)
            settings_sheet.update('A1:B1', [['Setting', 'Value']])
            settings_sheet.update('A2:A3', [['max_retries'], ['retry_intervals']])
        
        # Update settings
        settings_sheet.update('B2', str(max_retries))
        settings_sheet.update('B3', json.dumps(retry_intervals))
        
        print(f"Updated retry configuration: max_retries={max_retries}, intervals={retry_intervals}")
        
    def get_retry_config(self):
        """
        Get retry configuration from Settings worksheet.
        Returns default values if Settings worksheet doesn't exist.
        
        Returns:
            dict: Retry configuration with max_retries and retry_intervals
        """
        try:
            settings_sheet = self._get_worksheet("Settings")
            settings_data = settings_sheet.get_all_records()
            
            config = {}
            for row in settings_data:
                if row['Setting'] == 'max_retries':
                    config['max_retries'] = int(row['Value'])
                elif row['Setting'] == 'retry_intervals':
                    config['retry_intervals'] = json.loads(row['Value'])
            
            # If we got partial data, fill in defaults
            if 'max_retries' not in config:
                config['max_retries'] = 3
            if 'retry_intervals' not in config:
                config['retry_intervals'] = [1, 4, 24]
                
            return config
            
        except gspread.exceptions.WorksheetNotFound:
            # Return default values
            return {
                'max_retries': 3,
                'retry_intervals': [1, 4, 24]
            }

    def update_lead_fields(self, row_index: int, fields: dict):
        """
        Update multiple named fields for a given lead row in a single API call.

        Args:
            row_index (int): 0-based data row index
            fields (dict): mapping of header name -> value
        """
        if not fields:
            return
        ws = self._get_worksheet("Leads")
        headers = self._get_headers("Leads")
        sheet_row = row_index + 2
        updates = []
        for name, value in fields.items():
            if name not in headers:
                # If trying to write to a new column, add it to header row first
                ws.update_cell(1, len(headers) + 1, name)
                headers = headers + [name]
                self._headers_cache["Leads"] = headers
            col_idx = headers.index(name) + 1
            updates.append(gspread.Cell(row=sheet_row, col=col_idx, value=value))
        if updates:
            ws.update_cells(updates)