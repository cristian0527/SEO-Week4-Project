# Transfer Joey's commit
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask, render_template, flash, redirect, url_for, session, request, jsonify
from flask_bcrypt import Bcrypt
from flask_behind_proxy import FlaskBehindProxy
from forms import RegistrationForm, LoginForm
from users import add_user, get_user_by_email, get_unscheduled_tasks, get_tasks_by_user, add_task_to_db, update_task_compeletion, get_task_by_id, update_task_schedule, get_pending_tasks, get_completed_tasks, get_all_tasks_by_user
from google_auth_oauthlib.flow import Flow
from apis.google_calendar import load_credentials, save_credentials, list_upcoming_events, get_calendar_service, create_task_event
from apis.gemini import gemini_study_planner
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime, timedelta
from sqlalchemy import insert, update
from models.db_models import tasks


app = Flask(__name__)
proxied = FlaskBehindProxy(app)
bcrypt = Bcrypt(app)
app.secret_key = '2c68ac92b8611f9d78c491ca03495f66'

# Add template filter for date formatting
@app.template_filter('ddmmyyyy')
def ddmmyyyy_filter(date_obj):
    """Format date as DD/MM/YYYY for templates"""
    if date_obj:
        return date_obj.strftime('%d/%m/%Y')
    return ''

@app.template_filter('ddmmyyyy_time')
def ddmmyyyy_time_filter(datetime_obj):
    """Format datetime as DD/MM/YYYY HH:MM for templates"""
    if datetime_obj:
        return datetime_obj.strftime('%d/%m/%Y %H:%M')
    return ''

# Added two more scopes to gain access to email so we can send schedule to a user's google calendar 
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
    ]
REDIRECT_URI = 'https://managerricardo-librafrank-3000.codio.io/oauth2callback'

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's tasks
    pending_tasks = get_pending_tasks(session['user_id'])
    completed_tasks = get_completed_tasks(session['user_id'])
    
    # Try to get Google Calendar events
    calendar_events = []
    creds = load_credentials(session['user_id'])
    if creds:
        try:
            calendar_events = list_upcoming_events(creds)
        except Exception as e:
            flash("Error loading calendar events. Please reconnect your Google Calendar.", "warning")
    
    return render_template('home.html', 
                         pending_tasks=pending_tasks, 
                         completed_tasks=completed_tasks,
                         calendar_events=calendar_events)
    #return render_template('home.html', subtitle="Home Page", text="This is the home page.")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit(): 
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = {
            'username': form.username.data,
            'email': form.email.data,
            'hashed_password': hashed_password
        }
        if get_user_by_email(form.email.data):
            flash('Email already exists. Please log in.', 'danger')
            return redirect(url_for('login'))

        
        add_user(user)
        db_user = get_user_by_email(form.email.data)
        session['user_id'] = db_user.id
        
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('home')) 
        #print(form.errors)
    else:
        print("Form did not validate:", form.errors)

    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)
        if user and bcrypt.check_password_hash(user.hashed_password, form.password.data):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash(f'Login successful as {user.username}!', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

#tested
@app.route('/plan')
def index():
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for('login')) 
    
    creds = load_credentials(session['user_id']) 
    if not creds:
        return redirect(url_for('authorize'))
    
    events = list_upcoming_events(creds)
    summary = "\n".join([f"{e['start'].get('dateTime', e['start'].get('date'))} - {e['summary']}" for e in events])
    ai_plan = gemini_study_planner(summary)
    return f"<pre>{ai_plan}</pre>"

@app.route('/todo')
def todo():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login')) 

    pending_tasks = get_pending_tasks(session['user_id'])
    completed_tasks = get_completed_tasks(session['user_id'])

    return render_template('todo.html', pending_tasks=pending_tasks, completed_tasks=completed_tasks)

