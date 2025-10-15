# 📁 Project Structure

**Last Updated**: October 13, 2025  
**Status**: ✅ Clean & Production-Ready

---

## 🎯 Quick Navigation

| Need | File | Purpose |
|------|------|---------|
| **Deploy now** | `READY_TO_DEPLOY.md` | 3-step deployment guide |
| **Voice bot issues** | `VOICE_BOT_IMPROVEMENT_STRATEGY.md` | Complete strategy & fixes |
| **Vapi prompt** | `PROMPT_IMPROVEMENTS.md` | Copy-paste ready prompt |
| **Vapi settings** | `VAPI_DASHBOARD_CONFIGURATION.md` | Dashboard configuration |
| **LangFuse setup** | `LANGFUSE_SETUP_GUIDE.md` | Observability integration |
| **Production deploy** | `PRODUCTION_DEPLOYMENT.md` | Render deployment |
| **Project overview** | `README.md` | Main documentation |

---

## 📂 Complete Structure

```
Smart Presales Version 1/
│
├── 📚 DOCUMENTATION (8 files)
│   ├── README.md                              # Main project documentation
│   ├── READY_TO_DEPLOY.md                     # ⭐ Start here for deployment
│   ├── VOICE_BOT_IMPROVEMENT_STRATEGY.md      # Voice bot strategy & roadmap
│   ├── PROMPT_IMPROVEMENTS.md                 # Vapi assistant prompt
│   ├── VAPI_DASHBOARD_CONFIGURATION.md        # Vapi dashboard settings
│   ├── LANGFUSE_SETUP_GUIDE.md                # LangFuse observability guide
│   ├── PRODUCTION_DEPLOYMENT.md               # Production deployment guide
│   └── docs/
│       └── PRD.md                             # Product Requirements Document
│
├── ⚙️ CONFIGURATION (7 files)
│   ├── config/
│   │   ├── amber-sheets-credentials.json      # Google Sheets API credentials
│   │   ├── config.example.env                 # Environment variables template
│   │   └── credentials-template.json          # Credentials template
│   ├── Procfile                               # Render deployment config
│   ├── render.yaml                            # Render service config
│   ├── requirements.txt                       # Python dependencies
│   └── runtime.txt                            # Python version (3.13)
│
├── 💻 SOURCE CODE (17 files)
│   ├── main.py                                # ⭐ Application entry point
│   ├── startup.py                             # Setup & initialization
│   │
│   └── src/                                   # Core application
│       ├── __init__.py
│       │
│       ├── 🌐 WEB & API
│       ├── app.py                             # Flask app (dashboard + webhooks)
│       ├── static/                            # Frontend assets
│       │   ├── css/style.css                  # Dashboard styles
│       │   └── js/dashboard.js                # Dashboard JavaScript
│       └── templates/
│           └── index.html                     # Dashboard HTML
│       │
│       ├── 📞 VOICE & COMMUNICATION
│       ├── vapi_client.py                     # Vapi API client
│       ├── webhook_handler.py                 # Vapi webhook processor
│       ├── email_client.py                    # Email sending (SMTP)
│       ├── email_inbound.py                   # Email polling (IMAP)
│       └── whatsapp_client.py                 # WhatsApp messaging
│       │
│       ├── 🔄 ORCHESTRATION & WORKFLOWS
│       ├── scheduler.py                       # APScheduler background jobs
│       ├── call_orchestrator.py               # Legacy orchestrator (fallback)
│       ├── retry_manager.py                   # Retry logic & intervals
│       └── workflows/
│           ├── __init__.py
│           └── lead_workflow.py               # LangGraph workflow state machine
│       │
│       ├── 📊 DATA & STORAGE
│       ├── sheets_manager.py                  # Google Sheets API client
│       └── init_sheet.py                      # Sheet initialization script
│       │
│       └── 🔍 OBSERVABILITY
│           └── observability.py               # LangFuse tracing & logging
│
├── 🧪 TESTS (5 files)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_flow.py                       # End-to-end flow tests
│   │   ├── test_hybrid_orchestration.py       # Orchestration tests
│   │   ├── test_vapi_final.py                 # Vapi integration tests
│   │   └── test_webhook.py                    # Webhook handler tests
│   └── test_langfuse_connection.py            # LangFuse connection test
│
├── 🔧 UTILITIES (2 files)
│   ├── setup.py                               # Project setup script
│   └── setup_github.sh                        # GitHub setup script
│
└── 📝 LOGS (Auto-generated)
    └── logs/
        ├── app.log                            # Application logs
        ├── main.log                           # Main process logs
        └── test_server.log                    # Test server logs
```

---

## 🏗️ Architecture Overview

### **Core Components**

```
┌─────────────────────────────────────────────────────────────┐
│                      ENTRY POINT                            │
│                       main.py                               │
│  • Starts Flask app (dashboard + webhooks)                 │
│  • Initializes APScheduler background jobs                 │
│  • Sets up LangFuse observability                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├──────────────────┬──────────────────┐
                              ▼                  ▼                  ▼
┌────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│   WEB/API LAYER    │ │  ORCHESTRATION   │ │   OBSERVABILITY      │
│                    │ │                  │ │                      │
│ • Flask App        │ │ • APScheduler    │ │ • LangFuse Client    │
│ • Dashboard UI     │ │ • Job Scheduler  │ │ • Trace Decorators   │
│ • Webhook Endpoint │ │ • LangGraph      │ │ • Conversation Logs  │
│ • API Endpoints    │ │ • State Machine  │ │ • Call Analysis      │
└────────────────────┘ └──────────────────┘ └──────────────────────┘
         │                      │                       │
         │                      │                       │
         └──────────────────────┴───────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   INTEGRATION LAYER                         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │ Vapi Client │  │   Sheets    │  │  Communication   │   │
│  │             │  │   Manager   │  │                  │   │
│  │ • Outbound  │  │ • Read/Write│  │ • Email (SMTP)   │   │
│  │   Calls     │  │ • Batching  │  │ • Email (IMAP)   │   │
│  │ • Webhooks  │  │ • Caching   │  │ • WhatsApp API   │   │
│  └─────────────┘  └─────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### **Data Flow**

```
1. CALL INITIATION
   Scheduler → LangGraph Workflow → Vapi Client → Vapi API
                                          ↓
                                   Webhook Event
                                          ↓
