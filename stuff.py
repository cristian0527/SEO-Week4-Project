"""google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
google-generativeai
sqlalchemy
flask-bcrypt
google.genai

Flask==2.3.3
flask-bcrypt==1.0.1
flask-wtf==1.1.1
flask-behind-proxy==0.1.0
wtforms==3.1.1
email_validator>=1.2.1

google-auth==2.29.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.125.0
google-generativeai==0.3.2
sqlalchemy
pytz"
"""
"""
def convert_to_datetime(time_str, base_date):
    """
    #Convert time string like "9:24 PM" to datetime object
    """
    try:
        # Parse time like "9:24 PM" or "09:24 PM"
        time_obj = datetime.strptime(time_str, '%I:%M %p').time()
        return datetime.combine(base_date, time_obj)
    except ValueError:
        try:
            # Try without leading zero
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            return datetime.combine(base_date, time_obj)
        except ValueError:
            return None

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
        else:
            flash("No plan data found.", "danger")
            return redirect(url_for('scheduler'))
    
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
        
        # Get timezone
        ny_tz = pytz.timezone('America/New_York')
        today = datetime.now(ny_tz).date()
        
        events_created = 0
        
        for block in time_blocks:
            # Convert time strings to datetime objects
            start_dt = convert_to_datetime(block['start_time'], today)
            end_dt = convert_to_datetime(block['end_time'], today)
            
            if start_dt and end_dt:
                # Add timezone info
                start_dt = ny_tz.localize(start_dt)
                end_dt = ny_tz.localize(end_dt)
                
                # Handle overnight times (if end time is before start time, it's next day)
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
"""
@app.route('/save_schedule', methods=['POST'])
def save_schedule():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    plan_data = request.form.get('plan_data')
    goal = request.form.get('goal')
    
    # Check if user has Google Calendar connected
    creds = load_credentials(session['user_id'])
    if not creds:
        flash("Please connect your Google Calendar first.", "warning")
        return redirect(url_for('authorize'))
    
    # TODOO: Parse the plan_data and create calendar events
    # For now, just show success message
    flash("Schedule saved to your Google Calendar!", "success")
    return redirect(url_for('scheduler'))
"""


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
        
        # Parse deadline with time
        try:
            # Combine date and time
            deadline_datetime = datetime.strptime(f"{deadline_str} {deadline_time_str}", '%Y-%m-%d %H:%M')
        except ValueError:
            flash("Invalid deadline format.", "danger")
            return render_template('scheduler.html')
        
        # Get current time
        #current_time = datetime.now()
        ny_tz = pytz.timezone('America/New_York')
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
        
        # Generate AI study plan with improved prompt
        current_time = datetime.now()
        prompt = f"""
        You are a study scheduler. Create a specific, actionable study plan.
        
        Goal: {goal}
        Description: {description}
        Current time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}
        Deadline: {deadline_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}
        
        Create a study plan with specific time blocks starting RIGHT NOW until the deadline ONLY. 
        Format each block as:
        - Date & Time: [exact time]
        - Task: [specific task]
        - Duration: [how long]

        Stop at the deadline. Do not plan beyond {deadline_datetime.strftime('%B %d, %Y at %I:%M %p')}.
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


"""
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
        #Deadline: {deadline.strftime('%A, %B %d, %Y')}
        prompt = f"""
        #Goal: {goal}
        #Description: {description}
        #Current time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}
        #Deadline: {deadline_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}
        
        #Current calendar:
        #{calendar_summary}
        
        #Please create a study plan with specific time blocks, avoiding conflicts with the schedule above.
        """
        
        try:
            ai_plan = gemini_study_planner(prompt)
            return render_template('scheduler.html', plan=ai_plan, goal=goal)
        except Exception as e:
            flash("Error generating study plan. Please try again.", "danger")
            return render_template('scheduler.html')
    
    return render_template('scheduler.html')
"""






