# Deployment Checklist

## Pre-Deployment Checklist

### ✅ Code Preparation
- [x] All features implemented (bulk upload, bulk calling, retry logic)
- [x] Production-ready configuration
- [x] Proper error handling and logging
- [x] Environment variables configured
- [x] Dependencies listed in requirements.txt

### ✅ Files Created for Deployment
- [x] `.gitignore` - Excludes sensitive files and temporary data
- [x] `render.yaml` - Render deployment configuration
- [x] `Procfile` - Process definition for web services
- [x] `runtime.txt` - Python version specification
- [x] `DEPLOYMENT.md` - Detailed deployment instructions
- [x] `setup_github.sh` - GitHub setup helper script

## GitHub Setup

### 1. Create Repository
- [ ] Go to GitHub and create new repository: `amber-smart-presales`
- [ ] Make it private (recommended)
- [ ] Don't initialize with README

### 2. Push Code
```bash
# Run the setup script
./setup_github.sh

# Add remote (replace with your repo URL)
git remote add origin https://github.com/yourusername/amber-smart-presales.git

# Push to GitHub
git push -u origin main
```

## Render Deployment

### 1. Connect Repository
- [ ] Go to [Render Dashboard](https://dashboard.render.com)
- [ ] Click "New +" → "Web Service"
- [ ] Connect GitHub account
- [ ] Select `amber-smart-presales` repository

### 2. Configure Service
- [ ] **Name**: `amber-smart-presales`
- [ ] **Environment**: `Python 3`
- [ ] **Build Command**: `pip install -r requirements.txt`
- [ ] **Start Command**: `python main.py`

### 3. Set Environment Variables
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

### 4. Upload Credentials
- [ ] Upload `amber-sheets-credentials.json` as file variable
- [ ] Name it `GOOGLE_SHEETS_CREDENTIALS`

### 5. Deploy
- [ ] Click "Create Web Service"
- [ ] Wait for build to complete
- [ ] Note the deployment URL

## Post-Deployment Setup

### 1. Update Vapi Webhook
- [ ] Go to Vapi dashboard
- [ ] Update webhook URL to: `https://your-app-name.onrender.com/webhook/vapi`
- [ ] Save configuration

### 2. Test Application
- [ ] Access deployed app URL
- [ ] Add a test lead
- [ ] Initiate a call
- [ ] Verify webhook receives updates

### 3. Initialize Google Sheet
- [ ] The app will auto-create sheet structure
- [ ] Or manually run initialization if needed

## Verification Steps

### ✅ Functionality Tests
- [ ] Dashboard loads correctly
- [ ] Can add leads manually
- [ ] Can upload CSV files
- [ ] Can initiate individual calls
- [ ] Can initiate bulk calls
- [ ] Retry logic works for missed calls
- [ ] Webhooks update call status
- [ ] Post-call analysis displays correctly

### ✅ Production Readiness
- [ ] All sensitive data in environment variables
- [ ] No hardcoded credentials in code
- [ ] Proper error handling
- [ ] Logging configured
- [ ] Health check endpoint working

## Troubleshooting

### Common Issues
- **Build fails**: Check requirements.txt
- **Webhook not working**: Verify URL in Vapi
- **Google Sheets access**: Check credentials upload
- **Calls not working**: Verify Vapi API keys

### Support Resources
- [Render Documentation](https://render.com/docs)
- [Vapi Documentation](https://docs.vapi.ai)
- [Google Sheets API Docs](https://developers.google.com/sheets/api)

## Next Steps After Deployment

1. **Monitor Performance**: Check Render logs regularly
2. **Scale as Needed**: Upgrade Render plan if required
3. **Add Features**: Implement WhatsApp integration
4. **Security**: Add authentication and rate limiting
5. **Analytics**: Implement detailed reporting

---

**Ready to deploy?** Follow the steps above and your Amber Smart Presales application will be live on Render! 🚀
