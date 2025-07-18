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