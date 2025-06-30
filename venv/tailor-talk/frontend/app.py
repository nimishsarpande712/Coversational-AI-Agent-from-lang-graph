# Tailor-Talk: Enhanced Streamlit Frontend for Appointment Booking
import streamlit as st
import sys
import os
from datetime import datetime, timedelta
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agent.flow import TailorTalkAgent, AgentState
    from gcal_utils.gcal import GoogleCalendarManager
except ImportError as e:
    st.error(f"Required modules not found: {e}. Please ensure all dependencies are installed.")
    st.stop()


def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    if 'calendar_manager' not in st.session_state:
        st.session_state.calendar_manager = None
    if 'agent_state' not in st.session_state:
        st.session_state.agent_state = None
    if 'conversation_active' not in st.session_state:
        st.session_state.conversation_active = False
    if 'selected_slot' not in st.session_state:
        st.session_state.selected_slot = None
    if 'message_counter' not in st.session_state:
        st.session_state.message_counter = 0
    if 'booking_in_progress' not in st.session_state:
        st.session_state.booking_in_progress = False


def setup_sidebar():
    """Setup the sidebar with configuration options"""
    st.sidebar.title("🔧 Configuration")
    
    # OpenAI API Key
    st.sidebar.subheader("OpenAI Settings")
    openai_key = st.sidebar.text_input(
        "OpenAI API Key (Optional)", 
        type="password",
        help="Enter your OpenAI API key for enhanced responses"
    )
    
    # Agent setup
    st.sidebar.subheader("🤖 AI Agent")
    if st.sidebar.button("Initialize Agent"):
        try:
            st.session_state.agent = TailorTalkAgent(openai_api_key=openai_key if openai_key else None)
            st.sidebar.success("Agent initialized successfully!")
            st.session_state.conversation_active = True
        except Exception as e:
            st.sidebar.error(f"Failed to initialize agent: {str(e)}")
    
    # Calendar setup
    st.sidebar.subheader("📅 Google Calendar")
    if st.sidebar.button("Connect Calendar"):
        try:
            with st.spinner("Connecting to Google Calendar..."):
                st.session_state.calendar_manager = GoogleCalendarManager()
            st.sidebar.success("Calendar connected successfully!")
        except FileNotFoundError as e:
            st.sidebar.error(f"Credentials not found: {str(e)}")
            st.sidebar.info("Please ensure credentials.json is in the project root directory.")
        except Exception as e:
            st.sidebar.error(f"Failed to connect calendar: {str(e)}")
            st.sidebar.info("Calendar connection failed. Using mock data for demo.")
            # Set to None to trigger mock mode
            st.session_state.calendar_manager = None
    
    # Display status
    st.sidebar.subheader("📊 Status")
    calendar_status = "✅ Connected" if st.session_state.calendar_manager else "❌ Not connected (using mock data)"
    agent_status = "✅ Ready" if st.session_state.agent else "❌ Not initialized"
    
    st.sidebar.write(f"**Calendar:** {calendar_status}")
    st.sidebar.write(f"**Agent:** {agent_status}")
    
    # Demo buttons
    st.sidebar.subheader("🎯 Quick Start")
    demo_phrases = [
        "I want to schedule a meeting tomorrow afternoon",
        "Do you have any free time this Friday?",
        "Book a call between 3-5 PM next week"
    ]
    
    for phrase in demo_phrases:
        if st.sidebar.button(f"💬 \"{phrase[:20]}...\"", key=f"demo_{phrase[:10]}"):
            if st.session_state.agent:
                handle_demo_input(phrase)
            else:
                st.sidebar.warning("Please initialize the agent first!")
    
    # Clear conversation button
    st.sidebar.subheader("🔄 Actions")
    if st.sidebar.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.session_state.agent_state = None
        st.session_state.selected_slot = None
        st.session_state.booking_in_progress = False
        st.rerun()


