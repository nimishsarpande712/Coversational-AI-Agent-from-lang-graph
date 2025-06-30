#!/usr/bin/env python3
"""
Simple script to complete Google Calendar OAuth authentication
Run this once to generate token.json file
"""

import os
import sys
import json
from gcal_utils.gcal import GoogleCalendarManager

def main():
    print("🚀 Tailor-Talk Google Calendar Setup")
    print("=" * 50)
    
    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print("📝 Please ensure your Google Calendar API credentials are in credentials.json")
        return
    
    # Check if token.json already exists
    if os.path.exists('token.json'):
        print("✅ token.json already exists!")
        response = input("🔄 Do you want to re-authenticate? (y/N): ")
        if response.lower() != 'y':
            print("👍 Using existing authentication.")
            return
        else:
            os.remove('token.json')
            print("🗑️ Removed existing token.json")
    
    print("\n🔐 Starting Google Calendar authentication...")
    print("📋 A browser window will open for authorization.")
    print("⏱️ Please complete the process within 5 minutes.")
    print("\n" + "="*50)
    
    try:
        # Initialize the calendar manager (this will trigger OAuth)
        calendar_manager = GoogleCalendarManager()
        
        print("\n✅ Authentication successful!")
        print("🎉 Google Calendar is now connected!")
        
        # Test the connection
        print("\n🧪 Testing connection...")
        try:
            events = calendar_manager.get_upcoming_events(5)
            print(f"📅 Found {len(events)} upcoming events")
            
            if events:
                print("\n📋 Your upcoming events:")
                for i, event in enumerate(events[:3], 1):
                    print(f"  {i}. {event['summary']} - {event['start']}")
            else:
                print("📅 No upcoming events found (calendar might be empty)")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not fetch events: {e}")
        
        print("\n🎊 Setup complete! You can now use the Streamlit app.")
        print("▶️ Run: streamlit run frontend/app.py")
        
    except KeyboardInterrupt:
        print("\n⏹️ Authentication cancelled by user.")
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Ensure your credentials.json is valid")
        print("2. Check that Google Calendar API is enabled")
        print("3. Verify OAuth consent screen is configured")
        print("4. Make sure redirect URIs include http://localhost")

if __name__ == "__main__":
    main()
