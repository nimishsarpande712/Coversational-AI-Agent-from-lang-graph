# Google Calendar Credentials Converter
# This script converts web credentials to desktop format for local OAuth

import json
import os

def convert_web_to_desktop_credentials():
    """Convert web application credentials to desktop application format"""
    
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        return False
    
    try:
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
        
        if 'web' in creds:
            print("📝 Converting web credentials to desktop format...")
            
            # Create desktop version
            desktop_creds = {
                "installed": {
                    "client_id": creds['web']['client_id'],
                    "client_secret": creds['web']['client_secret'],
                    "project_id": creds['web']['project_id'],
                    "auth_uri": creds['web']['auth_uri'],
                    "token_uri": creds['web']['token_uri'],
                    "auth_provider_x509_cert_url": creds['web']['auth_provider_x509_cert_url'],
                    "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"]
                }
            }
            
            # Backup original
            with open('credentials_web_backup.json', 'w') as f:
                json.dump(creds, f, indent=2)
            
            # Write desktop version
            with open('credentials.json', 'w') as f:
                json.dump(desktop_creds, f, indent=2)
            
            print("✅ Credentials converted successfully!")
            print("📁 Original web credentials backed up to credentials_web_backup.json")
            return True
            
        else:
            print("✅ Credentials are already in desktop format!")
            return True
            
    except Exception as e:
        print(f"❌ Error converting credentials: {e}")
        return False

if __name__ == "__main__":
    convert_web_to_desktop_credentials()