def handle_demo_input(phrase):
    """Handle demo input phrase"""
    st.session_state.messages.append({"role": "user", "content": phrase})
    
    # Process with agent
    try:
        result = st.session_state.agent.run(phrase, st.session_state.agent_state)
        st.session_state.agent_state = result
        
        response = result.get("response", "I'm processing your request...")
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Force rerun to update the chat
        st.rerun()
        
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        st.rerun()


def display_chat_messages():
    """Display chat messages with enhanced formatting"""
    for msg_idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                # Enhanced formatting for assistant messages
                content = message["content"]
                if "time slots" in content.lower() or "available" in content.lower():
                    st.markdown(content)
                    
                    # If agent state has available slots, show interactive buttons
                    if (st.session_state.agent_state and 
                        st.session_state.agent_state.get("available_slots") and
                        "Which time works best" in content):
                        
                        available_slots = st.session_state.agent_state["available_slots"][:3]
                        st.write("**Quick Selection:**")
                        
                        cols = st.columns(len(available_slots))
                        for i, slot in enumerate(available_slots):
                            with cols[i]:
                                if st.button(
                                    f"📅 {slot['time']}\n{slot['date'][:10]}", 
                                    key=f"slot_{i}_{msg_idx}_{len(st.session_state.messages)}_{hash(str(slot))}"
                                ):
                                    confirm_booking(slot, i+1)
                else:
                    st.markdown(content)
            else:
                st.markdown(message["content"])


def confirm_booking(slot, slot_number):
    """Confirm booking for selected slot"""
    # Prevent duplicate confirmations
    if st.session_state.get('booking_in_progress'):
        return
    
    st.session_state.booking_in_progress = True
    st.session_state.selected_slot = slot
    st.session_state.message_counter += 1
    
    confirmation_message = f"Great! You selected option {slot_number}: {slot['date']} at {slot['time']}. Shall I book this appointment for you?"
    
    st.session_state.messages.append({"role": "assistant", "content": confirmation_message})
    
    # Process confirmation with agent
    try:
        result = st.session_state.agent.run("yes, book it", st.session_state.agent_state)
        st.session_state.agent_state = result
        
        if result.get("booking_confirmed"):
            # Actually book the appointment if calendar is connected
            if st.session_state.calendar_manager and slot.get("datetime"):
                try:
                    start_time = slot["datetime"]
                    end_time = start_time + timedelta(hours=1)
                    
                    booking_result = st.session_state.calendar_manager.book_appointment(
                        start_time=start_time,
                        end_time=end_time,
                        summary="Appointment booked via Tailor-Talk",
                        description="Appointment scheduled through AI assistant"
                    )
                    
                    if booking_result.get("success"):
                        success_msg = f"✅ Perfect! Your appointment has been booked for {slot['date']} at {slot['time']}. You should receive a calendar invite shortly."
                    else:
                        success_msg = f"⚠️ Appointment confirmed in our system for {slot['date']} at {slot['time']}, but there was an issue with the calendar booking: {booking_result.get('error', 'Unknown error')}"
                        
                except Exception as e:
                    success_msg = f"✅ Appointment confirmed for {slot['date']} at {slot['time']}. (Calendar booking failed: {str(e)})"
            else:
                success_msg = f"✅ Perfect! Your appointment has been confirmed for {slot['date']} at {slot['time']}. (Demo mode - no actual calendar booking)"
            
            st.session_state.messages.append({"role": "assistant", "content": success_msg})
        
        st.session_state.booking_in_progress = False
        st.rerun()
        
    except Exception as e:
        error_msg = f"An error occurred while booking: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        st.session_state.booking_in_progress = False
        st.rerun()


def handle_user_input():
    """Handle user input and generate response"""
    if prompt := st.chat_input("What can I help you with today? 💬"):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            if st.session_state.agent:
                try:
                    with st.spinner("Thinking..."):
                        result = st.session_state.agent.run(prompt, st.session_state.agent_state)
                        st.session_state.agent_state = result
                        
                        response = result.get("response", "I'm sorry, I couldn't process your request.")
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # Handle special cases
                        if result.get("booking_confirmed"):
                            st.balloons()
                            
                except Exception as e:
                    error_msg = f"An error occurred: {str(e)}"
                    st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                error_msg = "Please initialize the agent first using the sidebar."
                st.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})


