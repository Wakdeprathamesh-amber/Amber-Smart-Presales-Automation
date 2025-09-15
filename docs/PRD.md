## Amber Student Smart Presales – Product Requirements & Technical Design (PRD)

### 1. Problem Statement
- Presales team performs manual outbound calls to student leads, causing delays and missed opportunities.
- Missed/failed calls are not consistently retried; follow-ups via WhatsApp/email are ad-hoc.
- Post-call data (summary, structured fields, qualification) is inconsistent and manual.
- Limited visibility into lead statuses, outcomes, and pipeline health.

### 2. Goals & Objectives
- Automate outbound calls with an AI assistant (Vapi) to reach leads reliably.
- Centralize lead data and statuses with real-time updates.
- Implement automatic retry logic for missed/failed calls.
- Capture AI-powered post-call analysis (summary, structured data, success evaluation).
- Provide a dashboard to manage leads, trigger calls, review outcomes, bulk operations.
- Prepare for automated WhatsApp follow-ups (fallback and post-call) and two-way messaging.

### 3. Scope
- In-Scope (current POC)
  - Google Sheets as the system of record for leads.
  - Flask web app: dashboard, API, webhooks, orchestrator.
  - Vapi integration: outbound calling; webhooks for status and analysis.
  - Retry logic (configurable, minute-based for POC: 2, 4, 6 minutes).
  - Bulk lead upload (CSV) and bulk calling.
  - Lead deletion, UUID-based identity to avoid row-index fragility.
  - Deploy to Render with environment-based configuration.
- Next (near-term)
  - WhatsApp Cloud API: auto-send on max retries and post-call; manual send in UI.
  - Webhook for inbound WhatsApp replies and delivery receipts.
  - Persist message history; show in dashboard.
- Out-of-Scope (now)
  - Inbound voice call routing.
  - Full CRM integration and auth/role-based access.
  - Advanced analytics/BI and SLA alerting.

### 4. Users & Use Cases
- Presales Lead/Agent:
  - Upload leads, trigger calls, review outcomes, manage retries, delete bad leads.
  - View call summaries, structured data, and success evaluations.
- Presales Manager:
  - Monitor pipeline health, missed vs completed, qualified counts.

### 5. Success Metrics (KPIs)
- Contact rate: % of leads with answered calls within N attempts.
- Completion rate: % of initiated calls that complete with analysis.
- Qualification rate: % leads marked Qualified/Potential.
- Time-to-first-contact and time-to-completion.
- Reduction in manual effort (calls initiated via system).

### 6. High-Level Workflow
1) Lead added (UI/CSV) → pending.
2) Agent triggers call (manual) or bulk call → status initiated.
3) Vapi dials lead → webhooks stream status.
4) If answered, conversation proceeds; on end, Vapi sends analysis and evaluation.
5) Webhook updates sheet → dashboard reflects in near real-time.
6) If missed/failed, retry scheduled based on policy (2, 4, 6 minutes in POC).
7) After max retries, (future) WhatsApp fallback template auto-sent.
8) (Future) Post-call follow-up template auto-sent when call completes.

### 7. System Architecture
- Frontend: HTML/CSS/JS dashboard served by Flask.
- Backend: Flask API + webhook endpoints + orchestrator thread for retry processing.
- Data Store: Google Sheets (Leads, future: Settings/Conversations).
- Voice: Vapi Assistant (assistantId, phoneNumberId).
- Webhooks: Vapi → /webhook/vapi; (future) WhatsApp → /webhook/whatsapp.
- Hosting: Render (Python service). Ngrok only for local dev.

```
User ─▶ Dashboard (Flask) ─▶ API ─▶ Google Sheets
                        │            ▲
                        │            │
                        ├─▶ Vapi API (outbound call)
                        │
Webhook ◀───────────────┴── Vapi Webhooks (/webhook/vapi)

(Future)
Webhook ◀─────────────── WhatsApp Webhooks (/webhook/whatsapp)
           ▲
           └─▶ WhatsApp Cloud API (template/text send)
```

### 8. Data Model (Google Sheets: Leads worksheet)
- Columns:
  - lead_uuid (string, UUID v4)
  - number (E.164)
  - whatsapp_number (default: number)
  - name, email
  - call_status (pending, initiated, answered, missed, failed, completed)
  - retry_count (int), next_retry_time (ISO string)
  - whatsapp_sent (bool), email_sent (bool)
  - summary (string), success_status (Qualified/Potential/Not Qualified), structured_data (JSON string)
  - last_call_time (ISO string), vapi_call_id, last_analysis_at

