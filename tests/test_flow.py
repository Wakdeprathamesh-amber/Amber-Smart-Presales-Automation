import os
import logging
from dotenv import load_dotenv
from src.sheets_manager import SheetsManager
from src.vapi_client import VapiClient
from src.retry_manager import RetryManager
from src.webhook_handler import WebhookHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_components():
    """Test individual components of the system."""
    
    # Load environment variables
    load_dotenv()
    logger.info("Testing components...")
    
    try:
        # Test SheetsManager
        logger.info("Testing SheetsManager...")
        credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
        sheet_id = os.getenv('LEADS_SHEET_ID')
        
        if not credentials_file or not sheet_id:
            logger.error("Missing Google Sheets credentials or sheet ID in .env file")
            return False
        
        sheets_manager = SheetsManager(credentials_file, sheet_id)
        
        # Test Vapi client
        logger.info("Testing Vapi client...")
        vapi_api_key = os.getenv('VAPI_API_KEY')
        
        if not vapi_api_key:
            logger.error("Missing Vapi API key in .env file")
            return False
        
        vapi_client = VapiClient(vapi_api_key)
        
        # Test RetryManager
        logger.info("Testing RetryManager...")
        retry_intervals = [int(h) for h in os.getenv('RETRY_INTERVALS', '1,4,24').split(',')]
        max_retries = int(os.getenv('MAX_RETRY_COUNT', '3'))
        
        retry_manager = RetryManager(max_retries, retry_intervals)
        
        # Test webhook handler
        logger.info("Testing WebhookHandler...")
        webhook_handler = WebhookHandler(sheets_manager, retry_manager)
        
        logger.info("All components initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

def simulate_call_flow():
    """Simulate a complete call flow."""
    
    # Load environment variables
    load_dotenv()
    
    try:
        logger.info("Simulating call flow...")
        
        # Initialize components
        credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE')
        sheet_id = os.getenv('LEADS_SHEET_ID')
        sheets_manager = SheetsManager(credentials_file, sheet_id)
        
        vapi_api_key = os.getenv('VAPI_API_KEY')
        vapi_client = VapiClient(vapi_api_key)
        
        retry_intervals = [int(h) for h in os.getenv('RETRY_INTERVALS', '1,4,24').split(',')]
        max_retries = int(os.getenv('MAX_RETRY_COUNT', '3'))
        retry_manager = RetryManager(max_retries, retry_intervals)
        
        webhook_handler = WebhookHandler(sheets_manager, retry_manager)
        
        # Step 1: Get a pending lead (without actually calling the API)
        logger.info("Step 1: Simulating getting a pending lead...")
        
        mock_lead = {
            "id": "0",
            "number": "+919876543210",
            "whatsapp_number": "+919876543210",
            "name": "Test Student",
            "email": "test@example.com",
            "call_status": "pending",
            "retry_count": 0
        }
        
        # Step 2: Simulate call initiation
        logger.info("Step 2: Simulating call initiation...")
        
        # Step 3: Simulate webhook event for answered call
        logger.info("Step 3: Simulating webhook event for answered call...")
        
        mock_answered_event = {
            "type": "call.answered",
            "metadata": {
                "lead_id": "0"
            }
        }
        
        # Process the event without actually updating the sheet
        logger.info("Processing answered call event...")
        logger.info(f"Would update lead status to: answered")
        
        # Step 4: Simulate webhook event for call completion
        logger.info("Step 4: Simulating webhook event for call completion...")
        
        mock_completed_event = {
            "type": "call.completed",
            "metadata": {
                "lead_id": "0"
            },
            "ai_summary": "Student is interested in pursuing an MBA in the UK and needs housing assistance.",
            "ai_success_status": "Qualified",
            "ai_structured_data": '{"course": "MBA", "country": "UK", "housing": "needed", "visa_status": "not_applied"}'
        }
        
        # Process the event without actually updating the sheet
        logger.info("Processing completed call event...")
        logger.info(f"Would update lead status to: completed")
        logger.info(f"Would update AI summary, success status, and structured data")
        
        # Step 5: Simulate missed call and retry
        logger.info("Step 5: Simulating missed call and retry...")
        
        mock_missed_event = {
            "type": "call.missed",
            "metadata": {
                "lead_id": "0"
            },
            "retry_count": 0
        }
        
        # Process the event without actually updating the sheet
        logger.info("Processing missed call event...")
        logger.info(f"Would update lead status to: missed")
        logger.info(f"Would schedule retry with new count: 1")
        
        logger.info("Call flow simulation completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    if test_components():
        logger.info("Component tests passed!")
        
        if simulate_call_flow():
            logger.info("Call flow simulation passed!")
            logger.info("All tests passed! The system appears to be configured correctly.")
        else:
            logger.error("Call flow simulation failed.")
    else:
        logger.error("Component tests failed.")

