import os
import time
from datetime import datetime
from src.sheets_manager import SheetsManager
from src.vapi_client import VapiClient
from src.retry_manager import RetryManager

class CallOrchestrator:
    def __init__(self, sheets_manager, vapi_client, retry_manager, assistant_id, phone_number_id):
        """
        Initialize the call orchestrator.
        
        Args:
            sheets_manager (SheetsManager): Instance of SheetsManager
            vapi_client (VapiClient): Instance of VapiClient
            retry_manager (RetryManager): Instance of RetryManager
            assistant_id (str): ID of the Vapi assistant to use
            phone_number_id (str): ID of the Vapi phone number to call from
        """
        self.sheets_manager = sheets_manager
        self.vapi_client = vapi_client
        self.retry_manager = retry_manager
        self.assistant_id = assistant_id
        self.phone_number_id = phone_number_id
    
    def process_pending_leads(self, only_retry=True):
        """
        Process leads that are due for calls.
        
        Args:
            only_retry (bool): If True, only process retry leads, not new leads
            
        Returns:
            dict: Summary of processed leads
        """
        # Get leads that are due for retry (and optionally new pending leads)
        pending_leads = self.sheets_manager.get_pending_leads(only_retry=only_retry)
        
        results = {
            "total_leads_processed": len(pending_leads),
            "calls_initiated": 0,
            "errors": 0,
            "details": []
        }
        
        for _idx, lead in enumerate(pending_leads):
            # Determine actual sheet row (0-based) using lead_uuid if present; fallback to id
            lead_uuid = lead.get('lead_uuid')
            if lead_uuid:
                row_index_0 = self.sheets_manager.find_row_by_lead_uuid(lead_uuid)
            else:
                # legacy fallback: list position might not match sheet row; try id if present
                try:
                    row_index_0 = int(lead.get('id'))
                except Exception:
                    row_index_0 = None
            lead_id = lead_uuid or str(lead.get('id', ''))
            try:
                print(f"Processing lead: {lead.get('name', 'Unknown')} (Phone: {lead.get('number', 'Unknown')})")
                
                # Check if lead has required fields
                if not lead.get('number'):
                    print(f"Error: Missing phone number for lead {lead_id}")
                    results["errors"] += 1
                    results["details"].append({
                        "lead_id": lead_id,
                        "status": "error",
                        "error": "Missing phone number"
                    })
                    continue
                
                # Prepare lead data
                lead_data = {
                    "lead_uuid": lead_uuid,
                    "id": str(lead.get('id', '')),
                    "number": lead.get('number', ''),
                    "name": lead.get('name', ''),
                    "email": lead.get('email', '')
                }
                
                # Initiate call
                call_result = self.vapi_client.initiate_outbound_call(
                    lead_data=lead_data,
                    assistant_id=self.assistant_id,
                    phone_number_id=self.phone_number_id
                )
                
                if "error" in call_result:
                    # Call initiation failed
                    print(f"Error initiating call: {call_result['error']}")
                    results["errors"] += 1
                    results["details"].append({
                        "lead_id": lead_id,
                        "status": "error",
                        "error": call_result["error"]
                    })
                else:
                    # Call initiated successfully
                    print(f"Call initiated successfully for lead {lead_id}")
                    if row_index_0 is not None:
                        # record initiation with call_time and vapi_call_id
                        call_time = datetime.now().isoformat()
                        self.sheets_manager.update_lead_call_initiated(row_index_0, "initiated", call_time, call_result.get('id'))
                    results["calls_initiated"] += 1
                    results["details"].append({
                        "lead_id": lead_id,
                        "status": "initiated",
                        "call_id": call_result.get("id")
                    })
                
                # Add small delay between API calls to avoid rate limits
                time.sleep(1)
                
            except Exception as e:
                print(f"Exception processing lead {lead_id}: {e}")
                results["errors"] += 1
                results["details"].append({
                    "lead_id": lead_id,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def run_once(self):
        """
        Run a single processing cycle.
        
        Returns:
            dict: Results of processing
        """
        return self.process_pending_leads()
    
    def run_continuously(self, interval_seconds=60):
        """
        Run processing in a continuous loop with interval.
        
        Args:
            interval_seconds (int): Seconds to wait between processing cycles
        """
        print(f"Starting continuous processing. Checking for leads every {interval_seconds} seconds...")
        
        try:
            while True:
                print(f"\n[{datetime.now().isoformat()}] Running processing cycle...")
                results = self.run_once()
                
                print(f"Processed {results['total_leads_processed']} leads.")
                print(f"Calls initiated: {results['calls_initiated']}")
                print(f"Errors: {results['errors']}")
                
                print(f"Waiting for {interval_seconds} seconds before next cycle...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\nStopping continuous processing.")
            return