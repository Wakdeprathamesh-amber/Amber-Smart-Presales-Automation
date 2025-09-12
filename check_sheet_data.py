import os
from dotenv import load_dotenv
from src.sheets_manager import SheetsManager

def check_sheet_data():
    """Check the lead data in the Google Sheet and print it in a readable format."""
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
    sheet_id = os.getenv('LEADS_SHEET_ID')
    
    # Initialize sheet manager
    sheets_manager = SheetsManager(credentials_file, sheet_id)
    
    # Get all leads
    worksheet = sheets_manager.sheet.worksheet("Leads")
    all_leads = worksheet.get_all_records()
    
    print(f"\nFound {len(all_leads)} leads in the sheet:")
    print("-" * 80)
    
    # Print leads with key information
    for idx, lead in enumerate(all_leads):
        print(f"Lead #{idx+1}:")
        print(f"  Name: {lead.get('name', 'N/A')}")
        print(f"  Phone: {lead.get('number', 'N/A')}")
        print(f"  Email: {lead.get('email', 'N/A')}")
        print(f"  Status: {lead.get('call_status', 'N/A')}")
        
        # If call was completed, show summary and success status
        if lead.get('call_status') == 'completed':
            print(f"  Summary: {lead.get('summary', 'N/A')[:100]}...")
            print(f"  Success: {lead.get('success_status', 'N/A')}")
        
        print("-" * 80)

if __name__ == "__main__":
    check_sheet_data()

