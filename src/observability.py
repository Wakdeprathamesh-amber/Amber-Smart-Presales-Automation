"""
Observability and tracing with LangFuse.
Provides decorators and utilities for tracing calls, workflows, and conversations.
"""

import os
import logging
import json
from functools import wraps
from datetime import datetime
from src.utils import get_ist_timestamp, get_ist_now
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Global LangFuse client
_langfuse_client = None


def get_langfuse_client():
    """
    Get or create the global LangFuse client.
    Returns None if LangFuse is not configured (graceful degradation).
    """
    global _langfuse_client
    
    # Check if observability is enabled
    if os.getenv('ENABLE_OBSERVABILITY', 'true').lower() != 'true':
        logger.info("Observability disabled (ENABLE_OBSERVABILITY=false)")
        return None
    
    if _langfuse_client is not None:
        return _langfuse_client
    
    # Check if LangFuse credentials are configured
    public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
    secret_key = os.getenv('LANGFUSE_SECRET_KEY')
    host = os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')  # Default to US region
    
    if not public_key or not secret_key:
        logger.warning(
            "LangFuse not configured (missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY). "
            "Observability will be disabled. Set keys in .env to enable."
        )
        return None
    
    try:
        from langfuse import Langfuse
        
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            debug=os.getenv('LANGFUSE_DEBUG', 'false').lower() == 'true'
        )
        
        logger.info(f"✅ LangFuse client initialized (host: {host})")
        return _langfuse_client
        
    except ImportError:
        logger.warning("LangFuse library not installed. Observability disabled.")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize LangFuse: {e}")
        return None


