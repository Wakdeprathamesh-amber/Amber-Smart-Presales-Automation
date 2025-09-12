import os
import sys
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_project():
    """Set up the project directory structure and configuration files."""
    logger.info("Setting up Amber Student Smart Presales POC...")
    
    # Create necessary directories
    directories = ["logs", "config"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
    
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        if os.path.exists("config/config.example.env"):
            shutil.copy("config/config.example.env", ".env")
            logger.info("Created .env file from example template")
            logger.info("Please update the .env file with your actual configuration")
        else:
            logger.error("config.example.env not found, cannot create .env file")
            return False
    
    # Create logs directory
    if not os.path.exists("logs"):
        os.makedirs("logs")
        logger.info("Created logs directory")
    
    logger.info("Setup complete! Next steps:")
    logger.info("1. Update the .env file with your Google Sheets credentials and Vapi API key")
    logger.info("2. Run 'python src/init_sheet.py' to initialize your Google Sheet")
    logger.info("3. Run 'python main.py' to start the application")
    
    return True

if __name__ == "__main__":
    setup_project()