"""
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
    preferred_time_str = request.form.get('preferred_time')
    schedule_now = request.form.get('schedule_now')
    
    # Validate required fields
    if not title:
        flash("Task title is required.", "danger")
        return redirect(url_for('todo'))
    
    # Handle date format conversion (DD/MM/YYYY to YYYY-MM-DD)
    due_date = None
    if due_date_str:
        try:
            # If frontend sends DD/MM/YYYY format
            if '/' in due_date_str:
                due_date = datetime.strptime(due_date_str, '%d/%m/%Y').date()
            else:
                # If frontend sends YYYY-MM-DD format (HTML date input)
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
    
    due_datetime = None
    if due_date and due_time:
        due_datetime = datetime.combine(due_date, due_time)
    elif due_date:
        due_datetime = datetime.combine(due_date, datetime.min.time())

    #preferred_time = None
    #if preferred_time_str:
       # try:
        #    preferred_time = datetime.strptime(preferred_time_str, '%H:%M').time()
        #except ValueError:
         #   flash("Invalid preferred time format. Use HH:MM format.", "danger")
         #   return redirect(url_for('todo'))
    
    # Create new task
    task_data = {
        'user_id': session['user_id'],
        'title': title,
        'description': description,
        'link': link,
        'due_date': due_datetime,
        #'due_time': due_time,
        #'preferred_time': preferred_time,
        'is_completed': False,
        #'created_at': datetime.now()
    }
    
    # Add to database
    task_id = add_task_to_db(task_data)
    """
    # If user wants to schedule it immediately and has preferred time
    #if schedule_now and preferred_time and due_date:
        #success = schedule_task_to_calendar(session['user_id'], task_id, new_task)
        #if success:
            #flash("Task added and scheduled to your calendar!", "success")
        #else:
            #flash("Task added but failed to schedule to calendar.", "warning")
    #else:
        #flash("Task added successfully!", "success")
    """
    flash("Task added successfully!", "success")
    return redirect(url_for('todo'))
"""

