import os
import datetime
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# Define the scope for Google Calendar: full access to users' calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def load_credentials():
    """
    Loads credentials from 'token.json' if available. 
    If credentials are expired, but refreshable, refreshes them
    """
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
        if creds and creds.valid:
            return creds
        elif creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            return creds
    return None

def save_credentials(creds):
    """Saves the given credentials to token.json"""
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

def get_calendar_service(creds):
    # Builds and returns a Google calendar API service
    return build('calendar', 'v3', credentials=creds)

def list_upcoming_events(creds):
    service = get_calendar_service(creds)
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute()

    return events_result.get('items', [])