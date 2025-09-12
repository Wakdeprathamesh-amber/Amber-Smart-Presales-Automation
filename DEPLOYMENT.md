# Deployment Guide

This guide covers deploying the Amber Student Smart Presales application to GitHub and Render.

## Prerequisites

- GitHub account
- Render account
- Google Sheets API credentials
- Vapi account with API key, assistant ID, and phone number ID

## GitHub Setup

### 1. Create a GitHub Repository

1. Go to [GitHub](https://github.com) and create a new repository
2. Name it `amber-smart-presales` (or your preferred name)
3. Make it private (recommended for production)
4. Don't initialize with README (we already have one)

### 2. Push Code to GitHub

```bash
# Initialize git repository
git init

# Add all files
git add .

# Commit initial version
git commit -m "Initial commit: Amber Student Smart Presales POC"

# Add remote origin (replace with your repository URL)
git remote add origin https://github.com/yourusername/amber-smart-presales.git

# Push to GitHub
git push -u origin main
```

## Render Deployment

### 1. Connect Repository

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub account
4. Select your `amber-smart-presales` repository

### 2. Configure Service

**Basic Settings:**
- **Name**: `amber-smart-presales`
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Root Directory**: Leave empty (uses root)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`

**Environment Variables:**
Add these in the Render dashboard:

```
PORT=10000
GOOGLE_SHEETS_CREDENTIALS_FILE=config/amber-sheets-credentials.json
LEADS_SHEET_ID=your_google_sheet_id_here
VAPI_API_KEY=your_vapi_api_key_here
VAPI_ASSISTANT_ID=your_vapi_assistant_id_here
VAPI_PHONE_NUMBER_ID=your_vapi_phone_number_id_here
MAX_RETRY_COUNT=3
RETRY_INTERVALS=1,4,24
ORCHESTRATOR_INTERVAL_SECONDS=60
FLASK_DEBUG=False
```

### 3. Upload Credentials

**Important**: You need to upload your Google Sheets credentials file:

1. In your Render service dashboard, go to "Environment"
2. Click "Add Environment Variable"
3. Add a file variable named `GOOGLE_SHEETS_CREDENTIALS`
4. Upload your `amber-sheets-credentials.json` file

### 4. Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy your application
3. Once deployed, you'll get a URL like `https://amber-smart-presales.onrender.com`

## Post-Deployment Setup

### 1. Update Vapi Webhook

1. Go to your Vapi dashboard
2. Update the webhook URL to: `https://your-app-name.onrender.com/webhook/vapi`
3. Save the configuration

### 2. Initialize Google Sheet

1. Access your deployed app: `https://your-app-name.onrender.com`
2. The app will automatically create the required sheet structure
3. Or manually run the initialization if needed

### 3. Test the Application

1. Add a test lead through the dashboard
2. Initiate a call to verify everything works
3. Check that webhooks are being received

## Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `PORT` | Server port | No | 5001 |
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | Path to credentials JSON | Yes | - |
| `LEADS_SHEET_ID` | Google Sheet ID | Yes | - |
| `VAPI_API_KEY` | Vapi API key | Yes | - |
| `VAPI_ASSISTANT_ID` | Vapi assistant ID | Yes | - |
| `VAPI_PHONE_NUMBER_ID` | Vapi phone number ID | Yes | - |
| `MAX_RETRY_COUNT` | Maximum retry attempts | No | 3 |
| `RETRY_INTERVALS` | Retry intervals (hours) | No | 1,4,24 |
| `ORCHESTRATOR_INTERVAL_SECONDS` | Check interval | No | 60 |
| `FLASK_DEBUG` | Debug mode | No | False |

## Troubleshooting

### Common Issues

1. **Build Fails**: Check that all dependencies are in `requirements.txt`
2. **Webhook Not Working**: Verify the webhook URL in Vapi dashboard
3. **Google Sheets Access**: Ensure credentials file is uploaded correctly
4. **Calls Not Initiating**: Check Vapi API key and assistant ID

### Logs

View application logs in Render dashboard:
1. Go to your service
2. Click "Logs" tab
3. Monitor for errors and debug information

### Health Check

The application includes a health check endpoint:
- `GET https://your-app-name.onrender.com/health`

## Security Considerations

1. **Environment Variables**: Never commit sensitive data to GitHub
2. **Credentials**: Use Render's file upload for credentials
3. **Webhooks**: Consider adding webhook signature verification
4. **Rate Limiting**: Monitor Google Sheets API usage

## Scaling

For production scaling:
1. Upgrade to a paid Render plan
2. Consider using a proper database instead of Google Sheets
3. Implement proper authentication
4. Add monitoring and alerting

## Support

For issues with deployment:
1. Check Render logs
2. Verify all environment variables
3. Test locally first
4. Contact support if needed
