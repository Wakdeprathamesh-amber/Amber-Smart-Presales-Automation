import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_sheet():
    """
    Initialize a Google Sheet with the required structure for lead tracking.
    """
    # Load environment variables
    load_dotenv()
    
    credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
    sheet_id = os.getenv('LEADS_SHEET_ID')
    
    if not credentials_file or not sheet_id:
        logger.error("Missing required environment variables: GOOGLE_SHEETS_CREDENTIALS_FILE or LEADS_SHEET_ID")
        return False
    
    try:
        # Authenticate with Google Sheets
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(
            credentials_file, 
            scopes=scopes
        )
        
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(sheet_id)
        
        # Delete existing "Leads" worksheet if it exists
        try:
            worksheet = sheet.worksheet("Leads")
            sheet.del_worksheet(worksheet)
            logger.info("Deleted existing 'Leads' worksheet")
        except gspread.exceptions.WorksheetNotFound:
            logger.info("No existing 'Leads' worksheet found")
        
        # Create a new "Leads" worksheet
        worksheet = sheet.add_worksheet(title="Leads", rows=1000, cols=20)
        
        # Define the header row
        headers = [
            # Lead Input Fields
            "number",
            "whatsapp_number",
            "name",
            "email",
            
            # System/Workflow Tracking Fields
            "call_status",
            "retry_count",
            "next_retry_time",
            "whatsapp_sent",
            "email_sent",
            
            # AI Post-Call Analysis Fields
            "summary",
            "success_status",
            "structured_data"
        ]
        
        # Update the header row
        worksheet.update('A1:L1', [headers])
        
        # Format the header row
        worksheet.format('A1:L1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
        })
        
        # Add a sample row for testing
        sample_row = [
            "+919876543210",  # number
            "+919876543210",  # whatsapp_number
            "Test Student",   # name
            "test@example.com", # email
            "pending",        # call_status
            "0",              # retry_count
            "",               # next_retry_time
            "false",          # whatsapp_sent
            "false",          # email_sent
            "",               # summary
            "",               # success_status
            ""                # structured_data
        ]
        
        worksheet.update('A2:L2', [sample_row])
        
        logger.info("Successfully initialized Google Sheet with the required structure")
        print(f"Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing sheet: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    initialize_sheet()

