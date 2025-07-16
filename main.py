import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask, render_template, flash, redirect, url_for, session, request
from flask_bcrypt import Bcrypt
from flask_behind_proxy import FlaskBehindProxy
from forms import RegistrationForm, LoginForm
from users import users_db, add_user, get_user_by_email
from google_auth_oauthlib.flow import Flow
from apis.google_calendar import load_credentials, save_credentials, list_upcoming_events
from apis.gemini import gemini_study_planner

app = Flask(__name__)
proxied = FlaskBehindProxy(app)
bcrypt = Bcrypt(app)
app.secret_key = '2c68ac92b8611f9d78c491ca03495f66'

SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = 'https://managerricardo-librafrank-3000.codio.io/oauth2callback'

@app.route('/')
def home():
    return render_template('home.html', subtitle="Home Page", text="This is the home page.")

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit(): 
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = {
            'username': form.username.data,
            'email': form.email.data,
            'password': hashed_password
        }
        if get_user_by_email(user['email']):
            flash('Email already exists. Please log in.', 'danger')
            return redirect(url_for('login'))
        else:
            add_user(user)
            flash(f'Account created for {form.username.data}!', 'success')
            return redirect(url_for('home')) 
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)
        if user and bcrypt.check_password_hash(user['password'], form.password.data):
            session['user'] = user['username']
            flash(f'Login successful as {form.username.data}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login failed. Check your email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

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
