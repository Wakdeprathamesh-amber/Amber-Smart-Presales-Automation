import os
import requests
import json
from datetime import datetime
from src.observability import trace_vapi_call
from src.utils import get_ist_timestamp, get_ist_now

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
    
    @trace_vapi_call
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
        # Precompute date vars
        today_iso = get_ist_now().date().isoformat()
        today_human = get_ist_now().strftime("%A, %B %d, %Y")

        # Extract first name for more natural greeting
        from src.utils import extract_first_name
        full_name = str(lead_data.get("name") or "")
        first_name = extract_first_name(full_name) or full_name  # Fallback to full name if extraction fails
        
        payload = {
            "assistantId": assistant_id,
            # Pass dynamic variables for prompt interpolation (e.g., {{name}})
            "assistantOverrides": {
                "variableValues": {
                    "name": first_name,  # Pass first name only for natural greeting
                    "partner": str(lead_data.get("partner") or "")
                }
            },
            "phoneNumberId": phone_number_id,
            "customer": {
                "number": phone_number
            },
            "metadata": {
                # Prefer stable lead_uuid for correlation
                "lead_uuid": lead_data.get("lead_uuid", ""),
                # Keep legacy id fallback in case Vapi dashboard displays it
                "lead_id": lead_data.get("id", ""),
                "initiated_at": get_ist_timestamp(),
                # Provide current date context for assistant prompts
                "today_iso": today_iso,
                "today_human": today_human
            }
        }

        # Optionally pass Deepgram keyword/keyterm boosts via assistant overrides
        # Env format examples:
        #   VAPI_TRANSCRIBER_KEYWORDS=snuffleupagus:5,systrom,krieger
        #   VAPI_TRANSCRIBER_KEYTERMS=order number,account ID,PCI compliance
        dg_keywords_csv = os.getenv("VAPI_TRANSCRIBER_KEYWORDS", "").strip()
        dg_keyterms_csv = os.getenv("VAPI_TRANSCRIBER_KEYTERMS", "").strip()

        transcriber_overrides = {}
        if dg_keywords_csv:
            # Keep original tokens (Deepgram accepts optional :int intensifiers)
            keywords = [token.strip() for token in dg_keywords_csv.split(",") if token.strip()]
            if keywords:
                transcriber_overrides["keywords"] = keywords
        if dg_keyterms_csv:
            keyterms = [phrase.strip() for phrase in dg_keyterms_csv.split(",") if phrase.strip()]
            if keyterms:
                transcriber_overrides["keyterm"] = keyterms

        # If no env provided, use in-code defaults
        if not transcriber_overrides.get("keywords"):
            transcriber_overrides["keywords"] = [
                "UK:5",
                "USA:5",
                "Canada:3",
                "Ireland:3",
                "France:3",
                "Spain:3",
                "Germany:3",
                "Australia:3",
                "Amber:5",
                "IELTS:4",
                "TOEFL:4",
                "GRE:4",
                "GMAT:4",
                "SAT:4",
                "MSC:5",
                "MBA:4",
                "Bachelors:3",
                "Masters:3",
                "PhD:3",
                "September:3",
                "January:3",
                "May:3",
                "February:3",
                "Intake:3",
                "Visa:4",
                "Guarantor:4",
                "Budget:3",
                "WhatsApp:4",
                "Housing:3",
                "Dorm:3",
                "Apartment:3",
                "Shared:3",
                "exploring:2",
                "maybe:2",
                "thinking:2",
                "yeah:2",
                "yess:2",
                "sure:2",
                "ok:2",
                "fine:2",
                "go:2",
                "ahead:2"
            ]
        # Important: Only include keyterm if explicitly provided via env.
        # Some Deepgram models (e.g., Nova-2) may not accept keyterm, causing 400.

        if transcriber_overrides:
            # Ensure assistantOverrides exists and then attach transcriber overrides
            assistant_overrides = payload.get("assistantOverrides") or {}
            # Vapi requires provider if transcriber is overridden
            assistant_overrides["transcriber"] = {
                "provider": "deepgram",
                **transcriber_overrides
            }
            payload["assistantOverrides"] = assistant_overrides
        
        print(f"Calling API with payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as he:
                # Provide detailed response info for debugging 4xx/5xx
                err_body = None
                try:
                    err_body = response.text
                except Exception:
                    err_body = ''
                print(f"Vapi call failed: status={response.status_code} body={err_body}")
                return {"error": f"HTTP {response.status_code}", "body": err_body}
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