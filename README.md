# Amber Student Smart Presales Automation

A complete POC for automating the lead qualification process for Amber Student's presales team.

## Overview

Amber Student Smart Presales automation streamlines the outbound lead qualification workflow:

- **Automated Outbound Calls**: Uses Vapi voice assistant to call student leads
- **Intelligent Conversations**: AI-powered conversations to qualify leads
- **Call Analysis**: Generates summaries and extracts structured data
- **Lead Management**: Dashboard for tracking and managing leads
- **Automatic Retry Logic**: Handles missed calls with configurable retry intervals

## Features

### Voice Automation
- Automated outbound calling using Vapi AI assistant
- Natural conversations with leads to gather qualification data
- Call transcriptions and recordings

### Lead Management
- Modern dashboard UI for lead management
- Google Sheets integration for data storage
- Lead filtering and searching

### AI Analysis
- AI-generated call summaries
- Structured data extraction from conversations
- Lead qualification status determination

### Process Automation
- Automatic retries for missed calls
- Configurable retry intervals
- Webhook processing for real-time updates

## Getting Started

### Prerequisites
- Python 3.8+
- Google Sheets API credentials
- Vapi account and API key
- Access to a Google Sheet with the required lead data structure

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Update your `.env` file with your credentials:
   ```
   # Google Sheets Configuration
   GOOGLE_SHEETS_CREDENTIALS_FILE=config/your-credentials.json
   LEADS_SHEET_ID=your_sheet_id_here

   # Vapi Configuration
   VAPI_API_KEY=your_vapi_api_key_here
   VAPI_ASSISTANT_ID=your_assistant_id_here
   VAPI_PHONE_NUMBER_ID=your_phone_number_id_here

   # Retry Configuration
   MAX_RETRY_COUNT=3
   RETRY_INTERVALS=1,4,24  # Hours between retry attempts

   # Server Configuration
   PORT=5001
   ORCHESTRATOR_INTERVAL_SECONDS=60
   ```

### Running the Application

1. Initialize the Google Sheet (first time only):
   ```
   python src/init_sheet.py
   ```

2. Start the application:
   ```
   python main.py
   ```

3. Access the dashboard:
   ```
   http://localhost:5001
   ```

### Setting up Webhooks

For processing call events, set up a webhook using ngrok:

1. Start ngrok:
   ```
   ngrok http 5001
   ```

2. Configure Vapi webhook:
   - In your Vapi dashboard, set the webhook URL to: `https://your-ngrok-url.ngrok-free.app/webhook/vapi`

## Project Structure

```
Smart Presales Version 1/
├── config/                 # Configuration files
│   └── credentials.json    # Google Sheets API credentials
├── logs/                   # Application logs
├── src/
│   ├── static/             # Frontend assets
│   │   ├── css/            # Stylesheet files
│   │   └── js/             # JavaScript files
│   ├── templates/          # HTML templates
│   │   └── index.html      # Dashboard template
│   ├── app.py              # Flask application
│   ├── call_orchestrator.py # Call orchestration logic
│   ├── init_sheet.py       # Google Sheet initialization
│   ├── retry_manager.py    # Call retry logic
│   ├── sheets_manager.py   # Google Sheets integration
│   ├── vapi_client.py      # Vapi API client
│   └── webhook_handler.py  # Webhook processing
├── .env                    # Environment variables
├── DASHBOARD_README.md     # Dashboard documentation
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── setup.py               # Setup script
├── test_flow.py           # End-to-end test script
├── test_vapi_final.py     # Vapi API test script
└── verify_sheet.py        # Sheet verification utility
```

## Dashboard Usage

The dashboard provides an intuitive interface for managing leads and initiating calls:

- **Lead Management**: View, add, and filter leads
- **Call Initiation**: Start calls with a single click
- **Call Details**: View summaries, structured data, and call history
- **Retry Configuration**: Set retry attempts and intervals for missed calls
- **Real-time Updates**: See call statuses and outcomes
- **Statistics**: View key metrics and conversion rates

For detailed dashboard documentation, see [DASHBOARD_README.md](DASHBOARD_README.md).

## Deployment

This application can be deployed to cloud platforms like Render. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy to Render

1. Push code to GitHub
2. Connect repository to Render
3. Set environment variables
4. Upload Google Sheets credentials
5. Deploy!

## Contributing

This is a POC project. For production implementation, consider:

1. Database integration for more robust data storage
2. Authentication and user management
3. Additional communication channels (WhatsApp, email)
4. Enhanced analytics and reporting

## License

Copyright (c) 2025 Amber Student# Amber-Smart-Presales-Automation
