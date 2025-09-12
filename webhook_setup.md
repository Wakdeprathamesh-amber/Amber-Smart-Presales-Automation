# Setting Up Vapi Webhooks

This guide walks you through setting up webhooks to receive events from Vapi.

## 1. Start Your Application

First, make sure your application is running:

```bash
source venv/bin/activate
python main.py
```

This will start your Flask server on port 5000.

## 2. Expose Your Local Server with ngrok

In a new terminal window, run:

```bash
ngrok http 5000
```

This will generate output similar to:

```
Session Status                online
Account                       Your Account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       24ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123def456.ngrok.io -> http://localhost:5000
```

Copy the HTTPS forwarding URL (e.g., `https://abc123def456.ngrok.io`).

## 3. Configure Vapi Webhooks

1. Log in to your Vapi dashboard
2. Navigate to your assistant settings
3. Look for "Webhook" or "Server URL" settings
4. Enter your ngrok URL + `/webhook/vapi`
   - Example: `https://abc123def456.ngrok.io/webhook/vapi`
5. Save your settings

## 4. Test the Webhook Connection

To test if your webhook is properly set up:

1. Make a test call using Vapi
2. Check your application logs for incoming webhook events:
   ```bash
   tail -f logs/app.log
   ```

## Notes

- The ngrok URL changes each time you restart ngrok
- For production, you'll need a stable URL (deploy to a cloud service)
- Webhook events include call status updates, transcriptions, and AI analysis

