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
        # Option 1: JSON env var
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
        # Option 2: Render Secret File mounted path
        secret_file_candidates = [
            '/etc/secrets/GOOGLE_SHEETS_CREDENTIALS',
            os.path.join(os.getcwd(), 'GOOGLE_SHEETS_CREDENTIALS')
        ]

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(credentials_file), exist_ok=True)

            if credentials_json:
                creds = json.loads(credentials_json)
                with open(credentials_file, 'w') as f:
                    json.dump(creds, f, indent=2)
                logging.info(f"Created credentials file from GOOGLE_SHEETS_CREDENTIALS_JSON -> {credentials_file}")
                return

            # Try copying from secret file if exists
            for path in secret_file_candidates:
                if os.path.exists(path):
                    with open(path, 'r') as src, open(credentials_file, 'w') as dst:
                        dst.write(src.read())
                    logging.info(f"Copied credentials from {path} -> {credentials_file}")
                    return

            # If neither provided, fail
            logging.error("Credentials file not found and neither GOOGLE_SHEETS_CREDENTIALS_JSON nor Secret File is available")
            raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
        except Exception as e:
            logging.error(f"Failed to prepare credentials file: {e}")
            raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        setup_credentials()
        print("✅ Credentials setup completed successfully")
    except Exception as e:
        print(f"❌ Credentials setup failed: {e}")
        exit(1)
