# FastAPI Backend for Tailor-Talk
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import sys
import os
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agent.flow import TailorTalkAgent, AgentState
    from gcal_utils.gcal import GoogleCalendarManager
except ImportError as e:
    print(f"Import error: {e}")
    # Create a dummy class for development
    class GoogleCalendarManager:
        def __init__(self):
            pass

app = FastAPI(
    title="Tailor-Talk API",
    description="AI-powered appointment booking system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
agent_instance = None
calendar_instance = None


# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    intent: str
    conversation_stage: str
    available_slots: List[Dict[str, Any]]
    booking_confirmed: bool
    session_id: str


class BookingRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    summary: str = "AI Booked Appointment"
    description: str = ""
    attendee_email: Optional[str] = None


class BookingResponse(BaseModel):
    success: bool
    event_id: Optional[str] = None
    event_link: Optional[str] = None
    message: str


class AvailabilityRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    duration_minutes: int = 60


class AvailabilityResponse(BaseModel):
    available_slots: List[Dict[str, Any]]
    total_slots: int


# Session management
sessions: Dict[str, AgentState] = {}


def get_agent():
    """Dependency to get agent instance"""
    global agent_instance
    if agent_instance is None:
        agent_instance = TailorTalkAgent()
    return agent_instance


def get_calendar():
    """Dependency to get calendar instance"""
    global calendar_instance
    if calendar_instance is None:
        try:
            calendar_instance = GoogleCalendarManager()
        except Exception as e:
            print(f"Calendar initialization failed: {e}")
            calendar_instance = None
    return calendar_instance


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Tailor-Talk API",
        "version": "1.0.0",
        "endpoints": {
            "/chat": "POST - Chat with the AI agent",
            "/availability": "POST - Check calendar availability",
            "/book": "POST - Book an appointment",
            "/events": "GET - Get upcoming events",
            "/health": "GET - Health check"
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, agent: TailorTalkAgent = Depends(get_agent)):
    """Chat with the AI agent"""
    try:
        # Get or create session state
        session_id = message.session_id
        current_state = sessions.get(session_id)
        
        # Run agent
        result = agent.run(message.message, current_state)
        
        # Update session
        sessions[session_id] = result
        
        return ChatResponse(
            response=result.get("response", ""),
            intent=result.get("intent", ""),
            conversation_stage=result.get("conversation_stage", ""),
            available_slots=result.get("available_slots", []),
            booking_confirmed=result.get("booking_confirmed", False),
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/availability", response_model=AvailabilityResponse)
async def check_availability(
    request: AvailabilityRequest,
    calendar: GoogleCalendarManager = Depends(get_calendar)
):
    """Check calendar availability"""
    try:
        if calendar is None:
            # Return mock data if calendar not available
            mock_slots = []
            current_time = request.start_date
            while current_time < request.end_date:
                if current_time.hour >= 9 and current_time.hour < 17:  # Business hours
                    mock_slots.append({
                        "start": current_time,
                        "end": current_time + timedelta(minutes=request.duration_minutes),
                        "date": current_time.strftime("%A, %B %d, %Y"),
                        "time": current_time.strftime("%I:%M %p"),
                        "duration": f"{request.duration_minutes} minutes"
                    })
                current_time += timedelta(hours=1)
                
            return AvailabilityResponse(
                available_slots=mock_slots[:10],  # Limit to 10 slots
                total_slots=len(mock_slots)
            )
        
        free_slots = calendar.get_free_slots(
            start_date=request.start_date,
            end_date=request.end_date,
            duration_minutes=request.duration_minutes
        )
        
        return AvailabilityResponse(
            available_slots=free_slots,
            total_slots=len(free_slots)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/book", response_model=BookingResponse)
async def book_appointment(
    request: BookingRequest,
    calendar: GoogleCalendarManager = Depends(get_calendar)
):
    """Book an appointment"""
    try:
        if calendar is None:
            # Mock booking response
            return BookingResponse(
                success=True,
                event_id="mock_event_123",
                event_link="https://calendar.google.com/mock",
                message="Appointment booked successfully (demo mode)"
            )
        
        result = calendar.book_appointment(
            start_time=request.start_time,
            end_time=request.end_time,
            summary=request.summary,
            description=request.description,
            attendee_email=request.attendee_email
        )
        
        if result.get("success"):
            return BookingResponse(
                success=True,
                event_id=result.get("event_id"),
                event_link=result.get("event_link"),
                message="Appointment booked successfully"
            )
        else:
            return BookingResponse(
                success=False,
                message=f"Failed to book appointment: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events")
async def get_events(
    max_results: int = 10,
    calendar: GoogleCalendarManager = Depends(get_calendar)
):
    """Get upcoming events"""
    try:
        if calendar is None:
            return {
                "events": [],
                "message": "Calendar not connected - using demo mode"
            }
        
        events = calendar.get_upcoming_events(max_results)
        return {
            "events": events,
            "count": len(events)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        agent_status = "OK" if agent_instance else "Not initialized"
        calendar_status = "OK" if calendar_instance else "Not connected"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "agent": agent_status,
                "calendar": calendar_status
            },
            "sessions": len(sessions)
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} cleared"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@app.delete("/sessions")
async def clear_all_sessions():
    """Clear all sessions"""
    global sessions
    count = len(sessions)
    sessions = {}
    return {"message": f"Cleared {count} sessions"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