### 9. Key Components
- Flask App (`src/app.py`)
  - Routes: leads CRUD, initiate call, bulk upload/call, retry-config, webhooks, health.
  - Lazy initialization for credentials/services to avoid import-time failures.
- Orchestrator (`src/call_orchestrator.py`)
  - Polls for eligible leads (retry due), initiates calls, updates statuses.
- Sheets Manager (`src/sheets_manager.py`)
  - All reads/writes to Sheets; UUID lookup; deletion; AI analysis updates.
- Vapi Client (`src/vapi_client.py`)
  - initiate_outbound_call with assistantId/phoneNumberId and metadata (lead_uuid).
- Webhook Handler (`src/webhook_handler.py`)
  - Handles status-update and end-of-call-report.
  - Classifies missed/failed vs completed. Treats no-answer/timeout/ring-out as missed.
  - Exponential backoff for 429s; in-memory lead_uuid→row cache.

### 10. Retry Logic
- Config via env: MAX_RETRY_COUNT, RETRY_INTERVALS, RETRY_UNITS (minutes/hours).
- POC defaults: 3 attempts at 2, 4, 6 minutes (RETRY_UNITS=minutes, RETRY_INTERVALS=2,4,6).
- Missed/failed increments retry_count, sets next_retry_time.
- After max retries, mark no further retries; (future) trigger WhatsApp fallback.

### 11. WhatsApp Cloud API (Future Phase)
- Outbound:
  - Templates: fallback_after_retries, post_call_followup (languages e.g., en_US).
  - Env: WHATSAPP_CLOUD_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_WABA_ID, template names.
  - Triggers: on max retries; after completed call; manual send.
- Inbound/Webhooks:
  - /webhook/whatsapp with verify token; subscribe to messages + status updates.
  - Persist inbound messages to Sheets (Conversations) and show in dashboard.
- Compliance: opt-in tracking, STOP handling, 24-hour window.

#### 11.1 WhatsApp Templates & Flows (Planned)
- Template A: post_call_success
  - Use-case: Call answered and completed; send summary/follow-up links.
  - Variables: {{1}} student_name, {{2}} followup_link (or booking CTA), {{3}} advisor signature.
  - Trigger: End-of-call analysis received with success_status in [Qualified, Potential].
- Template B: retry_fallback_no_answer
  - Use-case: Max retries reached without connection; offer WhatsApp assistance and callback option.
  - Variables: {{1}} student_name, {{2}} callback_link or preferred time capture prompt, {{3}} support link.
  - Trigger: Max retry reached (missed/failed).
- Manual send: “Send WhatsApp” UI action to send either template or custom text (within 24h window).

#### 11.2 AI on WhatsApp (Two‑Way Messaging)
- Goal: Continue qualification over chat if user replies; AI responds contextually.
- Inputs to AI: Conversation history, lead record (name, preferences), Vapi call analysis if available.
- Guardrails: Respect 24-hour messaging policy; switch to templates outside window.
- Persistence: Store inbound/outbound messages with timestamps and message types.
- Handover: If user requests or confidence low, route to human agent and mark lead as assigned.

#### 11.3 Dashboard Additions for WhatsApp
- Per-lead “Message History” beside “Call History”.
- Manual “Send WhatsApp” with template pickers and variable preview.
- Status badges for delivery/read receipts.
- Filters: leads awaiting reply, within 24h window, needs human handover.

### 12. Security & Privacy
- Secrets via environment variables/secret files; never committed.
- Principle of least privilege for service account.
- Basic rate-limit/backoff for external APIs.
- Logging: minimal, no PII beyond what’s needed to debug.

### 13. Non-Functional Requirements
- Availability: Render Free (POC) acceptable; upgrade for always-on.
- Performance: Dashboard loads in <2s for typical sheet sizes; retries processed every 60s.
- Scalability: Migrate from Sheets to DB for >10k leads or heavy concurrency.
- Observability: Render logs; add structured logs and alerts later.

### 14. Deployment & Configuration
- Render Web Service: build pip install; start python main.py.
- Env Vars:
  - PORT, FLASK_DEBUG
  - GOOGLE_SHEETS_CREDENTIALS_FILE, GOOGLE_SHEETS_CREDENTIALS_JSON (or Secret File)
  - LEADS_SHEET_ID
  - VAPI_API_KEY, VAPI_ASSISTANT_ID, VAPI_PHONE_NUMBER_ID
  - MAX_RETRY_COUNT, RETRY_INTERVALS, RETRY_UNITS, ORCHESTRATOR_INTERVAL_SECONDS
- Webhooks:
  - Vapi: https://<app>.onrender.com/webhook/vapi
  - (Future) WhatsApp: https://<app>.onrender.com/webhook/whatsapp

