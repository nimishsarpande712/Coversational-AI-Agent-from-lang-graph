#!/usr/bin/env python3
"""
OAuth Setup and Troubleshooting Script for Google Calendar Integration
This script helps diagnose and fix common OAuth issues.
"""

import os
import json
import webbrowser
from pathlib import Path

def check_credentials_file():
    """Check the credentials.json file format and provide guidance"""
    print("🔍 Checking credentials.json file...")
    
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print("\n📋 To fix this:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Navigate to 'APIs & Services' > 'Credentials'")
        print("3. Download your OAuth 2.0 client credentials")
        print("4. Save as 'credentials.json' in this directory")
        return False
    
    try:
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
        
        if 'web' in creds:
            print("✅ Found 'web' application credentials")
            print(f"   Client ID: {creds['web']['client_id']}")
            print(f"   Project ID: {creds['web']['project_id']}")
            
            print("\n⚠️  ISSUE DETECTED: Web application credentials require fixed redirect URIs")
            print("\n🔧 SOLUTION OPTIONS:")
            print("1. Change to Desktop Application (RECOMMENDED):")
            print("   - Go to Google Cloud Console")
            print("   - Edit your OAuth client")
            print("   - Change application type from 'Web' to 'Desktop'")
            print("   - Download new credentials.json")
            
            print("\n2. OR add these redirect URIs to your web application:")
            redirect_uris = [
                "http://localhost:8080/",
                "http://localhost:8081/", 
                "http://localhost:8082/",
                "http://localhost:9090/"
            ]
            for uri in redirect_uris:
                print(f"   - {uri}")
            
            return "web"
            
        elif 'installed' in creds:
            print("✅ Found 'installed' application credentials")
            print(f"   Client ID: {creds['installed']['client_id']}")
            print(f"   Project ID: {creds['installed']['project_id']}")
            print("✅ This format should work correctly!")
            return "installed"
        else:
            print("❌ Unknown credentials format!")
            print("   Expected 'web' or 'installed' key in JSON")
            return False
            
    except json.JSONDecodeError:
        print("❌ Invalid JSON in credentials.json")
        return False
    except Exception as e:
        print(f"❌ Error reading credentials.json: {e}")
        return False

def convert_web_to_desktop():
    """Convert web credentials to desktop format"""
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        return False
    
    try:
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
        
        if 'web' not in creds:
            print("❌ This is not a web application credentials file")
            return False
        
        # Create desktop version
        desktop_creds = {
            "installed": {
                "client_id": creds['web']['client_id'],
                "client_secret": creds['web']['client_secret'],
                "project_id": creds['web']['project_id'],
                "auth_uri": creds['web']['auth_uri'],
                "token_uri": creds['web']['token_uri'],
                "auth_provider_x509_cert_url": creds['web']['auth_provider_x509_cert_url'],
                "redirect_uris": ["http://localhost"]
            }
        }
        
        # Backup original
        with open('credentials_web_backup.json', 'w') as f:
            json.dump(creds, f, indent=2)
        
        # Save converted version
        with open('credentials.json', 'w') as f:
            json.dump(desktop_creds, f, indent=2)
        
        print("✅ Converted web credentials to desktop format")
        print("📁 Original saved as credentials_web_backup.json")
        return True
        
    except Exception as e:
        print(f"❌ Error converting credentials: {e}")
        return False

def test_oauth_flow():
    """Test the OAuth flow"""
    print("\n🧪 Testing OAuth flow...")
    
    try:
        from gcal_utils.gcal import GoogleCalendarManager
        
        # Remove existing token to force fresh OAuth
        if os.path.exists('token.json'):
            os.remove('token.json')
            print("🗑️  Removed existing token.json for fresh test")
        
        print("🔄 Starting OAuth flow...")
        print("📱 A browser window should open for authorization")
        
        calendar_manager = GoogleCalendarManager()
        print("✅ OAuth flow completed successfully!")
        
        # Test basic functionality
        events = calendar_manager.get_upcoming_events(1)
        print(f"✅ Calendar access test passed! Found {len(events)} events")
        
        return True
        
    except FileNotFoundError as e:
        print(f"❌ Credentials file issue: {e}")
        return False
    except Exception as e:
        print(f"❌ OAuth flow failed: {e}")
        if "redirect_uri_mismatch" in str(e):
            print("\n💡 This confirms the redirect URI mismatch issue!")
            print("   Please follow the solution steps above.")
        return False

def open_google_console():
    """Open Google Cloud Console in browser"""
    console_url = "https://console.cloud.google.com/apis/credentials"
    print(f"\n🌐 Opening Google Cloud Console: {console_url}")
    webbrowser.open(console_url)

def main():
    """Main diagnostic and fix routine"""
    print("🔧 Google Calendar OAuth Setup and Troubleshooting")
    print("=" * 50)
    
    # Check current directory
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Step 1: Check credentials
    creds_type = check_credentials_file()
    
    if not creds_type:
        return
    
    print("\n" + "="*50)
    
    if creds_type == "web":
        print("🔄 You have web application credentials that need fixing...")
        
        choice = input("\nChoose an option:\n1. Convert to desktop format (quick fix)\n2. Open Google Console to change application type\n3. Test current setup anyway\n\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            if convert_web_to_desktop():
                print("\n✅ Conversion complete! Now testing OAuth flow...")
                test_oauth_flow()
            else:
                print("❌ Conversion failed")
        elif choice == "2":
            open_google_console()
            print("\n📋 After changing to Desktop application:")
            print("1. Download the new credentials.json")
            print("2. Replace your current credentials.json")
            print("3. Run this script again")
        elif choice == "3":
            test_oauth_flow()
        else:
            print("❌ Invalid choice")
    
    elif creds_type == "installed":
        print("✅ Credentials format looks good! Testing OAuth flow...")
        test_oauth_flow()
    
    print("\n" + "="*50)
    print("🎯 Quick Summary:")
    print("- If you see 'redirect_uri_mismatch', change app type to Desktop")
    print("- Desktop applications work better for local development")
    print("- Your credentials.json should have 'installed' not 'web' key")
    print("- Run this script again after making changes")

if __name__ == "__main__":
    main()
