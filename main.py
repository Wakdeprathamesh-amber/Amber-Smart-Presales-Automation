import os
import logging
from dotenv import load_dotenv
from src.app import app
from src.scheduler import start_background_jobs, shutdown_scheduler
import atexit

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

# Thread-based orchestration replaced with APScheduler (see src/scheduler.py)

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
    
    # Start APScheduler background jobs
    logger.info("Starting background job scheduler...")
    scheduler = start_background_jobs()
    
    # Register shutdown handler for graceful cleanup
    atexit.register(shutdown_scheduler)
    
    # Start Flask application for dashboard and webhooks
    port = int(os.getenv('PORT', '5001'))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    logger.info(f"Starting web server on port {port}")
    
    # Important: use_reloader=False to avoid duplicate scheduler instances
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=False)