# LangGraph flow logic for conversational appointment booking
import re
import json
from datetime import datetime, timedelta
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import os


class AgentState(TypedDict):
    """State for the conversational AI agent"""
    messages: Annotated[List[BaseMessage], "Messages in the conversation"]
    user_input: str
    intent: str
    extracted_info: Dict[str, Any]
    calendar_data: Dict[str, Any]
    available_slots: List[Dict[str, Any]]
    conversation_stage: str
    response: str
    booking_confirmed: bool


class TailorTalkAgent:
    """Main agent class for tailor-talk conversational AI"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY", "")
        ) if openai_api_key or os.getenv("OPENAI_API_KEY") else None
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("understand_intent", self.understand_intent)
        workflow.add_node("extract_datetime", self.extract_datetime)
        workflow.add_node("check_availability", self.check_availability)
        workflow.add_node("suggest_alternatives", self.suggest_alternatives)
        workflow.add_node("confirm_booking", self.confirm_booking)
        workflow.add_node("generate_response", self.generate_response)
        
        # Add edges with conditional routing
        workflow.add_edge(START, "understand_intent")
        workflow.add_conditional_edges(
            "understand_intent",
            self._route_after_intent,
            {
                "extract_datetime": "extract_datetime",
                "check_availability": "check_availability",
                "confirm_booking": "confirm_booking",
                "generate_response": "generate_response"
            }
        )
        workflow.add_edge("extract_datetime", "check_availability")
        workflow.add_conditional_edges(
            "check_availability",
            self._route_after_availability,
            {
                "suggest_alternatives": "suggest_alternatives",
                "confirm_booking": "confirm_booking",
                "generate_response": "generate_response"
            }
        )
        workflow.add_edge("suggest_alternatives", "generate_response")
        workflow.add_edge("confirm_booking", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def understand_intent(self, state: AgentState) -> AgentState:
        """Understand user intent and conversation stage"""
        user_input = state["user_input"].lower()
        
        # Intent classification
        if any(word in user_input for word in ["book", "schedule", "appointment", "meeting", "call"]):
            state["intent"] = "book_appointment"
        elif any(word in user_input for word in ["available", "free", "time", "slot"]):
            state["intent"] = "check_availability"
        elif any(word in user_input for word in ["yes", "confirm", "book it", "that works"]):
            state["intent"] = "confirm_booking"
        elif any(word in user_input for word in ["no", "different", "other", "alternative"]):
            state["intent"] = "request_alternatives"
        elif any(word in user_input for word in ["cancel", "reschedule", "change"]):
            state["intent"] = "modify_booking"
        else:
            state["intent"] = "general_inquiry"
        
        # Determine conversation stage
        if not state.get("conversation_stage"):
            state["conversation_stage"] = "initial"
        elif state["intent"] == "confirm_booking":
            state["conversation_stage"] = "confirming"
        elif state["available_slots"]:
            state["conversation_stage"] = "presenting_options"
        else:
            state["conversation_stage"] = "gathering_info"
        
        return state
    
    def extract_datetime(self, state: AgentState) -> AgentState:
        """Extract date and time information from user input"""
        user_input = state["user_input"]
        extracted_info = state.get("extracted_info", {})
        
        # Simple datetime extraction patterns
        date_patterns = [
            (r'tomorrow', lambda: datetime.now() + timedelta(days=1)),
            (r'today', lambda: datetime.now()),
            (r'next week', lambda: datetime.now() + timedelta(weeks=1)),
            (r'friday|monday|tuesday|wednesday|thursday|saturday|sunday', self._parse_weekday),
        ]
        
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2})-(\d{1,2})\s*(pm|am)',
            r'afternoon',
            r'morning',
            r'evening'
        ]
        
        # Extract date
        for pattern, handler in date_patterns:
            if re.search(pattern, user_input.lower()):
                if callable(handler):
                    extracted_info["preferred_date"] = handler().date()
                else:
                    extracted_info["preferred_date"] = handler
                break
        
        # Extract time
        for pattern in time_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                extracted_info["time_preference"] = match.group()
                break
        
        # Extract duration if mentioned
        duration_match = re.search(r'(\d+)\s*(hour|minute)', user_input.lower())
        if duration_match:
            extracted_info["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}s"
        else:
            extracted_info["duration"] = "1 hour"  # default
        
        state["extracted_info"] = extracted_info
        return state
    
    def check_availability(self, state: AgentState) -> AgentState:
        """Check calendar availability"""
        from gcal_utils.gcal import GoogleCalendarManager
        
        try:
            calendar_manager = GoogleCalendarManager()
            extracted_info = state.get("extracted_info", {})
            
            # If we have a specific date, check that date
            if "preferred_date" in extracted_info:
                target_date = extracted_info["preferred_date"]
                if isinstance(target_date, str):
                    target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                
                # Convert to datetime for calendar check
                target_datetime = datetime.combine(target_date, datetime.min.time())
                events = calendar_manager.get_events_for_date(target_datetime)
                
                # Generate available slots (simplified logic)
                available_slots = self._generate_available_slots(events, target_datetime)
                state["available_slots"] = available_slots
                state["calendar_data"] = {"events": events, "target_date": target_date}
            else:
                # Get upcoming events for the next few days
                upcoming_events = calendar_manager.get_upcoming_events(20)
                state["calendar_data"] = {"events": upcoming_events}
                
                # Generate available slots for the next 3 days
                available_slots = []
                for i in range(3):
                    date = datetime.now() + timedelta(days=i)
                    day_events = [e for e in upcoming_events if e["start"].startswith(date.strftime("%Y-%m-%d"))]
                    slots = self._generate_available_slots(day_events, date)
                    available_slots.extend(slots)
                
                state["available_slots"] = available_slots[:5]  # Limit to 5 suggestions
                
        except Exception as e:
            print(f"Calendar check failed: {e}")
            # Fallback to mock availability
            state["available_slots"] = self._generate_mock_slots()
            state["calendar_data"] = {"error": str(e)}
        
        return state
    
    def suggest_alternatives(self, state: AgentState) -> AgentState:
        """Suggest alternative time slots"""
        # This would typically generate new alternative slots
        # For now, we'll use the available slots we already have
        if not state.get("available_slots"):
            state["available_slots"] = self._generate_mock_slots()
        
        state["conversation_stage"] = "presenting_alternatives"
        return state
    
    def confirm_booking(self, state: AgentState) -> AgentState:
        """Confirm the booking"""
        if state["intent"] == "confirm_booking" and state.get("available_slots"):
            # In a real implementation, this would book the appointment
            state["booking_confirmed"] = True
            state["conversation_stage"] = "booking_confirmed"
        else:
            state["booking_confirmed"] = False
        
        return state
    
    def generate_response(self, state: AgentState) -> AgentState:
        """Generate appropriate response based on conversation state"""
        intent = state.get("intent", "")
        stage = state.get("conversation_stage", "")
        available_slots = state.get("available_slots", [])
        booking_confirmed = state.get("booking_confirmed", False)
        
        if booking_confirmed:
            response = "Great! I've confirmed your appointment. You should receive a confirmation email shortly. Is there anything else I can help you with?"
        elif stage == "presenting_options" and available_slots:
            response = "I found some available time slots for you:\n\n"
            for i, slot in enumerate(available_slots[:3], 1):
                response += f"{i}. {slot['date']} at {slot['time']} ({slot['duration']})\n"
            response += "\nWhich time works best for you? Just let me know the number or tell me if you'd like to see other options."
        elif stage == "presenting_alternatives":
            response = "Let me suggest some alternative times:\n\n"
            for i, slot in enumerate(available_slots[3:6], 1):
                response += f"{i}. {slot['date']} at {slot['time']} ({slot['duration']})\n"
            response += "\nDo any of these work better for you?"
        elif intent == "check_availability":
            if available_slots:
                response = f"I have several time slots available. Here are some options:\n\n"
                for i, slot in enumerate(available_slots[:3], 1):
                    response += f"{i}. {slot['date']} at {slot['time']}\n"
                response += "\nWould you like to book one of these slots?"
            else:
                response = "I don't see any available slots for your preferred time. Could you suggest an alternative time or date?"
        elif intent == "book_appointment":
            if not state.get("extracted_info", {}).get("preferred_date"):
                response = "I'd be happy to help you schedule an appointment! When would you like to meet? Please let me know your preferred date and time."
            else:
                response = "Let me check availability for your requested time..."
        else:
            response = "Hello! I'm here to help you schedule appointments. When would you like to book a meeting? You can say something like 'I want to schedule a call for tomorrow afternoon' or 'Do you have any free time this Friday?'"
        
        state["response"] = response
        return state
    
    def _route_after_intent(self, state: AgentState) -> str:
        """Route after understanding intent"""
        intent = state.get("intent", "")
        
        if intent == "confirm_booking":
            return "confirm_booking"
        elif intent in ["book_appointment", "check_availability"] and not state.get("extracted_info", {}).get("preferred_date"):
            return "extract_datetime"
        elif intent in ["book_appointment", "check_availability"]:
            return "check_availability"
        else:
            return "generate_response"
    
    def _route_after_availability(self, state: AgentState) -> str:
        """Route after checking availability"""
        available_slots = state.get("available_slots", [])
        intent = state.get("intent", "")
        
        if not available_slots and intent == "request_alternatives":
            return "suggest_alternatives"
        elif available_slots and intent == "confirm_booking":
            return "confirm_booking"
        else:
            return "generate_response"
    
    def _parse_weekday(self, weekday_match):
        """Parse weekday and return next occurrence"""
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        target_weekday = weekdays.get(weekday_match.group().lower())
        if target_weekday is not None:
            today = datetime.now()
            days_ahead = target_weekday - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        return datetime.now() + timedelta(days=1)
    
    def _generate_available_slots(self, events: List[Dict], target_date: datetime) -> List[Dict]:
        """Generate available time slots based on existing events"""
        available_slots = []
        
        # Define working hours (9 AM to 5 PM)
        work_start = target_date.replace(hour=9, minute=0, second=0, microsecond=0)
        work_end = target_date.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Create time slots every hour
        current_time = work_start
        while current_time < work_end:
            slot_end = current_time + timedelta(hours=1)
            
            # Check if this slot conflicts with any existing event
            conflict = False
            for event in events:
                event_start_str = event.get("start", "")
                if event_start_str:
                    try:
                        event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00'))
                        event_start = event_start.replace(tzinfo=None)  # Remove timezone for comparison
                        if current_time <= event_start < slot_end:
                            conflict = True
                            break
                    except:
                        continue
            
            if not conflict:
                available_slots.append({
                    "date": current_time.strftime("%A, %B %d, %Y"),
                    "time": current_time.strftime("%I:%M %p"),
                    "datetime": current_time,
                    "duration": "1 hour"
                })
            
            current_time += timedelta(hours=1)
        
        return available_slots
    
    def _generate_mock_slots(self) -> List[Dict]:
        """Generate mock available slots for demo purposes"""
        slots = []
        base_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        
        for i in range(5):
            slot_time = base_time + timedelta(days=i, hours=i % 3)
            slots.append({
                "date": slot_time.strftime("%A, %B %d, %Y"),
                "time": slot_time.strftime("%I:%M %p"),
                "datetime": slot_time,
                "duration": "1 hour"
            })
        
        return slots
    
    def run(self, user_input: str, current_state: Optional[AgentState] = None) -> Dict[str, Any]:
        """Run the agent with user input"""
        if current_state is None:
            initial_state = AgentState(
                messages=[],
                user_input=user_input,
                intent="",
                extracted_info={},
                calendar_data={},
                available_slots=[],
                conversation_stage="",
                response="",
                booking_confirmed=False
            )
        else:
            initial_state = current_state.copy()
            initial_state["user_input"] = user_input
            initial_state["messages"].append(HumanMessage(content=user_input))
        
        try:
            result = self.graph.invoke(initial_state)
            
            # Add AI response to messages
            if result.get("response"):
                result["messages"].append(AIMessage(content=result["response"]))
            
            return result
        except Exception as e:
            error_response = f"I apologize, but I encountered an error: {str(e)}. Please try again."
            return {
                **initial_state,
                "response": error_response,
                "messages": initial_state["messages"] + [AIMessage(content=error_response)]
            }