### 15. API Endpoints (Summary)
- GET / → dashboard
- GET /api/leads; POST /api/leads; DELETE /api/leads/:uuid
- POST /api/leads/:uuid/call; GET /api/leads/:uuid/details
- GET/POST /api/retry-config
- POST /api/leads/bulk-upload; POST /api/leads/bulk-call
- POST /webhook/vapi; (Future) POST /webhook/whatsapp
- GET /health

### 16. Dashboard (UI)
- Leads table with status, success status, retry count, last call time, actions.
- Add Lead modal, Retry Settings modal, Upload CSV, Call All Eligible.
- Lead Details: contact info, call status, analysis, call history.
- Auto-refresh when active calls present.

#### 16.1 Enhancements (Planned)
- WhatsApp Message History with send controls.
- Bulk upload improvements: validation report, sample CSV download.
- Agent routing: “Assign to Agent” action, with export to manual queues.
- Attachments (future): show call recording link and transcription excerpt when available.

### 17. Current POC Achievements
- End-to-end outbound calling via Vapi with correct payload and phone formats.
- Real-time webhook updates; missed/failed classification refined.
- AI analysis stored to Sheets; dashboard displays details.
- Retry logic (2/4/6 min); bulk upload & bulk call workflows.
- UUID identity; robust sheet operations; caching and backoff for 429s.
- Deletion by UUID; stable with re-additions.
- Deployment on Render with credentials bootstrapper.

### 18. Known Gaps & Next Steps
- WhatsApp integration (send + webhook + UI message history).
- Opt-in/STOP compliance handling.
- Enrich call history (multiple entries) vs single last call snapshot.
- Authentication/authorization for dashboard.
- Move from Sheets to database for scale; migrations and schema.
- Monitoring/alerting (errors, webhook failures, rate limits).

### 18.1 Costing (POC Estimates)
- Vapi: depends on plan (minutes per call, transcription/analysis). Assume $0.03–$0.08/min effective; analysis included per plan.
- Telephony (Plivo/Twilio via Vapi): per-minute outbound rates by destination (e.g., India ~$0.006–$0.02/min). Caller ID/STIR/SHAKEN/brand registration may add setup costs.
- WhatsApp Cloud API: template sends billed by conversation category and country; user-initiated within 24h window is often low/no cost; business-initiated templates incur country/category rates (e.g., $0.01–$0.15/conversation). Check Meta regional pricing.
- Render: Free for POC; upgrade Starter ($7/mo) or higher for always-on.
- Google Sheets API: free within quotas; consider BigQuery/DB costs if migrating.
- Misc: Domain/HTTPS (Render managed), monitoring (free/basic initially).
Note: Final costs vary by volumes (calls/minutes, WhatsApp conversations, geography). We’ll instrument metrics to forecast.

### 19. Delivery Plan (Next 2–3 Days)
Day 1:
- Implement WhatsApp send service + env config + manual “Send WhatsApp” action.
- Persist outbound sends to Sheets (Conversations sheet).

Day 2:
- Add /webhook/whatsapp for inbound replies + delivery status.
- Render in Lead Details → Message History. Basic STOP handling.

Day 3:
- Auto-send rules (max retries & post-call). Polish UI, error handling, docs.

### 22. Future Roadmap
- Inbound Voice Support (Customer Support):
  - Provision inbound numbers; webhook to AI assistant via Vapi; IVR-lite flows.
  - Screen intents (FAQ, policy, payment, property info) and answer using Amber knowledge base.
  - Handover to human when out-of-policy or high-risk.
- Knowledge Access for AI (Voice & Chat):
  - Connect to Amber databases/FAQs/inventory via secure APIs.
  - Retrieval-Augmented Generation (RAG) to ground responses in live data.
- Recommendations on Call/Chat:
  - Use structured preferences (budget, location, intake) + inventory to suggest properties.
  - Rankers akin to BERT/YouTube/TikTok style learning-to-rank; A/B test scripts/prompts.
- Advanced Analytics & ML:
  - Funnel tracking with reason codes at each step (missed reasons, objections, price sensitivity).
  - Lead scoring model predicting likelihood to book; next-best-action prompts.
  - Cohort reports for process optimization and script improvements.

### 20. Risks & Mitigations
- Google Sheets quotas → caching, backoff, reduce polling; consider DB migration.
- Vapi/WhatsApp API changes → version pinning, graceful errors.
- Template approval delays → prepare neutral copy; parallel approval.
- Render free tier sleep → upgrade instance for production.

### 21. Appendix
- Environment Variables Reference (see DEPLOYMENT.md).
- n8n alternative workflow export available under `n8n/` for non-code orchestration.


