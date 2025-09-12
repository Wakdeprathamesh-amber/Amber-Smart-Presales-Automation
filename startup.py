#!/usr/bin/env python3
"""
Startup script for Render deployment.
Handles credentials file creation from environment variables.
"""

import os
import json
import logging
from pathlib import Path

def setup_credentials():
    """Set up Google Sheets credentials from environment variable if needed."""
    credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'config/amber-sheets-credentials.json')
    
    # If credentials file doesn't exist, try to create it from environment variable
    if not os.path.exists(credentials_file):
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
        if credentials_json:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(credentials_file), exist_ok=True)
                
                # Parse and write credentials
                creds = json.loads(credentials_json)
                with open(credentials_file, 'w') as f:
                    json.dump(creds, f, indent=2)
                
                logging.info(f"Created credentials file from environment variable: {credentials_file}")
            except Exception as e:
                logging.error(f"Failed to create credentials file: {e}")
                raise
        else:
            logging.error(f"Credentials file not found and no GOOGLE_SHEETS_CREDENTIALS_JSON provided")
            raise FileNotFoundError(f"Credentials file not found: {credentials_file}")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        setup_credentials()
        print("✅ Credentials setup completed successfully")
    except Exception as e:
        print(f"❌ Credentials setup failed: {e}")
        exit(1)