"""
@app.route('/scheduler/', methods=['POST'])
def schedule_task_route(task_id):
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    use_ai = request.form.get('use_ai')
    preferred_time = request.form.get('preferred_time')

    if use_ai:
        # Use Gemini to find optimal time
        return schedule_task_with_ai(session['user_id'], task_id)
    else:
        # Schedule at user's preferred time
        preferred_time = data.get('preferred_time')
        return schedule_task_at_time(session['user_id'], task_id, preferred_time)

@app.route('/calendar')
def calendar():
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))
    
    creds = load_credentials(session['user_id'])
    if not creds:
        return redirect(url_for('authorize'))
    
    events = list_upcoming_events(creds)
    completed_tasks = get_completed_tasks(session['user_id'])
    
    return render_template('calendar.html', events=events, completed_tasks=completed_tasks)

@app.route('api/calendar/events')
def get_calendar_events():
    if 'user_id' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))
    
    creds = load_credentials(session['user_id'])
    if not creds:
        flash("Please connect your Google Calendar first.", "warning")
        return redirect(url_for('authorize'))
    
    events = list_upcoming_events(creds)
    return jsonify({'events': events})

"""
#@app.route('/scheduler')
#def scheduler():
#    if 'user_id' not in session:
#        flash("Please log in first.")
#        return redirect(url_for('login'))
#    
#    return render_template('scheduler.html')
"""

@app.route('/scheduler', methods=['GET', 'POST'])
def scheduler():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        goal = request.form.get('goal')
        description = request.form.get('description')
        deadline = request.form.get('deadline')

        if not goal or not deadline or not description:
            flash("Goal, description, and deadline are required", "danger")
            return redirect(url_for('scheduler'))
        
        # Handle both DD/MM/YYYY and YYYY-MM-DD formats
        try:
            if '/' in deadline:
                # DD/MM/YYYY format
                deadline_date = datetime.strptime(deadline, '%d/%m/%Y')
            else:
                # YYYY-MM-DD format (HTML date input)
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d')
        except ValueError:
            flash("Please use DD/MM/YYYY or YYYY-MM-DD format for deadline", "danger")
            return redirect(url_for('scheduler'))
        
        # Get user's calendar
        creds = load_credentials(session['user_id'])
        if not creds:
            flash("Please connect your Google Calendar first.", "warning")
            return redirect(url_for('authorize'))
        
        events = list_upcoming_events(creds)

        calendar_summary = "\n".join([
            f"{e['start'].get('dateTime', e['start'].get('date'))} - {e['summary']}" for e in events
        ])
        
        prompt = f"""
        #You are an supportive academic planning assistant.

        #The user's goal: "{goal}"
        #Deadline: {deadline_date.strftime('%A, %B %d, %Y')}

        #Description from user:
        #"{description}"

        #The user's current schedule is:
        #{calendar_summary}

        #Please return a study plan with specific daily time blocks (1-2 suggestions per day), avoiding conflicts with the calendar above unless otherwise noted. Format clearly by day of the week.
        """

        ai_output = gemini_study_planner(prompt)
        return render_template("scheduler.html", plan=ai_output)
    
    return render_template("scheduler.html")

@app.route('/api/schedule/save', methods=['POST'])
def save_schedule():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    
    data = request.get_json()
    schedule_blocks = data.get('schedule_blocks', [])
    
    creds = load_credentials(session['user_id'])
    if not creds:
        flash("Please connect your Google Calendar first.", "warning")
        return redirect(url_for('authorize'))
    
    # Add each schedule block to Google Calendar
    for block in schedule_blocks:
        create_calendar_event(creds, {
            'summary': block.get('title'),
            'description': block.get('description'),
            'start': block.get('start_time'),
            'end': block.get('end_time')
        })
    
    flash("Schedule saved to your Google Calendar!", "success")
    return redirect(url_for('scheduler'))
"""
"""
# HELPER FUNCTIONS
def format_date_for_display(date_obj):
    Convert date object to DD/MM/YYYY format for display
    if date_obj:
        return date_obj.strftime('%d/%m/%Y')
    return None

def format_datetime_for_display(datetime_obj):
    Convert datetime object to DD/MM/YYYY HH:MM format for display
    if datetime_obj:
        return datetime_obj.strftime('%d/%m/%Y %H:%M')
    return None

def add_task_to_db(task_data):
    from users import add_task_to_db as db_add_task
    return db_add_task(task_data)

def update_task_completion(task_id, completed):
    from users import update_task_completion as db_update_completion
    return db_update_completion(task_id, completed)

def schedule_task_to_calendar(user_id, task_id, task_data):
    from users import get_task_by_id, update_task_schedule
    from apis.google_calendar import create_task_event
    
    # Get user credentials
    creds = load_credentials(user_id)
    if not creds:
        return False
    
    # Create calendar event
    start_time = f"{task_data['due_date']}T{task_data['preferred_time']}"
    event_id = create_task_event(
        creds, 
        task_data['title'], 
        task_data['description'], 
        start_time
    )
    
    if event_id:
        # Update task with Google event ID
        scheduled_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        update_task_schedule(task_id, scheduled_datetime, event_id)
        return True
    return False

def schedule_task_with_ai(user_id, task_id):
    from users import get_task_by_id
    
    # Get task details
    task = get_task_by_id(task_id)
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for('todo'))
    
    # Get user's calendar to find optimal time
    creds = load_credentials(user_id)
    if not creds:
        flash("Please connect your Google Calendar first.", "warning")
        return redirect(url_for('authorize'))
    
    events = list_upcoming_events(creds)
    calendar_summary = "\n".join([f"{e['start'].get('dateTime', e['start'].get('date'))} - {e['summary']}" for e in events])
    
    # Ask Gemini for optimal scheduling
    ai_request = f"""
    #I need to schedule this task: {task.title}
    #Description: {task.description}
    #Due date: {task.due_date}
    
    #Current calendar:
    #{calendar_summary}
    
    #Please suggest the best time to work on this task (provide specific date and time in YYYY-MM-DDTHH:MM format).
    """
    
    ai_response = gemini_study_planner(ai_request)
    
    # You would need to parse the AI response to extract the suggested time
    # For now, flash the suggestion and redirect
    flash(f"AI Suggestion: {ai_response}", "info")
    return redirect(url_for('todo'))

def schedule_task_at_time(user_id, task_id, preferred_time):
    from users import get_task_by_id
    
    task = get_task_by_id(task_id)
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for('todo'))
    
    # Schedule at the preferred time
    task_data = {
        'title': task.title,
        'description': task.description,
        'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
        'preferred_time': preferred_time
    }
    
    success = schedule_task_to_calendar(user_id, task_id, task_data)
    if success:
        flash("Task scheduled successfully!", "success")
    else:
        flash("Failed to schedule task.", "danger")
    
    return redirect(url_for('todo'))
"""