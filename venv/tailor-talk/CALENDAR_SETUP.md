# Google Calendar Setup Troubleshooting Guide

## 🔧 Common Issues and Solutions

### 1. "No credentials found" Error
**Solution:** ✅ FIXED - Credentials converted to desktop format

### 2. OAuth Error or Redirect URI Mismatch
**Check these in Google Cloud Console:**

1. **Enable Google Calendar API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Select your project: `ee-nimimuguciaz9241`
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable" if not already enabled

2. **Configure OAuth Consent Screen:**
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type
   - Fill in required fields:
     - App name: "Tailor-Talk AI Assistant"
     - User support email: Your email
     - App domain: Leave empty for testing
     - Developer contact: Your email
   - Add scopes: `auth/calendar` and `auth/calendar.events`
   - Add test users: Your Gmail address

3. **Update OAuth 2.0 Client:**
   - Go to "APIs & Services" > "Credentials"
   - Click on your OAuth 2.0 Client ID
   - Under "Authorized redirect URIs", add:
     - `http://localhost:8080`
     - `http://localhost:8501`
     - `urn:ietf:wg:oauth:2.0:oob`

### 3. Authentication Flow
When you click "Connect Calendar" in the app:
1. Browser will open Google OAuth page
2. Sign in with your Google account
3. Grant calendar permissions
4. You'll be redirected back to the app
5. Token will be saved for future use

### 4. Testing the Connection
```python
# Test in Python console
from gcal_utils.gcal import GoogleCalendarManager
calendar = GoogleCalendarManager()
events = calendar.get_upcoming_events(5)
print(f"Found {len(events)} events")
```

### 5. Still Having Issues?
1. Delete `token.json` if it exists
2. Restart the Streamlit app
3. Try connecting calendar again
4. Check browser console for errors
5. Ensure you're using the correct Google account

## 📞 Support
If issues persist, check:
- Google Cloud Console quota limits
- API billing status
- Calendar permissions in your Google account
