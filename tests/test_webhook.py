#!/usr/bin/env python3
"""
Test script to simulate Vapi webhook events for testing post-call analysis flow.
This script sends simulated webhook events to the local server.
"""

import requests
import json
import sys
import time
from datetime import datetime

# Webhook URL (local server)
WEBHOOK_URL = "http://localhost:5001/webhook/vapi"

def send_webhook_event(event_type, lead_id="0"):
    """Send a simulated webhook event to the local server."""
    
    # Base event structure
    event = {
        "call": {
            "id": "test-call-123",
            "metadata": {
                "lead_id": lead_id,
                "initiated_at": datetime.now().isoformat()
            }
        },
        "message": {}
    }
    
    # Create event based on type
    if event_type == "answered":
        event["message"] = {
            "type": "status-update",
            "status": "answered",
            "call": event["call"]
        }
    
    elif event_type == "missed":
        event["message"] = {
            "type": "status-update",
            "status": "missed",
            "endedReason": "no-answer",
            "call": event["call"]
        }
    
    elif event_type == "ended":
        event["message"] = {
            "type": "status-update",
            "status": "ended",
            "endedReason": "completed",
            "call": event["call"]
        }
    
    elif event_type == "report":
        event["message"] = {
            "type": "end-of-call-report",
            "call": event["call"],
            "analysis": {
                "summary": "The student is planning to study Computer Science at Oxford University starting in September 2025. They have not yet received their visa and will need a guarantor for accommodation. They are looking for student housing with a budget of around £1000 per month.",
                "successEvaluation": "Qualified",
                "structuredData": {
                    "name": "Prathamesh",
                    "course": "Computer Science",
                    "university": "Oxford University",
                    "intake": "September 2025",
                    "visa_status": "Not yet applied",
                    "guarantor_needed": "Yes",
                    "housing_preference": "Student housing",
                    "budget": "£1000 per month",
                    "contact_preference": "WhatsApp"
                }
            }
        }
    
    else:
        print(f"Unknown event type: {event_type}")
        return False
    
    # Send webhook event
    print(f"\nSending {event_type} event for lead {lead_id}...")
    print(json.dumps(event, indent=2))
    
    try:
        response = requests.post(WEBHOOK_URL, json=event)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending webhook: {e}")
        return False

def simulate_full_call_flow(lead_id="0"):
    """Simulate a complete call flow with all webhook events."""
    
    print(f"\n=== Simulating complete call flow for lead {lead_id} ===\n")
    
    # Step 1: Call answered
    if not send_webhook_event("answered", lead_id):
        print("Failed to send 'answered' event. Aborting flow.")
        return False
    
    # Wait a moment
    time.sleep(2)
    
    # Step 2: Call ended
    if not send_webhook_event("ended", lead_id):
        print("Failed to send 'ended' event. Aborting flow.")
        return False
    
    # Wait a moment
    time.sleep(2)
    
    # Step 3: End-of-call report
    if not send_webhook_event("report", lead_id):
        print("Failed to send 'report' event. Aborting flow.")
        return False
    
    print("\n=== Call flow simulation completed successfully ===\n")
    return True

def simulate_missed_call(lead_id="0"):
    """Simulate a missed call with webhook event."""
    
    print(f"\n=== Simulating missed call for lead {lead_id} ===\n")
    
    # Send missed call event
    if not send_webhook_event("missed", lead_id):
        print("Failed to send 'missed' event. Aborting flow.")
        return False
    
    print("\n=== Missed call simulation completed successfully ===\n")
    return True

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get("http://localhost:5001/health")
        if response.status_code != 200:
            print("Server is not responding correctly. Make sure it's running.")
            sys.exit(1)
    except Exception:
        print("Could not connect to server. Make sure it's running on port 5001.")
        sys.exit(1)
    
    # Get lead ID from command line if provided
    lead_id = sys.argv[1] if len(sys.argv) > 1 else "0"
    
    # Get event type from command line if provided
    event_type = sys.argv[2] if len(sys.argv) > 2 else "full"
    
    if event_type == "full":
        simulate_full_call_flow(lead_id)
    elif event_type == "missed":
        simulate_missed_call(lead_id)
    elif event_type in ["answered", "ended", "report"]:
        send_webhook_event(event_type, lead_id)
    else:
        print(f"Unknown event type: {event_type}")
        print("Usage: python test_webhook.py [lead_id] [event_type]")
        print("Event types: full, missed, answered, ended, report")

