import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 
# To check if the code even works and run smoothly ^^^

import os
import json
from sqlalchemy import select, insert, update
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from models.db_models import get_engine, oauth_tokens
from datetime import datetime, timedelta

# Connect to database
engine = get_engine()
conn = engine.connect()


# Define the scope for Google Calendar: full access to users' calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

def load_credentials(user_id):
    """
    Loads credentials from 'token.json' if available. 
    If credentials are expired, but refreshable, refreshes them
    """
    query = select(oauth_tokens).where(oauth_tokens.c.user_id == user_id)
    result = conn.execute(query).fetchone()
    if not result:
        return None
    
    creds = Credentials(
        token=result.access_token,
        refresh_token=result.refresh_token,
        token_uri=result.token_uri,
        client_id=result.client_id,
        client_secret=result.client_secret,
        scopes=json.loads(result.scopes or "[]")
    )

    #creds = Credentials.from_authorized_user_file(creds_dict)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(user_id, creds, result.google_email)
        except Exception as e:
            print(f"Error refreshing credentials {e}")
            return None
    
    return creds
    #if os.path.exists('token.json'):
        #creds = Credentials.from_authorized_user_file('token.json')
        #if creds and creds.valid:
            #return creds
        #elif creds and creds.expired and creds.refresh_token:
            #creds.refresh(Request())
            #return creds
    #return None

def save_credentials(user_id, creds, google_email=None):
    """Saves the given credentials to token.json"""
    query = select(oauth_tokens).where(oauth_tokens.c.user_id == user_id)
    existing = conn.execute(query).fetchone()

    values = {
        "user_id": user_id,
        "google_email": google_email,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": json.dumps(creds.scopes),
        "expiry": creds.expiry
        #"created_at": datetime.datetime.utcnow()
    }
    if existing:
        query = update(oauth_tokens).where(oauth_tokens.c.user_id == user_id).values(**values)
        #update = oauth_tokens.select().where(oauth_tokens.c.user_id == user_id).values(**values)
        #conn.execute(update)
    else:
        query = insert(oauth_tokens).values(**values)
        #insert = oauth_tokens.select().values(**values)
        #conn.execute(insert)
    conn.execute(query)
    conn.commit()

    #with open('token.json', 'w') as token:
        #token.write(creds.to_json())

def get_calendar_service(creds):
    # Builds and returns a Google calendar API service
    return build('calendar', 'v3', credentials=creds)

def list_upcoming_events(creds):
    service = get_calendar_service(creds)
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=now, maxResults=50, singleEvents=True, orderBy='startTime').execute()

    return events_result.get('items', [])

# To do: Create a create_event function
def create_calendar_event(creds, event_data):
    service = get_calendar_service(creds)
    # Format the event data for google calendar
    event = {
        'summary': event_data.get('summary', 'Study Task'),
        'description': event_data.get('description', ''),
        'start': {
            'dateTime': event_data['start'],
            'timeZone': 'America/New_York',  # Adjust based on your timezone
        },
        'end': {
            'dateTime': event_data['end'],
            'timeZone': 'America/New_York',  # Adjust based on your timezone
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event.get('id')
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return None

def create_task_event(creds, task_title, task_description, start_time, duration_minutes=60):
    # Creates  calendar event for specific task
    start_datetime = datetime.fromisoformat(start_time)
    #end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)
    end_datetime = start_datetime + timedelta(minutes=duration_minutes)

    event_data = {
        'summary': f"📚 {task_title}",
        'description': task_description,
        'start': start_datetime.isoformat(),
        'end': end_datetime.isoformat()
    }

    return create_calendar_event(creds, event_data)

def get_free_time_slots(creds, start_date, end_date):
    service = get_calendar_service(creds)
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_date.isoformat() + 'Z',
        timeMax=end_date.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get("items", [])
    busy_times = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))

        if 'T' in start:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            busy_times.append((start_dt, end_dt))
    
    return busy_times

if __name__ == "__main__":
    try: 
        test = conn.execute(select(oauth_tokens)).fetchall()
        print("google_calendar.py loaded and db conn works")
    except Exception as e:
        print(f"Error {e}")