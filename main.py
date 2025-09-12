import os
import logging
from dotenv import load_dotenv
import threading
from src.sheets_manager import SheetsManager
from src.vapi_client import VapiClient
from src.retry_manager import RetryManager
from src.call_orchestrator import CallOrchestrator
from src.app import app

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def start_orchestrator():
    """Start the call orchestration process in a separate thread."""
    try:
        logger.info("Initializing call orchestrator...")
        
        # Initialize components with error handling
        try:
            sheets_manager = SheetsManager(
                credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
                sheet_id=os.getenv('LEADS_SHEET_ID')
            )

            retry_intervals = [int(x) for x in os.getenv('RETRY_INTERVALS', '1,4,24').split(',')]
            retry_units = os.getenv('RETRY_UNITS', 'hours')
            retry_manager = RetryManager(
                max_retries=int(os.getenv('MAX_RETRY_COUNT', '3')),
                retry_intervals=retry_intervals,
                interval_unit=retry_units
            )

            vapi_client = VapiClient(api_key=os.getenv('VAPI_API_KEY'))
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            logger.error("Please check your environment variables and credentials")
            return
        
        # Get assistant ID from environment
        assistant_id = os.getenv('VAPI_ASSISTANT_ID')
        if not assistant_id:
            logger.error("VAPI_ASSISTANT_ID environment variable not set")
            return
        
        # Get phone number ID from environment
        phone_number_id = os.getenv('VAPI_PHONE_NUMBER_ID')
        if not phone_number_id:
            logger.error("VAPI_PHONE_NUMBER_ID environment variable not set")
            return
        
        # Create orchestrator
        orchestrator = CallOrchestrator(
            sheets_manager=sheets_manager,
            vapi_client=vapi_client,
            retry_manager=retry_manager,
            assistant_id=assistant_id,
            phone_number_id=phone_number_id
        )
        
        # Run with interval (in seconds)
        interval = int(os.getenv('ORCHESTRATOR_INTERVAL_SECONDS', '60'))
        logger.info(f"Starting call orchestrator with {interval} second interval")
        orchestrator.run_continuously(interval_seconds=interval)
    
    except Exception as e:
        logger.error(f"Error in orchestrator: {e}", exc_info=True)

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Set up credentials if needed
    try:
        from startup import setup_credentials
        setup_credentials()
    except Exception as e:
        logger.error(f"Failed to set up credentials: {e}")
        # Continue anyway - the app will handle missing credentials gracefully
    
    # Start call orchestrator in a separate thread
    orchestrator_thread = threading.Thread(target=start_orchestrator)
    orchestrator_thread.daemon = True
    orchestrator_thread.start()
    
    # Start Flask application for dashboard and webhooks
    port = int(os.getenv('PORT', '5001'))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    logger.info(f"Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)