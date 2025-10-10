import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

def test_vapi_connection():
    """Test connection to Vapi API using the correct format from documentation"""
    # Load environment variables
    load_dotenv()
    
    vapi_api_key = os.getenv('VAPI_API_KEY')
    assistant_id = os.getenv('VAPI_ASSISTANT_ID')
    
    if not vapi_api_key or not assistant_id:
        print("ERROR: Missing Vapi API key or assistant ID in .env file")
        return False
    
    print(f"Using Vapi API key: {vapi_api_key[:8]}...")
    print(f"Using Assistant ID: {assistant_id}")
    
    # Get phone number ID
    print("\nWe need your phone number ID from Vapi.")
    print("You can find this in your Vapi dashboard under Phone Numbers.")
    phone_number_id = input("Enter your Vapi phone number ID: ")
    
    if not phone_number_id:
        print("ERROR: Phone number ID is required")
        return False
    
    # Test phone number
    test_number = input("Enter a phone number to test (E.164 format, e.g., +919876543210): ")
    if not test_number:
        test_number = "+919876543210"  # Default test number
    
    # Base URL and headers
    base_url = "https://api.vapi.ai"
    headers = {
        "Authorization": f"Bearer {vapi_api_key}",
        "Content-Type": "application/json"
    }
    
    # Correctly formatted payload based on documentation - WITHOUT variables
    payload = {
        "assistantId": assistant_id,
        "phoneNumberId": phone_number_id,
        "customer": {
            "number": test_number
        },
        # Removed variables field
        "metadata": {
            "lead_id": "test-001",
            "initiated_at": datetime.now().isoformat()
        }
    }
    
    print("\nRequest payload:")
    print(json.dumps(payload, indent=2))
    
    # Ask for confirmation before making the call
    confirm = input("\nThis will initiate a real call. Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled")
        return False
    
    try:
        print("\nMaking API request...")
        response = requests.post(
            f"{base_url}/call", 
            headers=headers, 
            json=payload
        )
        
        print(f"Status code: {response.status_code}")
        
        try:
            response_json = response.json()
            print("Response JSON:")
            print(json.dumps(response_json, indent=2))
        except:
            print("Response text (not JSON):")
            print(response.text)
            
        if response.status_code == 200 or response.status_code == 201:
            print("\nSUCCESS: Call initiated successfully!")
            if "id" in response_json:
                print(f"Call ID: {response_json.get('id')}")
            return True
        else:
            print("\nERROR: Failed to place call")
            return False
            
    except Exception as e:
        print(f"Exception during API request: {e}")
        return False

if __name__ == "__main__":
    test_vapi_connection()