# HELPER FUNCTION: Add task to Google Calendar
def add_task_to_google_calendar(user_id, task_id, title, description, due_datetime, duration_minutes=60):
    """
    Add a task to user's Google Calendar using the existing create_task_event function
    Returns: (success: bool, event_id: str or None)
    """
    try:
        creds = load_credentials(user_id)
        if not creds:
            return False, None
        
        # Use your existing create_task_event function
        event_id = create_task_event(
            creds=creds,
            task_title=title,
            task_description=description,
            start_time=due_datetime.isoformat(),
            duration_minutes=duration_minutes
        )
        
        if event_id:
            # Update task in database with Google event ID
            update_task_schedule(task_id, due_datetime, event_id)
            return True, event_id
        
        return False, None
        
    except Exception as e:
        print(f"Error adding task to Google Calendar: {e}")
        return False, None

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    # Get form data
    title = request.form.get('title')
    description = request.form.get('description', '')
    link = request.form.get('link', '')
    due_date_str = request.form.get('due_date')
    due_time_str = request.form.get('due_time')
    
    # Validate required fields
    if not title:
        flash("Task title is required.", "danger")
        return redirect(url_for('todo'))
    
    # Handle date format conversion (supports both DD/MM/YYYY and YYYY-MM-DD)
    due_date = None
    if due_date_str:
        try:
            if '/' in due_date_str:
                due_date = datetime.strptime(due_date_str, '%d/%m/%Y').date()
            else:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Please use DD/MM/YYYY or YYYY-MM-DD format for date.", "danger")
            return redirect(url_for('todo'))
    
    # Handle time conversion
    due_time = None
    if due_time_str:
        try:
            due_time = datetime.strptime(due_time_str, '%H:%M').time()
        except ValueError:
            flash("Invalid time format. Use HH:MM format.", "danger")
            return redirect(url_for('todo'))
    
    # Combine date and time
    due_datetime = None
    if due_date and due_time:
        due_datetime = datetime.combine(due_date, due_time)
    elif due_date:
        due_datetime = datetime.combine(due_date, datetime.min.time())
    
    # Create task description with link if provided
    task_description = description
    if link:
        task_description += f"\n\nLink: {link}"
    
    # Create new task data
    task_data = {
        'user_id': session['user_id'],
        'title': title,
        'description': task_description,
        'due_date': due_datetime,
        'is_completed': False,
    }
    
    # Add to database first
    task_id = add_task_to_db(task_data)
    
    # Automatically add to Google Calendar if due date/time is provided
    if due_datetime:
        success, event_id = add_task_to_google_calendar(
            session['user_id'], task_id, title, task_description, due_datetime, duration_minutes=60
        )
        
        if success:
            flash("Task added successfully and scheduled in your Google Calendar!", "success")
        else:
            flash("Task added successfully, but failed to add to Google Calendar. Make sure your calendar is connected.", "warning")
    else:
        flash("Task added successfully! Add a due date to automatically sync with Google Calendar.", "info")
    
    return redirect(url_for('todo'))

@app.route('/add_task_to_calendar/<int:task_id>', methods=['POST'])
def add_existing_task_to_calendar(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get task from database
    task = get_task_by_id(task_id)
    if not task or task.user_id != session['user_id']:
        flash("Task not found.", "danger")
        return redirect(url_for('todo'))
    
    if not task.due_date:
        flash("Cannot add task to calendar without a due date.", "warning")
        return redirect(url_for('todo'))
    
    # Add to Google Calendar
    success, event_id = add_task_to_google_calendar(
        session['user_id'], task_id, task.title, task.description, task.due_date
    )
    
    if success:
        flash("Task added to your Google Calendar!", "success")
    else:
        flash("Failed to add task to Google Calendar.", "danger")
    
    return redirect(url_for('todo'))


@app.route('/authorize')
def authorize():
    user_id = session.get('user_id')
    if 'user_id' not in session:
        flash("Please log in to connect Google Calendar.", "warning")
        return redirect(url_for('login')) 
    
    creds = load_credentials(user_id)
    if creds:
        flash("Google Calendar already connected!")
        return redirect(url_for('home'))  # Already authenticated

    flow = Flow.from_client_secrets_file(
        'google_calendar_credentials.json',
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    user_id = session.get('user_id')
    if 'user_id' not in session:
        flash("Please log in to complete Google authentication.", "warning")
        return redirect(url_for('login')) 
    
    flow = Flow.from_client_secrets_file(
        'google_calendar_credentials.json',
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)
    
    creds = flow.credentials

    #email = creds.id_token.get("email") if creds.id_token else 
    email = None
    if creds.id_token:
        try: 
            idinfo = id_token.verify_oauth2_token(creds.id_token, requests.Request())
            email = idinfo.get("email")
        except Exception as e:
            print(f"failed to verify id token {e}")
            #email = None
    #else: 
        #email = None
    save_credentials(session['user_id'], creds, google_email=email)
    #save_credentials(user_id, creds, google_email=email)

    flash("Google Calendar connected successfully! Your events will now appear on the calendar.", "success")
    return redirect(url_for('index'))


@app.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    # Update task completion status
    update_task_compeletion(task_id, True)
    
    flash("Task Completed.", "success")
    return redirect(request.referrer or url_for('todo'))
    #return redirect(url_for('todo'))

# SCHEDULER PAGE (goal-based planning)
@app.route('/scheduler', methods=['GET', 'POST'])
def scheduler():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        goal = request.form.get('goal')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        
        if not goal or not description or not deadline_str:
            flash("Goal, description, and deadline are required.", "danger")
            return render_template('scheduler.html')
        
        # Parse deadline
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        except ValueError:
            flash("Invalid deadline format.", "danger")
            return render_template('scheduler.html')
        
        # Get user's calendar for context
        creds = load_credentials(session['user_id'])
        calendar_summary = ""
        if creds:
            try:
                events = list_upcoming_events(creds)
                calendar_summary = "\n".join([
                    f"{e['start'].get('dateTime', e['start'].get('date'))} - {e['summary']}" 
                    for e in events
                ])
            except Exception:
                calendar_summary = "No calendar events available"
        
        # Generate AI study plan
        prompt = f"""
        Goal: {goal}
        Description: {description}
        Deadline: {deadline.strftime('%A, %B %d, %Y')}
        
        Current calendar:
        {calendar_summary}
        
        Please create a study plan with specific time blocks, avoiding conflicts with the schedule above.
        """
        
        try:
            ai_plan = gemini_study_planner(prompt)
            return render_template('scheduler.html', plan=ai_plan, goal=goal)
        except Exception as e:
            flash("Error generating study plan. Please try again.", "danger")
            return render_template('scheduler.html')
    
    return render_template('scheduler.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)