2. WEBHOOK PROCESSING
   Vapi → Webhook Handler → Callback Detection
                          → Human Handover
                          → Call Analysis
                          → Sheets Update
                          → LangFuse Trace

3. CALLBACK SCHEDULING
   Webhook Handler → Extract Time → Schedule Job → APScheduler
                                          ↓
                                   (Trigger at scheduled time)
                                          ↓
                                   Vapi Client → Initiate Call

4. FALLBACK CHANNELS
   Missed Call → Retry Manager → Max Retries?
                                    ↓
                            Yes → WhatsApp Fallback
                                → Email Fallback
```

---

## 📊 Code Statistics

### **Source Code**
- **Total Lines**: ~3,500 lines
- **Python Files**: 17 files
- **Test Files**: 5 files
- **Documentation**: 8 files

### **Key Modules**
| Module | Lines | Purpose |
|--------|-------|---------|
| `scheduler.py` | ~480 | Background job orchestration |
| `webhook_handler.py` | ~660 | Vapi webhook processing + callbacks |
| `sheets_manager.py` | ~400 | Google Sheets integration |
| `lead_workflow.py` | ~410 | LangGraph state machine |
| `app.py` | ~350 | Flask dashboard & API |
| `vapi_client.py` | ~210 | Vapi API client |
| `observability.py` | ~180 | LangFuse tracing |

---

## 🎯 Key Features

### **✅ Implemented**
1. ✅ **Automated Outbound Calls** - Vapi voice assistant
2. ✅ **Call Analysis** - AI-generated summaries & structured data
3. ✅ **Retry Logic** - Configurable intervals for missed calls
4. ✅ **Multi-Channel Fallback** - WhatsApp + Email
5. ✅ **Dashboard** - Lead management UI
6. ✅ **APScheduler** - Background job orchestration
7. ✅ **LangGraph** - Stateful workflow state machine
8. ✅ **LangFuse** - End-to-end observability
9. ✅ **Callback Scheduling** - Natural language time parsing
10. ✅ **Human Handover** - Function calling integration

### **⏳ Planned (Future)**
- Phase 4: Evaluation framework for voice bot
- Phase 5: A/B testing & prompt iteration
- Multi-language support
- Slack notifications for human handover

---

## 🚀 Quick Commands

### **Local Development**
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# Run tests
python -m pytest tests/

# Test LangFuse connection
python test_langfuse_connection.py
```

### **Deployment**
```bash
# Push to GitHub (auto-deploys to Render)
git add .
git commit -m "Your message"
git push origin main

# Manual Render deployment
# Go to: https://dashboard.render.com
# Click: Manual Deploy
```

---

## 📚 Documentation Index

| File | Lines | Purpose | Audience |
|------|-------|---------|----------|
| `README.md` | 300 | Project overview | Everyone |
| `READY_TO_DEPLOY.md` | 230 | Quick deployment guide | DevOps, Team Lead |
| `VOICE_BOT_IMPROVEMENT_STRATEGY.md` | 539 | Voice bot analysis & fixes | PM, Tech Lead |
| `PROMPT_IMPROVEMENTS.md` | 261 | Vapi assistant prompt | Prompt Engineer |
| `VAPI_DASHBOARD_CONFIGURATION.md` | 212 | Dashboard settings | DevOps, Admin |
| `LANGFUSE_SETUP_GUIDE.md` | 971 | Observability setup | DevOps, Developer |
| `PRODUCTION_DEPLOYMENT.md` | 399 | Production deploy | DevOps |
| `docs/PRD.md` | ~500 | Product requirements | PM, Stakeholders |

**Total Documentation**: ~3,400 lines

---

## ✅ Code Quality Checklist

- ✅ **Clean Structure**: Well-organized, logical file hierarchy
- ✅ **No Redundancy**: Removed 15 outdated .md files (67% reduction)
- ✅ **Modular Design**: Separation of concerns across modules
- ✅ **Type Hints**: Used where appropriate
- ✅ **Error Handling**: Try-except blocks with logging
- ✅ **Logging**: Structured logging throughout
- ✅ **Testing**: Comprehensive test suite
- ✅ **Documentation**: Extensive inline comments & docs
- ✅ **Environment Variables**: Secure config management
- ✅ **No Linter Errors**: All files pass linting
- ✅ **Git Ignored**: venv, __pycache__, credentials excluded

---

## 🎯 Next Steps

1. **Review** this structure
2. **Deploy** using `READY_TO_DEPLOY.md`
3. **Test** voice bot improvements
4. **Monitor** using LangFuse dashboard
5. **Iterate** based on real call data

---

## 📞 Support

- **GitHub**: https://github.com/[your-repo]
- **Render Dashboard**: https://dashboard.render.com
- **LangFuse Dashboard**: https://us.cloud.langfuse.com
- **Documentation**: All .md files in root directory

---

**Status**: ✅ Production-Ready  
**Maintainability**: Excellent  
**Code Quality**: High  
**Documentation**: Comprehensive

🎉 **Ready to deploy!**

