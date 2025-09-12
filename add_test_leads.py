import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

def add_test_leads():
    """Add test leads to the Google Sheet for automated calling."""
    # Load environment variables
    load_dotenv()
    
    credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
    sheet_id = os.getenv('LEADS_SHEET_ID')
    
    if not credentials_file or not sheet_id:
        print("Missing environment variables: GOOGLE_SHEETS_CREDENTIALS_FILE or LEADS_SHEET_ID")
        return False
    
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
    worksheet = sheet.worksheet("Leads")
    
    # Add some test leads
    test_leads = [
        [
            "+919175686589",  # number - REPLACE WITH YOUR ACTUAL TEST NUMBER
            "+919175686589",  # whatsapp_number
            "Test User 1",    # name
            "test1@example.com", # email
            "pending",        # call_status
            "0",              # retry_count
            "",               # next_retry_time
            "false",          # whatsapp_sent
            "false",          # email_sent
            "",               # summary
            "",               # success_status
            ""                # structured_data
        ],
        [
            "+919175686589",  # number - REPLACE WITH YOUR ACTUAL TEST NUMBER
            "+919175686589",  # whatsapp_number
            "Test User 2",    # name
            "test2@example.com", # email
            "pending",        # call_status
            "0",              # retry_count
            "",               # next_retry_time
            "false",          # whatsapp_sent
            "false",          # email_sent
            "",               # summary
            "",               # success_status
            ""                # structured_data
        ]
    ]
    
    # Get the current row count and add the test leads
    all_values = worksheet.get_all_values()
    start_row = len(all_values) + 1
    
    for i, lead in enumerate(test_leads):
        row_index = start_row + i
        worksheet.update(f'A{row_index}:L{row_index}', [lead])
        print(f"Added test lead {i+1}: {lead[2]}")
    
    print("\nTest leads added successfully!")
    print(f"Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    return True

if __name__ == "__main__":
    add_test_leads()

