# Google Calendar integration utilities with booking capabilities
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Google Calendar dependencies not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")


# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]


class GoogleCalendarManager:
    """Manager for Google Calendar operations including booking"""
    
    def __init__(self, credentials_file: str = "credentials.json"):
        self.credentials_file = credentials_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        creds = None
        
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = None
                
                # Check for Streamlit secrets first
                if self._has_streamlit_secrets():
                    flow = self._create_flow_from_secrets()
                # Then check for environment variables
                elif self._has_env_vars():
                    flow = self._create_flow_from_env()
                # Finally, check for credentials file
                elif os.path.exists(self.credentials_file):
                    try:
                        # Try to read and parse the credentials file
                        with open(self.credentials_file, 'r') as f:
                            credentials_data = json.load(f)
                        
                        # Handle both "web" and "installed" app types
                        if 'web' in credentials_data:
                            # Convert web credentials to installed app format for local OAuth
                            client_config = {
                                "installed": {
                                    "client_id": credentials_data['web']['client_id'],
                                    "client_secret": credentials_data['web']['client_secret'],
                                    "project_id": credentials_data['web']['project_id'],
                                    "auth_uri": credentials_data['web']['auth_uri'],
                                    "token_uri": credentials_data['web']['token_uri'],
                                    "auth_provider_x509_cert_url": credentials_data['web']['auth_provider_x509_cert_url'],
                                    "redirect_uris": ["http://localhost"]
                                }
                            }
                            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                        else:
                            # Standard installed app credentials
                            flow = InstalledAppFlow.from_client_secrets_file(
                                self.credentials_file, SCOPES)
                    except Exception as e:
                        print(f"Error reading credentials file: {e}")
                        raise FileNotFoundError(f"Invalid credentials file format: {e}")
                else:
                    raise FileNotFoundError(f"No credentials found. Please provide {self.credentials_file}, environment variables, or Streamlit secrets.")
                
                if flow:
                    try:
                        creds = flow.run_local_server(port=0)
                    except Exception as e:
                        print(f"OAuth flow failed: {e}")
                        # Try alternative port
                        try:
                            creds = flow.run_local_server(port=8080)
                        except Exception as e2:
                            print(f"OAuth flow failed on alternative port: {e2}")
                            raise Exception(f"Failed to complete OAuth flow: {e2}")
            
            # Save the credentials for the next run
            try:
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"Warning: Could not save token: {e}")
        
        self.service = build('calendar', 'v3', credentials=creds)
    
    def _has_streamlit_secrets(self):
        """Check if running in Streamlit with secrets"""
        try:
            import streamlit as st
            return hasattr(st, 'secrets') and 'google_calendar' in st.secrets
        except:
            return False
    
    def _has_env_vars(self):
        """Check if required environment variables are present"""
        required_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_PROJECT_ID']
        return all(os.getenv(var) for var in required_vars)
    
    def _create_flow_from_secrets(self):
        """Create OAuth flow from Streamlit secrets"""
        import streamlit as st
        client_config = {
            "web": {
                "client_id": st.secrets.google_calendar.client_id,
                "client_secret": st.secrets.google_calendar.client_secret,
                "project_id": st.secrets.google_calendar.project_id,
                "auth_uri": st.secrets.google_calendar.auth_uri,
                "token_uri": st.secrets.google_calendar.token_uri,
                "auth_provider_x509_cert_url": st.secrets.google_calendar.auth_provider_x509_cert_url
            }
        }
        return InstalledAppFlow.from_client_config(client_config, SCOPES)
    
    def _create_flow_from_env(self):
        """Create OAuth flow from environment variables"""
        client_config = {
            "web": {
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                "project_id": os.getenv('GOOGLE_PROJECT_ID'),
                "auth_uri": os.getenv('GOOGLE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
                "token_uri": os.getenv('GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
                "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs')
            }
        }
        return InstalledAppFlow.from_client_config(client_config, SCOPES)
    
    def get_upcoming_events(self, max_results: int = 10) -> List[Dict]:
        """Get upcoming events from the primary calendar"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                formatted_events.append({
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end,
                    'id': event.get('id'),
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                })
            
            return formatted_events
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_events_for_date(self, date: datetime) -> List[Dict]:
        """Get events for a specific date"""
        try:
            # Start and end of the day
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                formatted_events.append({
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end,
                    'id': event.get('id'),
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                })
            
            return formatted_events
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_free_slots(self, start_date: datetime, end_date: datetime, 
                      duration_minutes: int = 60, 
                      working_hours: tuple = (9, 17)) -> List[Dict]:
        """Get available time slots between start_date and end_date"""
        try:
            # Get all events in the time range
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Extract busy periods
            busy_periods = []
            for event in events:
                start_str = event['start'].get('dateTime')
                end_str = event['end'].get('dateTime')
                
                if start_str and end_str:
                    try:
                        start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        busy_periods.append((start_time, end_time))
                    except:
                        continue
            
            # Sort busy periods
            busy_periods.sort(key=lambda x: x[0])
            
            # Generate free slots
            free_slots = []
            current_date = start_date.date()
            end_search_date = end_date.date()
            
            while current_date <= end_search_date:
                # Define working hours for the day
                day_start = datetime.combine(current_date, datetime.min.time()).replace(hour=working_hours[0])
                day_end = datetime.combine(current_date, datetime.min.time()).replace(hour=working_hours[1])
                
                # Find free slots for this day
                current_time = day_start
                
                while current_time + timedelta(minutes=duration_minutes) <= day_end:
                    slot_end = current_time + timedelta(minutes=duration_minutes)
                    
                    # Check if this slot conflicts with any busy period
                    is_free = True
                    for busy_start, busy_end in busy_periods:
                        if (current_time < busy_end and slot_end > busy_start):
                            is_free = False
                            # Skip to after this busy period
                            current_time = busy_end
                            break
                    
                    if is_free:
                        free_slots.append({
                            'start': current_time,
                            'end': slot_end,
                            'date': current_time.strftime("%A, %B %d, %Y"),
                            'time': current_time.strftime("%I:%M %p"),
                            'duration': f"{duration_minutes} minutes"
                        })
                        current_time += timedelta(minutes=duration_minutes)
                    
                    # Prevent infinite loop
                    if current_time >= day_end:
                        break
                
                current_date += timedelta(days=1)
            
            return free_slots
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def book_appointment(self, start_time: datetime, end_time: datetime, 
                        summary: str = "Appointment", 
                        description: str = "", 
                        attendee_email: str = None) -> Dict:
        """Book an appointment in the calendar"""
        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            if attendee_email:
                event['attendees'] = [{'email': attendee_email}]
            
            created_event = self.service.events().insert(
                calendarId='primary', 
                body=event
            ).execute()
            
            return {
                'success': True,
                'event_id': created_event.get('id'),
                'event_link': created_event.get('htmlLink'),
                'summary': summary,
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
            
        except HttpError as error:
            print(f'An error occurred while booking: {error}')
            return {
                'success': False,
                'error': str(error)
            }
    
    def search_events(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for events containing the query string"""
        try:
            events_result = self.service.events().list(
                calendarId='primary',
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                formatted_events.append({
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end,
                    'id': event.get('id'),
                    'description': event.get('description', ''),
                    'location': event.get('location', '')
                })
            
            return formatted_events
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def cancel_appointment(self, event_id: str) -> Dict:
        """Cancel an appointment by event ID"""
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            return {
                'success': True,
                'message': 'Appointment cancelled successfully'
            }
            
        except HttpError as error:
            print(f'An error occurred while cancelling: {error}')
            return {
                'success': False,
                'error': str(error)
            }
