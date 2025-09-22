import os
import requests
from typing import Dict, List, Optional


class WhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str, dry_run: bool = False):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.dry_run = dry_run or (os.getenv("WHATSAPP_DRY_RUN", "false").lower() == "true")
        self.base_url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def send_template(self,
                      to_number_e164: str,
                      template_name: str,
                      language: str = "en",
                      body_parameters: Optional[List[str]] = None) -> Dict:
        """
        Send a WhatsApp template message using WhatsApp Cloud API.

        Args:
            to_number_e164: Recipient in E.164 format
            template_name: Approved template name
            language: BCP-47 code like 'en' or 'en_US'
            body_parameters: Optional list of strings mapped to {{1}}, {{2}}, ...
        """
        # Normalize phone format
        to_number = to_number_e164 if to_number_e164.startswith("+") else f"+{to_number_e164}"

        components = []
        if body_parameters:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in body_parameters]
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                **({"components": components} if components else {})
            }
        }

        if self.dry_run:
            # Simulate success without making network call
            return {
                "dry_run": True,
                "to": to_number,
                "template": template_name,
                "language": language,
                "parameters": body_parameters or [],
                "id": "wamid.DRY_RUN_MESSAGE"
            }

        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, "status_code", None), "body": getattr(e.response, "text", None)}


