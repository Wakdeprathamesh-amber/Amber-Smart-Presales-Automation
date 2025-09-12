import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

def verify_sheet():
    # Load environment variables
    load_dotenv()
    
    credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
    sheet_id = os.getenv('LEADS_SHEET_ID')
    
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
    
    # Get the "Leads" worksheet
    try:
        worksheet = sheet.worksheet("Leads")
        
        # Get all values
        all_values = worksheet.get_all_values()
        
        # Print headers
        print("SHEET HEADERS:")
        print("=============")
        if all_values:
            headers = all_values[0]
            for idx, header in enumerate(headers):
                print(f"{idx+1}. {header}")
        else:
            print("No headers found!")
        
        print("\nSAMPLE DATA:")
        print("===========")
        if len(all_values) > 1:
            sample_row = all_values[1]
            for idx, value in enumerate(sample_row):
                if idx < len(headers):
                    print(f"{headers[idx]}: {value}")
        else:
            print("No sample data found!")
            
        print("\nSheet URL:", f"https://docs.google.com/spreadsheets/d/{sheet_id}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    verify_sheet()

