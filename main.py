import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask, redirect, url_for, session, request
from google_auth_oauthlib.flow import Flow
from apis.google_calendar import load_credentials, save_credentials, list_upcoming_events
from apis.gemini import gemini_study_planner

app = Flask(__name__)
app.secret_key = '2c68ac92b8611f9d78c491ca03495f66'

SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = 'https://managerricardo-librafrank-3000.codio.io/oauth2callback'

@app.route('/plan')
def index():
    creds = load_credentials()
    if not creds:
        return redirect(url_for('authorize'))

    events = list_upcoming_events(creds)
    summary = "\n".join([f"{e['start'].get('dateTime', e['start'].get('date'))} - {e['summary']}" for e in events])

    ai_plan = gemini_study_planner(summary)
    return f"<pre>{ai_plan}</pre>"

@app.route('/authorize')
def authorize():
    creds = load_credentials()
    if creds:
        return redirect(url_for('index'))  # Already authenticated

    flow = Flow.from_client_secrets_file(
        'google_calendar_credentials.json',
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    flow = Flow.from_client_secrets_file(
        'google_calendar_credentials.json',
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    save_credentials(creds)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