def display_calendar_events():
    """Display upcoming calendar events"""
    st.subheader("📅 Upcoming Events")
    
    if st.session_state.calendar_manager:
        try:
            with st.spinner("Loading calendar events..."):
                events = st.session_state.calendar_manager.get_upcoming_events(5)
            
            if events:
                for event in events:
                    with st.expander(f"📅 {event['summary']}", expanded=False):
                        start_time = event['start']
                        if 'T' in start_time:  # DateTime format
                            formatted_start = datetime.fromisoformat(start_time.replace('Z', '+00:00')).strftime("%B %d, %Y at %I:%M %p")
                        else:  # Date format
                            formatted_start = datetime.fromisoformat(start_time).strftime("%B %d, %Y")
                        
                        st.write(f"**📅 Start:** {formatted_start}")
                        if event['description']:
                            st.write(f"**📝 Description:** {event['description']}")
                        if event['location']:
                            st.write(f"**📍 Location:** {event['location']}")
            else:
                st.info("No upcoming events found.")
                
        except Exception as e:
            st.error(f"Failed to fetch calendar events: {str(e)}")
            st.info("Using demo mode - no actual calendar events shown.")
    else:
        st.info("📝 Calendar not connected. Here's what you can do:")
        st.markdown("""
        1. **Connect your Google Calendar** using the sidebar
        2. **Try some example phrases:**
           - "I want to schedule a meeting tomorrow"
           - "Do you have any free time this Friday?"
           - "Book a call between 2-4 PM next week"
        3. **Natural conversation** - just ask in plain English!
        """)


def display_agent_debug_info():
    """Display agent state for debugging (collapsible)"""
    if st.session_state.agent_state and st.sidebar.checkbox("🔍 Debug Info"):
        with st.sidebar.expander("Agent State", expanded=False):
            st.json({
                "intent": st.session_state.agent_state.get("intent", ""),
                "conversation_stage": st.session_state.agent_state.get("conversation_stage", ""),
                "extracted_info": st.session_state.agent_state.get("extracted_info", {}),
                "available_slots_count": len(st.session_state.agent_state.get("available_slots", [])),
                "booking_confirmed": st.session_state.agent_state.get("booking_confirmed", False)
            })


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="Tailor-Talk AI Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
    }
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .status-connected {
        background-color: #d4edda;
        color: #155724;
    }
    .status-disconnected {
        background-color: #f8d7da;
        color: #721c24;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Tailor-Talk AI Assistant</h1>
        <p>Your intelligent appointment booking assistant powered by LangGraph</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    initialize_session_state()
    
    # Setup sidebar
    setup_sidebar()
    display_agent_debug_info()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 Chat with Your Assistant")
        
        # Welcome message for new users
        if not st.session_state.messages:
            st.info("👋 Welcome! I'm your AI appointment booking assistant. Start by saying something like 'I want to schedule a meeting' or use the quick start options in the sidebar!")
        
        display_chat_messages()
        handle_user_input()
    
    with col2:
        display_calendar_events()
        
        # Quick stats
        if st.session_state.agent_state:
            st.subheader("📊 Session Stats")
            stats_data = {
                "Messages": len(st.session_state.messages),
                "Intent": st.session_state.agent_state.get("intent", "None").title(),
                "Stage": st.session_state.agent_state.get("conversation_stage", "None").title(),
                "Available Slots": len(st.session_state.agent_state.get("available_slots", []))
            }
            
            for key, value in stats_data.items():
                st.metric(key, value)
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; color: #666;">
            <p><em>Powered by LangGraph, Streamlit, and Google Calendar API</em></p>
            <p>🔒 Your data is secure and private</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