def trace_vapi_call(func):
    """
    Decorator to trace Vapi call initiation.
    Creates a trace in LangFuse for the entire call lifecycle.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        langfuse = get_langfuse_client()
        
        # If LangFuse not configured, just run the function normally
        if langfuse is None:
            return func(*args, **kwargs)
        
        # Extract lead data from arguments
        lead_data = kwargs.get('lead_data') or (args[1] if len(args) > 1 else {})
        lead_uuid = lead_data.get('lead_uuid', 'unknown')
        lead_name = lead_data.get('name', 'Unknown')
        lead_number = lead_data.get('number', 'Unknown')
        partner = lead_data.get('partner', 'Unknown')
        
        # Create or update trace for this lead
        trace = langfuse.trace(
            id=lead_uuid,  # Use lead_uuid as trace ID for continuity
            name="lead_call_journey",
            user_id=lead_uuid,
            metadata={
                "lead_name": lead_name,
                "lead_number": lead_number,
                "partner": partner,
                "timestamp": get_ist_timestamp()
            },
            tags=["vapi", "outbound_call", "voice", "call_initiation"]
        )
        
        try:
            # Execute the actual function
            result = func(*args, **kwargs)
            
            # Add span for call initiation
            if "error" in result:
                trace.span(
                    name="call_initiation",
                    input={
                        "lead_uuid": lead_uuid,
                        "lead_name": lead_name,
                        "lead_number": lead_number,
                        "assistant_id": kwargs.get('assistant_id') or (args[2] if len(args) > 2 else None),
                        "phone_number_id": kwargs.get('phone_number_id') or (args[3] if len(args) > 3 else None)
                    },
                    output={"error": result.get("error")},
                    level="ERROR",
                    status_message=f"Call initiation failed: {result.get('error')}",
                    metadata={"timestamp": get_ist_timestamp()}
                )
            else:
                trace.span(
                    name="call_initiation",
                    input={
                        "lead_uuid": lead_uuid,
                        "lead_name": lead_name,
                        "lead_number": lead_number,
                        "assistant_id": kwargs.get('assistant_id') or (args[2] if len(args) > 2 else None),
                        "phone_number_id": kwargs.get('phone_number_id') or (args[3] if len(args) > 3 else None)
                    },
                    output={
                        "call_id": result.get('id'),
                        "status": "initiated"
                    },
                    level="DEFAULT",
                    status_message="Call initiated successfully",
                    metadata={
                        "vapi_call_id": result.get('id'),
                        "timestamp": get_ist_timestamp()
                    }
                )
            
            langfuse.flush()
            return result
            
        except Exception as e:
            # Log exception
            trace.span(
                name="call_initiation",
                input={"lead_uuid": lead_uuid},
                output={"exception": str(e)},
                level="ERROR",
                status_message=f"Call initiation exception: {str(e)}",
                metadata={"timestamp": get_ist_timestamp()}
            )
            langfuse.flush()
            raise
    
    return wrapper


def trace_webhook_event(event_type: str, lead_uuid: str, event_data: Dict[str, Any]) -> Optional[Any]:
    """
    Trace webhook events (status updates, end-of-call reports).
    
    Args:
        event_type: Type of webhook event (status-update, end-of-call-report)
        lead_uuid: UUID of the lead
        event_data: Full webhook payload
        
    Returns:
        Span object or None if LangFuse not configured
    """
    langfuse = get_langfuse_client()
    
    if langfuse is None:
        return None
    
    try:
        # Create span for this webhook event
        span = langfuse.span(
            name=f"webhook_{event_type}",
            trace_id=lead_uuid,  # Group all events for same lead
            input=event_data,
            metadata={
                "event_type": event_type,
                "timestamp": get_ist_timestamp()
            },
            level="DEFAULT"
        )
        
        return span
        
    except Exception as e:
        logger.warning(f"Failed to create webhook span: {e}")
        return None


def log_call_analysis(
    lead_uuid: str,
    summary: str,
    success_status: str,
    structured_data: Dict[str, Any],
    call_id: Optional[str] = None,
    transcript: Optional[str] = None,
    call_duration: Optional[int] = None,
    recording_url: Optional[str] = None
):
    """
    Log AI analysis results from end-of-call report with full details.
    
    Args:
        lead_uuid: UUID of the lead
        summary: AI-generated call summary
        success_status: Qualification status (qualified, unqualified, etc.)
        structured_data: Extracted structured data
        call_id: Vapi call ID
        transcript: Full call transcript
        call_duration: Duration in seconds
        recording_url: URL to call recording
    """
    langfuse = get_langfuse_client()
    
    if langfuse is None:
        return
    
    try:
        # Get or create trace for this lead
        trace = langfuse.trace(
            id=lead_uuid,
            name="lead_call_journey",
            user_id=lead_uuid,
            metadata={
                "call_id": call_id,
                "timestamp": get_ist_timestamp()
            },
            tags=["call", "analysis", "post_call"]
        )
        
        # Add generation for AI analysis
        trace.generation(
            name="call_analysis",
            model="vapi_assistant",
            input={
                "call_id": call_id,
                "transcript_length": len(transcript) if transcript else 0
            },
            output={
                "summary": summary,
                "success_status": success_status,
                "structured_data": structured_data
            },
            metadata={
                "analysis_type": "post_call",
                "call_duration": call_duration,
                "recording_url": recording_url,
                "timestamp": get_ist_timestamp()
            },
            level="DEFAULT",
            status_message=f"Call analyzed: {success_status}"
        )
        
        # Add transcript as a separate event if available
        if transcript:
            trace.event(
                name="call_transcript",
                input={"transcript": transcript[:1000]},  # First 1000 chars
                metadata={
                    "full_length": len(transcript),
                    "call_id": call_id,
                    "timestamp": get_ist_timestamp()
                },
                level="DEFAULT"
            )
        
        # Add call metrics as scores
        if success_status:
            # Map success status to numeric score
            status_scores = {
                "qualified": 1.0,
                "potential": 0.7,
                "not qualified": 0.3,
                "not_qualified": 0.3
            }
            score_value = status_scores.get(success_status.lower(), 0.5)
            
            trace.score(
                name="lead_qualification",
                value=score_value,
                comment=f"Status: {success_status}"
            )
        
        if call_duration:
            # Normalize call duration to 0-1 scale (0-600 seconds = 0-1)
            duration_score = min(call_duration / 600.0, 1.0)
            trace.score(
                name="call_duration",
                value=duration_score,
                comment=f"{call_duration} seconds"
            )
        
        langfuse.flush()
        
    except Exception as e:
        logger.warning(f"Failed to log call analysis: {e}")


def log_conversation_message(
    lead_uuid: str,
    channel: str,
    direction: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log individual conversation messages across channels.
    
    Args:
        lead_uuid: UUID of the lead
        channel: Communication channel (call, whatsapp, email)
        direction: Message direction (in, out)
        content: Message content
        metadata: Additional metadata
    """
    langfuse = get_langfuse_client()
    
    if langfuse is None:
        return
    
    try:
        langfuse.span(
            name=f"message_{channel}_{direction}",
            trace_id=lead_uuid,
            input={"content": content},
            metadata={
                "channel": channel,
                "direction": direction,
                "timestamp": get_ist_timestamp(),
                **(metadata or {})
            },
            level="DEBUG"
        )
        
        langfuse.flush()
        
    except Exception as e:
        logger.warning(f"Failed to log conversation message: {e}")


