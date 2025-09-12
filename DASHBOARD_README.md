# Smart Presales Dashboard

## Overview

The Smart Presales Dashboard provides a user-friendly interface for managing leads, initiating calls, and analyzing call outcomes. This document explains how to use the dashboard effectively.

## Features

### Lead Management
- View all leads in a sortable, filterable table
- Add new leads with contact information
- Filter leads by call status
- Search leads by name, phone, or email

### Call Initiation
- Initiate calls to leads with a single click
- View call status in real-time
- Track call history and outcomes

### Call Analysis
- View AI-generated call summaries
- See structured data extracted from calls
- Check lead qualification status

### Retry Configuration
- Set maximum number of retry attempts
- Configure time intervals between retries
- Add or remove retry intervals as needed

## Dashboard Sections

### Statistics Cards
The top of the dashboard displays key statistics:
- **Total Leads**: Number of leads in the system
- **Completed Calls**: Successfully completed calls
- **Pending Calls**: Leads waiting to be called
- **Missed Calls**: Calls that weren't answered and need retry
- **Qualified Leads**: Leads marked as qualified by the AI

### Leads Table
The main table shows all leads with the following information:
- Name, Phone, Email: Basic contact information
- Call Status: Current status (pending, initiated, answered, missed, failed, completed)
- Success Status: AI qualification result (Qualified, Potential, Not Qualified)
- Retry Count: Number of retry attempts and next scheduled retry time
- Last Call Time: When the last call was made
- Actions: Buttons to call or view details

### Lead Details
Clicking the "Details" button shows comprehensive information about a lead:
- **Contact Information**: Name, phone, email, WhatsApp number
- **Call Status**: Current status, retry count, last call time, next retry time
- **Call Analysis**: AI-generated summary, success status, structured data
- **Call History**: Record of all calls and their outcomes

## Using the Dashboard

### Adding a Lead
1. Click the "Add Lead" button
2. Fill in the required information (name, phone number)
3. Click "Add Lead" to save

### Initiating a Call
1. Find the lead in the table
2. Click the "Call" button next to the lead
3. The system will initiate a call via Vapi
4. The lead status will update to "initiated"

### Viewing Lead Details
1. Click the "Details" button next to a lead
2. A modal will open showing all lead information
3. Review call summary, structured data, and history

### Configuring Retry Settings
1. Click the "Retry Settings" button
2. Set the maximum number of retry attempts
3. Configure the time intervals (in hours) between retries
4. Add or remove intervals as needed
5. Click "Save Configuration" to apply changes

## Retry Logic

The system automatically handles call retries based on your configuration:

1. When a call is missed or fails, the system increments the retry count
2. The next retry time is calculated based on the configured intervals
3. When the retry time arrives, the orchestrator automatically attempts the call again
4. After reaching the maximum retry count, no further attempts are made

## Dashboard Updates

The dashboard automatically refreshes when:
- A new lead is added
- A call is initiated
- The retry configuration is updated

You can also manually refresh by clicking the "Refresh" button.

## Webhook Integration

The system processes real-time updates from Vapi webhooks:
- Call status changes (answered, missed, ended)
- Post-call analysis (summary, structured data, success evaluation)

These updates are reflected in the dashboard automatically.