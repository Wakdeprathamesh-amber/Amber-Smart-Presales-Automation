"""
LangGraph workflow for lead engagement orchestration.
Handles multi-channel communication: Call → WhatsApp → Email with retries.
"""

import os
import logging
from typing import TypedDict, List, Literal, Annotated
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


# Define the state structure
class LeadState(TypedDict):
    """State for lead engagement workflow."""
    lead_uuid: str
    lead_name: str
    lead_number: str
    lead_email: str
    whatsapp_number: str
    
    # Status tracking
    call_status: str  # pending, initiated, answered, missed, failed, completed
    retry_count: int
    max_retries: int
    
    # Channel tracking
    channels_tried: List[str]  # ['call', 'whatsapp', 'email']
    last_channel: str
    
    # Conversation context (centralized memory)
    conversation_history: List[dict]
    
    # Results
    qualification_status: str  # qualified, unqualified, needs_followup
    structured_data: dict
    summary: str
    
    # Workflow control
    next_action: str  # call, retry, whatsapp_fallback, email_fallback, complete


def initiate_call_node(state: LeadState) -> dict:
    """
    Node: Initiate outbound call via Vapi.
    
    Returns:
        dict: Updated state with call initiation results
    """
    try:
        from src.vapi_client import VapiClient
        from src.sheets_manager import SheetsManager
        
        logger.info(f"[Workflow] Initiating call for lead {state['lead_uuid']}")
        
        vapi_client = VapiClient(api_key=os.getenv('VAPI_API_KEY'))
        
        # Prepare lead data
        lead_data = {
            "lead_uuid": state["lead_uuid"],
            "number": state["lead_number"],
            "name": state["lead_name"],
            "email": state["lead_email"]
        }
        
        # Initiate call
        result = vapi_client.initiate_outbound_call(
            lead_data=lead_data,
            assistant_id=os.getenv('VAPI_ASSISTANT_ID'),
            phone_number_id=os.getenv('VAPI_PHONE_NUMBER_ID')
        )
        
        if "error" in result:
            logger.error(f"[Workflow] Call initiation failed: {result['error']}")
            return {
                "call_status": "failed",
                "last_channel": "call",
                "channels_tried": state["channels_tried"] + ["call"],
                "next_action": "check_retry"
            }
        
        logger.info(f"[Workflow] Call initiated successfully: {result.get('id')}")
        
        # Update Sheets with initiated status
        try:
            sheets_manager = SheetsManager(
                credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
                sheet_id=os.getenv('LEADS_SHEET_ID')
            )
            row_index = sheets_manager.find_row_by_lead_uuid(state["lead_uuid"])
            if row_index is not None:
                sheets_manager.update_lead_call_initiated(
                    row_index,
                    "initiated",
                    datetime.now().isoformat(),
                    result.get('id')
                )
        except Exception as e:
            logger.warning(f"[Workflow] Failed to update Sheets: {e}")
        
        return {
            "call_status": "initiated",
            "last_channel": "call",
            "channels_tried": state["channels_tried"] + ["call"] if "call" not in state["channels_tried"] else state["channels_tried"],
            "conversation_history": state["conversation_history"] + [{
                "timestamp": datetime.now().isoformat(),
                "channel": "call",
                "action": "initiated",
                "call_id": result.get('id')
            }],
            "next_action": "await_webhook"  # Wait for Vapi webhook to update status
        }
        
    except Exception as e:
        logger.error(f"[Workflow] Call node error: {e}", exc_info=True)
        return {
            "call_status": "failed",
            "next_action": "check_retry"
        }


def check_retry_node(state: LeadState) -> Literal["retry", "fallback", "complete"]:
    """
    Node: Decide whether to retry call or fallback to other channels.
    
    Returns:
        str: Next action ("retry", "fallback", or "complete")
    """
    logger.info(f"[Workflow] Checking retry for lead {state['lead_uuid']}: retry_count={state['retry_count']}, max={state['max_retries']}")
    
    # If call was completed successfully, we're done
    if state["call_status"] == "completed":
        return "complete"
    
    # If we can retry, do so
    if state["retry_count"] < state["max_retries"]:
        logger.info(f"[Workflow] Will retry (attempt {state['retry_count'] + 1}/{state['max_retries']})")
        return "retry"
    
    # Max retries reached, fallback to other channels
    logger.info(f"[Workflow] Max retries reached, moving to fallback")
    return "fallback"