def trace_workflow_node(node_name: str):
    """
    Decorator to trace LangGraph workflow node execution.
    
    Args:
        node_name: Name of the workflow node
    """
    def decorator(func):
        @wraps(func)
        def wrapper(state, *args, **kwargs):
            langfuse = get_langfuse_client()
            
            if langfuse is None:
                return func(state, *args, **kwargs)
            
            lead_uuid = state.get('lead_uuid', 'unknown')
            
            try:
                # Create span for node execution
                span = langfuse.span(
                    name=f"workflow_node_{node_name}",
                    trace_id=lead_uuid,
                    input={
                        "state": {
                            "call_status": state.get('call_status'),
                            "retry_count": state.get('retry_count'),
                            "channels_tried": state.get('channels_tried'),
                            "next_action": state.get('next_action')
                        }
                    },
                    metadata={
                        "node_name": node_name,
                        "timestamp": get_ist_timestamp()
                    },
                    level="DEFAULT"
                )
                
                # Execute node
                result = func(state, *args, **kwargs)
                
                # Log output
                span.end(
                    output={
                        "result": result if isinstance(result, dict) else str(result)
                    },
                    level="DEFAULT",
                    status_message=f"Node '{node_name}' completed"
                )
                
                langfuse.flush()
                return result
                
            except Exception as e:
                logger.error(f"Workflow node '{node_name}' failed: {e}")
                
                if 'span' in locals():
                    span.end(
                        output={"error": str(e)},
                        level="ERROR",
                        status_message=f"Node '{node_name}' failed: {str(e)}"
                    )
                    langfuse.flush()
                
                raise
        
        return wrapper
    return decorator


def create_score(
    trace_id: str,
    name: str,
    value: float,
    comment: Optional[str] = None
):
    """
    Create a score for a trace (e.g., call quality, conversation success).
    
    Args:
        trace_id: Trace ID (typically lead_uuid)
        name: Score name (e.g., "call_quality", "qualification_accuracy")
        value: Score value (0.0 to 1.0)
        comment: Optional comment
    """
    langfuse = get_langfuse_client()
    
    if langfuse is None:
        return
    
    try:
        langfuse.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment
        )
        
        langfuse.flush()
        
    except Exception as e:
        logger.warning(f"Failed to create score: {e}")


def flush_langfuse():
    """Manually flush all pending LangFuse events."""
    langfuse = get_langfuse_client()
    
    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            logger.warning(f"Failed to flush LangFuse: {e}")


# Context manager for tracing
class LangFuseTrace:
    """Context manager for creating LangFuse traces."""
    
    def __init__(self, name: str, user_id: str, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.user_id = user_id
        self.metadata = metadata or {}
        self.trace = None
        self.langfuse = get_langfuse_client()
    
    def __enter__(self):
        if self.langfuse:
            self.trace = self.langfuse.trace(
                name=self.name,
                user_id=self.user_id,
                metadata=self.metadata
            )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.trace:
            if exc_type:
                self.trace.update(
                    output={"error": str(exc_val)},
                    level="ERROR",
                    status_message=f"Failed: {str(exc_val)}"
                )
            else:
                self.trace.update(
                    level="DEFAULT",
                    status_message="Completed successfully"
                )
            
            self.langfuse.flush()
        
        return False  # Don't suppress exceptions

