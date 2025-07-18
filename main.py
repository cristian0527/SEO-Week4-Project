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
import pytz
import re
import calendar


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
# REDIRECT_URI = 'https://managerricardo-librafrank-3000.codio.io/oauth2callback'
REDIRECT_URI = 'https://prestodinner-riskarctic-4000.codio.io/proxy/3000/oauth2callback'


"""
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
"""
"""
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('calendar_view'))
"""

@app.route('/')
def welcome():
    # Landing Page
    if 'user_id' in session:
        return redirect(url_for('calendar_view'))
    else:
        return render_template('welcome.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('welcome'))  # Redirect to welcome page, not home

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # Add this line
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html', form=form)  # Pass form
        
        user = get_user_by_email(email)
        if user and bcrypt.check_password_hash(user.hashed_password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('calendar_view'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()  # Add this line
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # ... your existing validation code ...
        
        if get_user_by_email(email):
            flash('Email already exists. Please log in.', 'danger')
            return redirect(url_for('login'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = {
            'username': username,
            'email': email,
            'hashed_password': hashed_password
        }
        
        add_user(user)
        db_user = get_user_by_email(email)
        session['user_id'] = db_user.id
        
        flash(f'Account created for {username}!', 'success')
        return redirect(url_for('calendar_view'))
    
    return render_template('register.html', form=form)  # Pass form

# DYNAMIC CALENDAR ROUTE
@app.route('/home')
@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Default to current date if no year/month provided
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    # Validate month/year
    if month < 1 or month > 12:
        month = now.month
        year = now.year
    
    # Calculate previous and next month
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    
    # Get calendar data
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Get today's date for highlighting
    today = now.date()
    
    # Get tasks for this month
    pending_tasks = get_pending_tasks(session['user_id'])
    completed_tasks = get_completed_tasks(session['user_id'])
    
    # Filter tasks for current month
    month_pending_tasks = []
    month_completed_tasks = []
    
    for task in pending_tasks:
        if task.due_date and task.due_date.year == year and task.due_date.month == month:
            month_pending_tasks.append(task)
    
    for task in completed_tasks:
        if task.due_date and task.due_date.year == year and task.due_date.month == month:
            month_completed_tasks.append(task)
    
    # Get Google Calendar events for this month
    calendar_events = []
    creds = load_credentials(session['user_id'])
    if creds:
        try:
            # Get events for the entire month
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = datetime(year, month + 1, 1) - timedelta(days=1)
            
            # Set timezone
            ny_tz = pytz.timezone('America/New_York')
            month_start = ny_tz.localize(month_start)
            month_end = ny_tz.localize(month_end.replace(hour=23, minute=59, second=59))
            
            # Get events for this month only
            service = get_calendar_service(creds)
            events_result = service.events().list(
                calendarId='primary',
                timeMin=month_start.isoformat(),
                timeMax=month_end.isoformat(),
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            calendar_events = events_result.get('items', [])
            
        except Exception as e:
            print(f"Error loading calendar events: {e}")
            flash("Error loading calendar events. Please reconnect your Google Calendar.", "warning")
    
    return render_template('calendar_dynamic.html',
                         calendar_weeks=cal,
                         month_name=month_name,
                         year=year,
                         month=month,
                         today=today,
                         prev_year=prev_year,
                         prev_month=prev_month,
                         next_year=next_year,
                         next_month=next_month,
                         pending_tasks=month_pending_tasks,
                         completed_tasks=month_completed_tasks,
                         calendar_events=calendar_events)


"""
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
"""
"""
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')
        
        user = get_user_by_email(email)
        if user and bcrypt.check_password_hash(user.hashed_password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('calendar_view'))  # Changed from 'home' to 'calendar_view'
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # ... your existing validation code ...
        
        add_user(user)
        db_user = get_user_by_email(email)
        session['user_id'] = db_user.id
        
        flash(f'Account created for {username}!', 'success')
        return redirect(url_for('calendar_view'))  # Changed from 'home' to 'calendar_view'
    
    return render_template('register.html')
"""
"""
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)

        if user and bcrypt.check_password_hash(user.hashed_password, form.password.data):
            session['user_id'] = user.id
            flash(f'Login successful as {user.username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash(f'Login failed. Please try again!', 'danger')

    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/calendar')
def calendar():
    if session['user'] is None:
        flash("Please log in first.")
        return redirect(url_for('login')) 
    
    creds = load_credentials(session['user']) 

    if not creds:
        return redirect(url_for('authorize'))

    events = list_upcoming_events(creds)
    
    # FullCalendar events
    fc_events = []
    for e in events:
        fc_events.append({
            "title": e['summary'],
            "start": e['start'].get('dateTime', e['start'].get('date')),
            "end": e['end'].get('dateTime', e['end'].get('date')),
        })

    return render_template('calendar.html', fc_events=fc_events)


@app.route('/plan')
def index():
    if session['user'] is None:
        flash("Please log in first.")
        return redirect(url_for('login')) 
    
    creds = load_credentials(session['user']) 
    if not creds:
        return redirect(url_for('authorize'))
    
    events = list_upcoming_events(creds)
    summary = "\n".join([f"{e['start'].get('dateTime', e['start'].get('date'))} - {e['summary']}" for e in events])
    ai_plan = gemini_study_planner(summary)
    return f"<pre>{ai_plan}</pre>"
"""

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
    user = session.get('user')
    if 'user' not in session:
        flash("Please log in to connect Google Calendar.", "warning")
        return redirect(url_for('login')) 
    
    creds = load_credentials(user)
    if creds:
        flash("Google Calendar already connected!")
        return redirect(url_for('calendar_view'))  # Already authenticated


    flow = Flow.from_client_secrets_file(
        'google_calendar_credentials.json',
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    print("Redirecting user to:", auth_url)
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    user = session.get('user')
    if 'user' not in session:
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
    return redirect(url_for('calendar_view'))


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
        deadline_time_str = request.form.get('deadline_time', '23:59')  # Default to end of day if no time
        
        if not goal or not description or not deadline_str:
            flash("Goal, description, and deadline are required.", "danger")
            return render_template('scheduler.html')
        
        # Set up NYC timezone
        ny_tz = pytz.timezone('America/New_York')
        
        # Parse deadline with time and timezone
        try:
            # Combine date and time
            deadline_naive = datetime.strptime(f"{deadline_str} {deadline_time_str}", '%Y-%m-%d %H:%M')
            deadline_datetime = ny_tz.localize(deadline_naive)  # Add timezone info
        except ValueError:
            flash("Invalid deadline format.", "danger")
            return render_template('scheduler.html')
        
        # Get current time with NYC timezone
        current_time = datetime.now(ny_tz)
        
        # Check if deadline is in the past
        if deadline_datetime <= current_time:
            flash("Deadline must be in the future.", "danger")
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
        
        # Generate AI study plan with improved prompt (using NYC timezone)

        prompt = f"""
                IMPORTANT: Follow this EXACT format. Do not deviate from this structure.

                Goal: {goal}
                Description: {description}  
                Current time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}
                Deadline: {deadline_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}

                SPECIAL INSTRUCTIONS: If the user mentions starting on a specific day (like "start Saturday"), begin the schedule on that day, NOT today.

                ## 📅 Your Study Schedule

                **TIME BLOCK 1**
                ⏰ **Time:** [start time] - [end time]
                📝 **Task:** [specific task name]
                ⏱️ **Duration:** [X hours Y minutes]
                📋 **Details:** [brief description of what to do]

                **TIME BLOCK 2**
                ⏰ **Time:** [start time] - [end time]
                📝 **Task:** [specific task name]  
                ⏱️ **Duration:** [X hours Y minutes]
                📋 **Details:** [brief description of what to do]

                Continue this pattern for each time block.

                **IMPORTANT RULES:**
                - Use simple, clear language
                - Each time block should be 15 minutes to 2 hours max
                - Include short breaks between long blocks
                - Stop exactly at the deadline: {deadline_datetime.strftime('%B %d, %Y at %I:%M %p')}
                - Use 12-hour format (7:30 PM not 19:30)
                - Make task names short and actionable

                Current calendar events to avoid conflicts:
                {calendar_summary}
                """

        
        try:
            ai_plan = gemini_study_planner(prompt)
            
            # Store the plan data in session for saving to calendar later
            session['current_plan'] = {
                'goal': goal,
                'description': description,
                'deadline': deadline_datetime.isoformat(),
                'plan': ai_plan,
                'created_at': current_time.isoformat()
            }
            
            return render_template('scheduler.html', plan=ai_plan, goal=goal)
        except Exception as e:
            print(f"Error generating study plan: {e}")
            flash("Error generating study plan. Please try again.", "danger")
            return render_template('scheduler.html')
    
    return render_template('scheduler.html')

def parse_time_blocks_with_dates(plan_text):
    """
    Parse structured time blocks from Gemini output that includes date headers
    Returns list of time blocks with start_time, end_time, task, duration, details, and date
    """
    time_blocks = []
    
    # Split the text into sections by day headers like "**Friday, July 18, 2025**"
    day_sections = re.split(r'\*\*([A-Za-z]+,\s*[A-Za-z]+\s*\d+,\s*\d+)\*\*', plan_text)
    
    current_date = None
    
    for i in range(1, len(day_sections), 2):  # Skip first empty section, then take every other
        if i < len(day_sections) - 1:
            date_header = day_sections[i].strip()
            section_content = day_sections[i + 1]
            
            # Parse the date from the header
            try:
                # Parse dates like "Friday, July 18, 2025"
                parsed_date = datetime.strptime(date_header, '%A, %B %d, %Y').date()
                current_date = parsed_date
            except ValueError:
                try:
                    # Try alternative format
                    parsed_date = datetime.strptime(date_header, '%A, %B %d, %Y').date()
                    current_date = parsed_date
                except ValueError:
                    # If we can't parse the date, use previous date or default
                    if current_date:
                        current_date = current_date + timedelta(days=1)
                    else:
                        current_date = datetime.now().date()
            
            # Now parse time blocks within this day section
            blocks = re.split(r'\*\*TIME BLOCK \d+\*\*', section_content)
            
            for block in blocks[1:]:  # Skip first empty split
                # Extract time using regex
                time_match = re.search(r'\*\*Time:\*\* (.+?) - (.+?)\n', block)
                task_match = re.search(r'\*\*Task:\*\* (.+?)\n', block)
                duration_match = re.search(r'\*\*Duration:\*\* (.+?)\n', block)
                details_match = re.search(r'\*\*Details:\*\* (.+?)(?:\n\n|\n\*\*|$)', block, re.DOTALL)
                
                if time_match and task_match:
                    start_time_str = time_match.group(1).strip()
                    end_time_str = time_match.group(2).strip()
                    task = task_match.group(1).strip()
                    duration = duration_match.group(1).strip() if duration_match else ""
                    details = details_match.group(1).strip() if details_match else ""
                    
                    time_blocks.append({
                        'start_time': start_time_str,
                        'end_time': end_time_str,
                        'task': task,
                        'duration': duration,
                        'details': details,
                        'date': current_date  # Add the parsed date
                    })
    
    # Fallback: if no date headers were found, use the original parsing method
    if not time_blocks:
        return parse_time_blocks_fallback(plan_text)
    
    return time_blocks

def parse_time_blocks_fallback(plan_text):
    """
    Fallback parsing method (your original function) when no date headers are found
    """
    time_blocks = []
    
    # Split by TIME BLOCK sections
    blocks = re.split(r'\*\*TIME BLOCK \d+\*\*', plan_text)
    
    for block in blocks[1:]:  # Skip first empty split
        # Extract time using regex
        time_match = re.search(r'\*\*Time:\*\* (.+?) - (.+?)\n', block)
        task_match = re.search(r'\*\*Task:\*\* (.+?)\n', block)
        duration_match = re.search(r'\*\*Duration:\*\* (.+?)\n', block)
        details_match = re.search(r'\*\*Details:\*\* (.+?)(?:\n\n|\n\*\*|$)', block, re.DOTALL)
        
        if time_match and task_match:
            start_time_str = time_match.group(1).strip()
            end_time_str = time_match.group(2).strip()
            task = task_match.group(1).strip()
            duration = duration_match.group(1).strip() if duration_match else ""
            details = details_match.group(1).strip() if details_match else ""
            
            time_blocks.append({
                'start_time': start_time_str,
                'end_time': end_time_str,
                'task': task,
                'duration': duration,
                'details': details,
                'date': None  # No date parsed
            })
    
    return time_blocks

@app.route('/save_schedule', methods=['POST'])
def save_schedule():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    # Get the plan data
    plan_data = request.form.get('plan_data')
    goal = request.form.get('goal')
    
    if not plan_data:
        # Try to get from session if not in form
        current_plan = session.get('current_plan')
        if current_plan:
            plan_data = current_plan['plan']
            goal = current_plan['goal']
            description = current_plan.get('description', '')
            deadline_str = current_plan.get('deadline')
        else:
            flash("No plan data found.", "danger")
            return redirect(url_for('scheduler'))
    else:
        # Get from session if available
        current_plan = session.get('current_plan', {})
        description = current_plan.get('description', '')
        deadline_str = current_plan.get('deadline')
    
    # Check if user has Google Calendar connected
    creds = load_credentials(session['user_id'])
    if not creds:
        flash("Please connect your Google Calendar first.", "warning")
        return redirect(url_for('authorize'))
    
    try:
        # Parse the time blocks from the plan using the improved parser
        time_blocks = parse_time_blocks_with_dates(plan_data)
        
        if not time_blocks:
            flash("Could not parse time blocks from the plan.", "danger")
            return redirect(url_for('scheduler'))
        
        # Get timezone and current time
        import pytz
        ny_tz = pytz.timezone('America/New_York')
        current_time = datetime.now(ny_tz)
        
        # Parse deadline from session
        deadline_datetime = None
        if deadline_str:
            try:
                deadline_datetime = datetime.fromisoformat(deadline_str)
                if deadline_datetime.tzinfo is None:
                    deadline_datetime = ny_tz.localize(deadline_datetime)
            except:
                deadline_datetime = current_time + timedelta(hours=6)  # Default fallback
        else:
            deadline_datetime = current_time + timedelta(hours=6)  # Default fallback
        
        events_created = 0
        
        for i, block in enumerate(time_blocks):
            # If we have a parsed date from the AI output, use it
            if block.get('date'):
                target_date = block['date']
            else:
                # Fallback to the old logic if no date was parsed
                if i == 0:
                    target_date = detect_start_date_from_description(description, current_time)
                else:
                    # Use previous day + 1 or same day logic
                    prev_block = time_blocks[i-1]
                    prev_date = prev_block.get('date') or current_time.date()
                    target_date = prev_date
            
            # Parse the time strings
            try:
                start_time_obj = datetime.strptime(block['start_time'], '%I:%M %p').time()
                end_time_obj = datetime.strptime(block['end_time'], '%I:%M %p').time()
            except ValueError:
                print(f"Could not parse time: {block['start_time']} - {block['end_time']}")
                continue
            
            # Create datetime objects
            start_dt = datetime.combine(target_date, start_time_obj)
            end_dt = datetime.combine(target_date, end_time_obj)
            
            # Add timezone info
            start_dt = ny_tz.localize(start_dt)
            end_dt = ny_tz.localize(end_dt)
            
            # Handle case where end time is before start time (spans midnight)
            if end_dt <= start_dt:
                end_dt = end_dt + timedelta(days=1)
            
            # Create event description
            description_text = f"Goal: {goal}\n\n{block['details']}"
            if block['duration']:
                description_text += f"\n\nDuration: {block['duration']}"
            
            # Create calendar event using your existing function
            event_id = create_task_event(
                creds=creds,
                task_title=block['task'],
                task_description=description_text,
                start_time=start_dt.isoformat(),
                duration_minutes=int((end_dt - start_dt).total_seconds() / 60)
            )
            
            if event_id:
                events_created += 1
                print(f"Created event: {block['task']} on {target_date} from {start_dt} to {end_dt}")
            else:
                print(f"Failed to create event: {block['task']}")
        
        if events_created > 0:
            flash(f"Successfully created {events_created} calendar events!", "success")
        else:
            flash("Failed to create calendar events. Please try again.", "danger")
            
    except Exception as e:
        print(f"Error saving schedule: {e}")
        import traceback
        traceback.print_exc()
        flash("Error saving schedule to calendar. Please try again.", "danger")
    
    return redirect(url_for('scheduler'))

"""
def parse_time_blocks(plan_text):
    
    Parse the structured time blocks from Gemini output
    Returns list of time blocks with start_time, end_time, task, duration, details
    
    time_blocks = []
    
    # Split by TIME BLOCK sections
    blocks = re.split(r'\*\*TIME BLOCK \d+\*\*', plan_text)
    
    for block in blocks[1:]:  # Skip first empty split
        # Extract time using regex
        time_match = re.search(r'\*\*Time:\*\* (.+?) - (.+?)\n', block)
        task_match = re.search(r'\*\*Task:\*\* (.+?)\n', block)
        duration_match = re.search(r'\*\*Duration:\*\* (.+?)\n', block)
        details_match = re.search(r'\*\*Details:\*\* (.+?)(?:\n\n|\n\*\*|$)', block, re.DOTALL)
        
        if time_match and task_match:
            start_time_str = time_match.group(1).strip()
            end_time_str = time_match.group(2).strip()
            task = task_match.group(1).strip()
            duration = duration_match.group(1).strip() if duration_match else ""
            details = details_match.group(1).strip() if details_match else ""
            
            time_blocks.append({
                'start_time': start_time_str,
                'end_time': end_time_str,
                'task': task,
                'duration': duration,
                'details': details
            })
    
    return time_blocks
"""

def detect_start_date_from_description(description, current_time):
    """
    Parse the description to find if user wants to start on a specific day
    Returns the appropriate start date
    """
    description_lower = description.lower()
    current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday
    
    weekdays = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    # Check if user mentions starting on a specific day
    for day_name, day_num in weekdays.items():
        if f'start {day_name}' in description_lower or f'begin {day_name}' in description_lower:
            # Calculate days until that weekday
            days_ahead = (day_num - current_weekday) % 7
            if days_ahead == 0:  # It's today
                days_ahead = 0 if f'start today' in description_lower else 7  # Next week if not explicitly today
            
            target_date = current_time.date() + timedelta(days=days_ahead)
            return target_date
    
    # Check for "tomorrow"
    if 'start tomorrow' in description_lower or 'begin tomorrow' in description_lower:
        return current_time.date() + timedelta(days=1)
    
    # Check for "next week"
    if 'start next week' in description_lower:
        days_until_monday = (7 - current_weekday) % 7
        return current_time.date() + timedelta(days=days_until_monday)
    
    # Default to today
    return current_time.date()

def convert_to_datetime_with_future_dates(time_str, base_date, current_time, deadline_datetime, description=""):
    """
    Convert time string to datetime object with support for future start dates
    """
    try:
        # Parse time like "2:00 AM" or "11:29 PM"
        time_obj = datetime.strptime(time_str, '%I:%M %p').time()
        
        # Determine the actual start date based on description
        actual_start_date = detect_start_date_from_description(description, current_time)
        
        # Use the actual start date instead of base_date for the first block
        result_dt = datetime.combine(actual_start_date, time_obj)
        
        # If this time has already passed today but we're starting in the future, use the future date
        if actual_start_date > current_time.date():
            # Keep the future date
            pass
        elif actual_start_date == current_time.date():
            # Starting today - check if time has passed
            current_time_only = current_time.time()
            if time_obj < current_time_only:
                # This time has passed today, might be for tomorrow
                deadline_date = deadline_datetime.date()
                if deadline_date > actual_start_date:
                    result_dt = result_dt + timedelta(days=1)
        
        return result_dt
        
    except ValueError:
        try:
            # Try 24-hour format
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            actual_start_date = detect_start_date_from_description(description, current_time)
            result_dt = datetime.combine(actual_start_date, time_obj)
            
            if actual_start_date > current_time.date():
                pass  # Keep future date
            elif actual_start_date == current_time.date() and time_obj < current_time.time():
                if deadline_datetime.date() > actual_start_date:
                    result_dt = result_dt + timedelta(days=1)
                    
            return result_dt
        except ValueError:
            return None

"""
@app.route('/save_schedule', methods=['POST'])
def save_schedule():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    # Get the plan data
    plan_data = request.form.get('plan_data')
    goal = request.form.get('goal')
    
    if not plan_data:
        # Try to get from session if not in form
        current_plan = session.get('current_plan')
        if current_plan:
            plan_data = current_plan['plan']
            goal = current_plan['goal']
            description = current_plan.get('description', '')
            deadline_str = current_plan.get('deadline')
        else:
            flash("No plan data found.", "danger")
            return redirect(url_for('scheduler'))
    else:
        # Get from session if available
        current_plan = session.get('current_plan', {})
        description = current_plan.get('description', '')
        deadline_str = current_plan.get('deadline')
    
    # Check if user has Google Calendar connected
    creds = load_credentials(session['user_id'])
    if not creds:
        flash("Please connect your Google Calendar first.", "warning")
        return redirect(url_for('authorize'))
    
    try:
        # Parse the time blocks from the plan
        time_blocks = parse_time_blocks(plan_data)
        
        if not time_blocks:
            flash("Could not parse time blocks from the plan.", "danger")
            return redirect(url_for('scheduler'))
        
        # Get timezone and current time
        import pytz
        ny_tz = pytz.timezone('America/New_York')
        current_time = datetime.now(ny_tz)
        
        # Parse deadline from session
        deadline_datetime = None
        if deadline_str:
            try:
                deadline_datetime = datetime.fromisoformat(deadline_str)
                if deadline_datetime.tzinfo is None:
                    deadline_datetime = ny_tz.localize(deadline_datetime)
            except:
                deadline_datetime = current_time + timedelta(hours=6)  # Default fallback
        else:
            deadline_datetime = current_time + timedelta(hours=6)  # Default fallback
        
        events_created = 0
        last_event_date = None
        
        for i, block in enumerate(time_blocks):
            # For the first block, use description to determine start date
            # For subsequent blocks, use the date of the previous block or increment if needed
            if i == 0:
                # First block - determine start date from description
                start_dt = convert_to_datetime_with_future_dates(
                    block['start_time'], current_time.date(), current_time, deadline_datetime, description
                )
                end_dt = convert_to_datetime_with_future_dates(
                    block['end_time'], current_time.date(), current_time, deadline_datetime, description
                )
            else:
                # Subsequent blocks - use last event date as base or increment if time went backward
                base_date = last_event_date if last_event_date else current_time.date()
                
                start_dt = convert_to_datetime_with_future_dates(
                    block['start_time'], base_date, current_time, deadline_datetime, ""
                )
                end_dt = convert_to_datetime_with_future_dates(
                    block['end_time'], base_date, current_time, deadline_datetime, ""
                )
                
                # If start time is earlier than the previous block, assume it's the next day
                if last_event_date and start_dt and start_dt.date() == last_event_date:
                    previous_block = time_blocks[i-1]
                    try:
                        prev_end_time = datetime.strptime(previous_block['end_time'], '%I:%M %p').time()
                        current_start_time = datetime.strptime(block['start_time'], '%I:%M %p').time()
                        if current_start_time < prev_end_time:
                            start_dt = start_dt + timedelta(days=1)
                            end_dt = end_dt + timedelta(days=1)
                    except:
                        pass
            
            if start_dt and end_dt:
                # Add timezone info if not already present
                if start_dt.tzinfo is None:
                    start_dt = ny_tz.localize(start_dt)
                if end_dt.tzinfo is None:
                    end_dt = ny_tz.localize(end_dt)
                
                # Handle case where end time is before start time (spans midnight)
                if end_dt <= start_dt:
                    end_dt = end_dt + timedelta(days=1)
                
                # Create event description
                description_text = f"Goal: {goal}\n\n{block['details']}"
                if block['duration']:
                    description_text += f"\n\nDuration: {block['duration']}"
                
                # Create calendar event using your existing function
                event_id = create_task_event(
                    creds=creds,
                    task_title=block['task'],
                    task_description=description_text,
                    start_time=start_dt.isoformat(),
                    duration_minutes=int((end_dt - start_dt).total_seconds() / 60)
                )
                
                if event_id:
                    events_created += 1
                    last_event_date = start_dt.date()
                    print(f"Created event: {block['task']} from {start_dt} to {end_dt}")
                else:
                    print(f"Failed to create event: {block['task']}")
        
        if events_created > 0:
            flash(f"Successfully created {events_created} calendar events!", "success")
        else:
            flash("Failed to create calendar events. Please try again.", "danger")
            
    except Exception as e:
        print(f"Error saving schedule: {e}")
        import traceback
        traceback.print_exc()
        flash("Error saving schedule to calendar. Please try again.", "danger")
    
    return redirect(url_for('scheduler'))
"""

def convert_to_datetime(time_str, base_date, current_time, deadline_datetime):
    """
    Convert time string like "2:00 AM" to datetime object
    Handles overnight schedules properly
    """
    try:
        # Parse time like "2:00 AM" or "11:29 PM"
        time_obj = datetime.strptime(time_str, '%I:%M %p').time()
        result_dt = datetime.combine(base_date, time_obj)
        
        # If the time is before current time AND the deadline is tomorrow,
        # assume this time block is for the next day
        current_time_only = current_time.time()
        deadline_date = deadline_datetime.date()
        
        # If deadline is tomorrow and this time is early (like 2:00 AM)
        if (deadline_date > base_date and 
            time_obj < datetime.strptime("6:00 AM", '%I:%M %p').time()):
            result_dt = result_dt + timedelta(days=1)
        
        # Or if this time is before current time and we're past midnight deadline
        elif (time_obj < current_time_only and 
              deadline_datetime.time() < datetime.strptime("6:00 AM", '%I:%M %p').time()):
            result_dt = result_dt + timedelta(days=1)
            
        return result_dt
        
    except ValueError:
        try:
            # Try 24-hour format
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            result_dt = datetime.combine(base_date, time_obj)
            
            # Same overnight logic for 24-hour format
            if (deadline_datetime.date() > base_date and 
                time_obj < datetime.strptime("06:00", '%H:%M').time()):
                result_dt = result_dt + timedelta(days=1)
                
            return result_dt
        except ValueError:
            return None

"""
@app.route('/save_schedule', methods=['POST'])
def save_schedule():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    # Get the plan data
    plan_data = request.form.get('plan_data')
    goal = request.form.get('goal')
    
    if not plan_data:
        # Try to get from session if not in form
        current_plan = session.get('current_plan')
        if current_plan:
            plan_data = current_plan['plan']
            goal = current_plan['goal']
            # Get the deadline from session too
            deadline_str = current_plan.get('deadline')
        else:
            flash("No plan data found.", "danger")
            return redirect(url_for('scheduler'))
    else:
        # Get deadline from session if available
        current_plan = session.get('current_plan', {})
        deadline_str = current_plan.get('deadline')
    
    # Check if user has Google Calendar connected
    creds = load_credentials(session['user_id'])
    if not creds:
        flash("Please connect your Google Calendar first.", "warning")
        return redirect(url_for('authorize'))
    
    try:
        # Parse the time blocks from the plan
        time_blocks = parse_time_blocks(plan_data)
        
        if not time_blocks:
            flash("Could not parse time blocks from the plan.", "danger")
            return redirect(url_for('scheduler'))
        
        # Get timezone and current time
        import pytz
        ny_tz = pytz.timezone('America/New_York')
        current_time = datetime.now(ny_tz)
        today = current_time.date()
        
        # Parse deadline from session
        deadline_datetime = None
        if deadline_str:
            try:
                deadline_datetime = datetime.fromisoformat(deadline_str)
                if deadline_datetime.tzinfo is None:
                    deadline_datetime = ny_tz.localize(deadline_datetime)
            except:
                deadline_datetime = current_time + timedelta(hours=6)  # Default fallback
        else:
            deadline_datetime = current_time + timedelta(hours=6)  # Default fallback
        
        events_created = 0
        
        for block in time_blocks:
            # Convert time strings to datetime objects with proper overnight handling
            start_dt = convert_to_datetime(block['start_time'], today, current_time, deadline_datetime)
            end_dt = convert_to_datetime(block['end_time'], today, current_time, deadline_datetime)
            
            if start_dt and end_dt:
                # Add timezone info if not already present
                if start_dt.tzinfo is None:
                    start_dt = ny_tz.localize(start_dt)
                if end_dt.tzinfo is None:
                    end_dt = ny_tz.localize(end_dt)
                
                # Handle case where end time is before start time (spans midnight)
                if end_dt <= start_dt:
                    end_dt = end_dt + timedelta(days=1)
                
                # Create event description
                description = f"Goal: {goal}\n\n{block['details']}"
                if block['duration']:
                    description += f"\n\nDuration: {block['duration']}"
                
                # Create calendar event using your existing function
                event_id = create_task_event(
                    creds=creds,
                    task_title=block['task'],
                    task_description=description,
                    start_time=start_dt.isoformat(),
                    duration_minutes=int((end_dt - start_dt).total_seconds() / 60)
                )
                
                if event_id:
                    events_created += 1
                    print(f"Created event: {block['task']} from {start_dt} to {end_dt}")
                else:
                    print(f"Failed to create event: {block['task']}")
        
        if events_created > 0:
            flash(f"Successfully created {events_created} calendar events!", "success")
        else:
            flash("Failed to create calendar events. Please try again.", "danger")
            
    except Exception as e:
        print(f"Error saving schedule: {e}")
        flash("Error saving schedule to calendar. Please try again.", "danger")
    
    return redirect(url_for('scheduler'))
"""


if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port, debug=True)