def increment_retry_node(state: LeadState) -> dict:
    """
    Node: Increment retry count and schedule next retry.
    """
    new_retry_count = state["retry_count"] + 1
    
    logger.info(f"[Workflow] Incrementing retry count to {new_retry_count}")
    
    # Update Sheets with retry info
    try:
        from src.sheets_manager import SheetsManager
        from src.retry_manager import RetryManager
        
        sheets_manager = SheetsManager(
            credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
            sheet_id=os.getenv('LEADS_SHEET_ID')
        )
        
        retry_intervals = [float(x) for x in os.getenv('RETRY_INTERVALS', '0.5,24').split(',')]
        retry_manager = RetryManager(
            max_retries=state["max_retries"],
            retry_intervals=retry_intervals,
            interval_unit=os.getenv('RETRY_UNITS', 'hours')
        )
        
        next_retry_time = retry_manager.get_next_retry_time(state["retry_count"])
        
        row_index = sheets_manager.find_row_by_lead_uuid(state["lead_uuid"])
        if row_index is not None:
            sheets_manager.update_lead_fields(row_index, {
                "call_status": "missed",
                "retry_count": str(new_retry_count),
                "next_retry_time": next_retry_time
            })
    except Exception as e:
        logger.warning(f"[Workflow] Failed to update retry info: {e}")
    
    return {
        "retry_count": new_retry_count,
        "call_status": "missed",
        "next_action": "retry"
    }


def whatsapp_fallback_node(state: LeadState) -> dict:
    """
    Node: Send WhatsApp fallback message after max call retries.
    """
    try:
        from src.whatsapp_client import WhatsAppClient
        
        logger.info(f"[Workflow] Sending WhatsApp fallback for lead {state['lead_uuid']}")
        
        # Check if WhatsApp is enabled and configured
        if not os.getenv('WHATSAPP_ENABLE_FALLBACK', 'true').lower() == 'true':
            logger.info("[Workflow] WhatsApp fallback disabled, skipping")
            return {"next_action": "email_fallback"}
        
        template = os.getenv('WHATSAPP_TEMPLATE_FALLBACK')
        if not template:
            logger.warning("[Workflow] No WhatsApp fallback template configured")
            return {"next_action": "email_fallback"}
        
        whatsapp_client = WhatsAppClient(
            access_token=os.getenv('WHATSAPP_ACCESS_TOKEN', 'DUMMY'),
            phone_number_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID', '0'),
            dry_run=os.getenv('WHATSAPP_DRY_RUN', 'false').lower() == 'true'
        )
        
        result = whatsapp_client.send_template(
            to_number_e164=state["whatsapp_number"],
            template_name=template,
            language=os.getenv('WHATSAPP_LANGUAGE', 'en'),
            body_parameters=[state["lead_name"] or "there"]
        )
        
        if "error" not in result:
            logger.info(f"[Workflow] WhatsApp fallback sent successfully")
            
            # Update Sheets
            try:
                from src.sheets_manager import SheetsManager
                sheets_manager = SheetsManager(
                    credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
                    sheet_id=os.getenv('LEADS_SHEET_ID')
                )
                row_index = sheets_manager.find_row_by_lead_uuid(state["lead_uuid"])
                if row_index is not None:
                    sheets_manager.update_fallback_status(row_index, whatsapp_sent=True)
            except Exception:
                pass
            
            return {
                "channels_tried": state["channels_tried"] + ["whatsapp"] if "whatsapp" not in state["channels_tried"] else state["channels_tried"],
                "last_channel": "whatsapp",
                "conversation_history": state["conversation_history"] + [{
                    "timestamp": datetime.now().isoformat(),
                    "channel": "whatsapp",
                    "action": "fallback_sent",
                    "template": template
                }],
                "next_action": "email_fallback"
            }
        else:
            logger.error(f"[Workflow] WhatsApp fallback failed: {result.get('error')}")
            return {"next_action": "email_fallback"}
        
    except Exception as e:
        logger.error(f"[Workflow] WhatsApp node error: {e}", exc_info=True)
        return {"next_action": "email_fallback"}


