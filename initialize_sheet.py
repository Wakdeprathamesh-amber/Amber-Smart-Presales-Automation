#!/usr/bin/env python3
"""
Initialize the Google Sheet with the required structure for the Smart Presales system.
This script creates the Leads worksheet with the necessary headers if it doesn't exist.
"""

import os
import sys
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

def initialize_sheet():
    """Initialize the Google Sheet with required structure."""
    
    # Get credentials and sheet ID from environment
    credentials_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
    sheet_id = os.getenv("LEADS_SHEET_ID")
    
    if not credentials_file:
        print("Error: GOOGLE_SHEETS_CREDENTIALS_FILE environment variable not set.")
        sys.exit(1)
    
    if not sheet_id:
        print("Error: LEADS_SHEET_ID environment variable not set.")
        sys.exit(1)
    
    # Authenticate with Google Sheets API
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        credentials = Credentials.from_service_account_file(
            credentials_file,
            scopes=scopes
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(sheet_id)
        print(f"Successfully connected to Google Sheet: {sheet.title}")
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        sys.exit(1)
    
    # Check if Leads worksheet exists
    try:
        leads_worksheet = sheet.worksheet("Leads")
        print("Leads worksheet already exists.")
        
        # Check if it has headers
        headers = leads_worksheet.row_values(1)
        if headers:
            print(f"Headers found: {headers}")
            # Offer to reset schema if it's outdated
            desired_headers = [
                "lead_uuid", "number", "whatsapp_number", "name", "email", "call_status",
                "retry_count", "next_retry_time", "whatsapp_sent", "email_sent",
                "summary", "success_status", "structured_data", "last_call_time",
                "vapi_call_id", "last_analysis_at"
            ]
            if headers != desired_headers:
                print("Resetting Leads sheet schema to stable UUID-based format...")
                leads_worksheet.clear()
                leads_worksheet.update('A1:P1', [desired_headers])
                print("Schema reset completed.")
        else:
            print("No headers found. Adding headers...")
            headers = [
                "lead_uuid", "number", "whatsapp_number", "name", "email", "call_status",
                "retry_count", "next_retry_time", "whatsapp_sent", "email_sent",
                "summary", "success_status", "structured_data", "last_call_time",
                "vapi_call_id", "last_analysis_at"
            ]
            leads_worksheet.update('A1:P1', [headers])
            print("Headers added successfully.")
    except gspread.exceptions.WorksheetNotFound:
        print("Leads worksheet not found. Creating new worksheet...")
        
        # Create new worksheet
        leads_worksheet = sheet.add_worksheet(title="Leads", rows=100, cols=13)
        
        # Add headers
        headers = [
            "number", "whatsapp_number", "name", "email", "call_status",
            "retry_count", "next_retry_time", "whatsapp_sent", "email_sent",
            "summary", "success_status", "structured_data", "last_call_time"
        ]
        leads_worksheet.update('A1:M1', [headers])
        print("Leads worksheet created with headers.")
    
    # Check if Settings worksheet exists
    try:
        settings_worksheet = sheet.worksheet("Settings")
        print("Settings worksheet already exists.")
    except gspread.exceptions.WorksheetNotFound:
        print("Settings worksheet not found. Creating new worksheet...")
        
        # Create new worksheet
        settings_worksheet = sheet.add_worksheet(title="Settings", rows=10, cols=5)
        
        # Add headers and default values
        settings_worksheet.update('A1:B1', [['Setting', 'Value']])
        settings_worksheet.update('A2:B2', [['max_retries', '3']])
        settings_worksheet.update('A3:B3', [['retry_intervals', '[1, 4, 24]']])
        print("Settings worksheet created with default values.")
    
    print("\nSheet initialization complete!")
    print("\nYou can now add leads through the dashboard or manually to the Google Sheet.")
    print("Make sure to follow the header structure for manual additions.")

if __name__ == "__main__":
    initialize_sheet()
