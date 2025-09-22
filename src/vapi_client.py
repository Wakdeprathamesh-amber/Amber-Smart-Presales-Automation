import os
import requests
import json
from datetime import datetime

class VapiClient:
    def __init__(self, api_key):
        """
        Initialize the Vapi API client.
        
        Args:
            api_key (str): API key for Vapi
        """
        self.api_key = api_key
        self.base_url = "https://api.vapi.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def initiate_outbound_call(self, lead_data, assistant_id, phone_number_id):
        """
        Initiate an outbound call to a lead using Vapi.
        
        Args:
            lead_data (dict): Dictionary containing lead information
            assistant_id (str): ID of the Vapi assistant to use
            phone_number_id (str): ID of the Vapi phone number to call from
            
        Returns:
            dict: Response from Vapi API
        """
        endpoint = f"{self.base_url}/call"
        
        # Format the phone number if needed
        phone_number = str(lead_data.get("number", ""))
        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
        
        # Payload format as per Vapi documentation
        payload = {
            "assistantId": assistant_id,
            "phoneNumberId": phone_number_id,
            "customer": {
                "number": phone_number
            },
            "metadata": {
                # Prefer stable lead_uuid for correlation
                "lead_uuid": lead_data.get("lead_uuid", ""),
                # Keep legacy id fallback in case Vapi dashboard displays it
                "lead_id": lead_data.get("id", ""),
                "initiated_at": datetime.now().isoformat(),
                # Provide current date context for assistant prompts
                "today_iso": datetime.now().date().isoformat(),
                "today_human": datetime.now().strftime("%A, %B %d, %Y")
            }
        }
        
        print(f"Calling API with payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                endpoint, 
                headers=self.headers, 
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error initiating call: {e}")
            return {"error": str(e)}
    
    def get_call_details(self, call_id):
        """
        Get details of a specific call from Vapi.
        
        Args:
            call_id (str): ID of the call
            
        Returns:
            dict: Call details from Vapi
        """
        endpoint = f"{self.base_url}/call/{call_id}"
        
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting call details: {e}")
            return {"error": str(e)}
    
    def get_transcription(self, call_id):
        """
        Get the transcription of a call from Vapi.
        
        Args:
            call_id (str): ID of the call
            
        Returns:
            dict: Transcription details from Vapi
        """
        endpoint = f"{self.base_url}/call/{call_id}/transcript"
        
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting transcription: {e}")
            return {"error": str(e)}