def email_fallback_node(state: LeadState) -> dict:
    """
    Node: Send email fallback after WhatsApp attempt.
    """
    try:
        from src.email_client import EmailClient
        
        logger.info(f"[Workflow] Sending email fallback for lead {state['lead_uuid']}")
        
        if not state["lead_email"]:
            logger.info("[Workflow] No email address, skipping")
            return {"next_action": "complete"}
        
        email_client = EmailClient(
            dry_run=os.getenv('EMAIL_DRY_RUN', 'true').lower() == 'true'
        )
        
        subject = os.getenv('EMAIL_SUBJECT', 'Missed Call Follow-Up Email')
        body_template = os.getenv('EMAIL_TEMPLATE_BODY', 'Hi {name}, we tried reaching you...')
        body = body_template.format(name=state["lead_name"] or "there")
        
        result = email_client.send(
            to_email=state["lead_email"],
            subject=f"{subject} [Lead:{state['lead_uuid']}]",
            body_text=body,
            extra_headers={'X-Lead-UUID': state['lead_uuid']}
        )
        
        if "error" not in result:
            logger.info(f"[Workflow] Email fallback sent successfully")
            
            # Update Sheets
            try:
                from src.sheets_manager import SheetsManager
                sheets_manager = SheetsManager(
                    credentials_file=os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE'),
                    sheet_id=os.getenv('LEADS_SHEET_ID')
                )
                row_index = sheets_manager.find_row_by_lead_uuid(state["lead_uuid"])
                if row_index is not None:
                    sheets_manager.update_fallback_status(row_index, email_sent=True)
            except Exception:
                pass
            
            return {
                "channels_tried": state["channels_tried"] + ["email"] if "email" not in state["channels_tried"] else state["channels_tried"],
                "last_channel": "email",
                "conversation_history": state["conversation_history"] + [{
                    "timestamp": datetime.now().isoformat(),
                    "channel": "email",
                    "action": "fallback_sent",
                    "subject": subject
                }],
                "next_action": "complete"
            }
        else:
            logger.error(f"[Workflow] Email fallback failed: {result.get('error')}")
            return {"next_action": "complete"}
        
    except Exception as e:
        logger.error(f"[Workflow] Email node error: {e}", exc_info=True)
        return {"next_action": "complete"}


def create_lead_workflow():
    """
    Create and compile the lead engagement workflow.
    
    Returns:
        Compiled LangGraph workflow
    """
    # Create the graph
    workflow = StateGraph(LeadState)
    
    # Add nodes
    workflow.add_node("initiate_call", initiate_call_node)
    workflow.add_node("check_retry", check_retry_node)
    workflow.add_node("increment_retry", increment_retry_node)
    workflow.add_node("whatsapp_fallback", whatsapp_fallback_node)
    workflow.add_node("email_fallback", email_fallback_node)
    
    # Set entry point
    workflow.set_entry_point("initiate_call")
    
    # Add conditional edges from initiate_call
    # Note: In real system, webhook updates the state asynchronously
    # For now, we check retry after call initiation
    workflow.add_edge("initiate_call", "check_retry")
    
    # Add conditional edges from check_retry
    workflow.add_conditional_edges(
        "check_retry",
        check_retry_node,
        {
            "retry": "increment_retry",
            "fallback": "whatsapp_fallback",
            "complete": END
        }
    )
    
    # After incrementing retry, loop back to initiate_call
    workflow.add_edge("increment_retry", "initiate_call")
    
    # Fallback chain: WhatsApp → Email → END
    workflow.add_edge("whatsapp_fallback", "email_fallback")
    workflow.add_edge("email_fallback", END)
    
    # Compile with memory checkpointer for state persistence
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    logger.info("✅ Lead workflow compiled successfully")
    
    return app


# Global workflow instance
_workflow_app = None

def get_workflow():
    """Get or create the global workflow instance."""
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = create_lead_workflow()
    return _workflow_app

