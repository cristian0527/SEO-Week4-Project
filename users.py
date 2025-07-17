import sqlalchemy as db
from datetime import datetime
from models.db_models import get_engine, users, tasks

engine = get_engine()
conn = engine.connect()
metadata = db.MetaData()


# Add user to database
def add_user(user):
    insert_query = db.insert(users).values(
        username=user['username'],
        email=user['email'],
        hashed_password=user['hashed_password']
    )
    with engine.begin() as conn:  
        conn.execute(insert_query)


# Get User by email (from login / register)
def get_user_by_email(email):
    get_email = db.select(users).where(users.c.email == email)
    with engine.connect() as conn:
        return conn.execute(get_email).fetchone()

# Get user by ID 
def get_user_by_id(user_id):
    get_id = db.select(users).where(users.c.id == user_id)
    with engine.connect() as conn:
        return conn.execute(get_id).fetchone()

def delete_user(user_email):
    delete_stmt = db.delete(users).where(users.c.email == user_email)
    with engine.begin() as conn:
        result = conn.execute(delete_stmt)
        return result.rowcount

#NEW but let's see if used
def get_unscheduled_tasks(user_id):
    query = db.select(tasks).where(
        tasks.c.user_id == user_id,
        tasks.c.scheduled_time == None,
        tasks.c.is_completed == False
    )
    with engine.begin() as conn:
        return conn.execute(query).fetchall()

#NEW FUNCTIONS
def get_tasks_by_user(user_id):
    query = db.select(tasks).where(tasks.c.user_id == user_id).order_by(tasks.c.due_date)
    with engine.connect() as conn:
        return conn.execute(query).fetchall()

def add_task_to_db(task_data):
    insert_query = db.insert(tasks).values(
        user_id=task_data['user_id'],
        title=task_data['title'],
        description=task_data.get('description', ''),
        due_date=task_data.get('due_date'),
        scheduled_time=task_data.get('scheduled_time'),
        is_completed=task_data.get('is_completed', False),
        google_event=task_data.get('google_event'),
        #created_at=datetime.now()
    )
    with engine.begin() as conn:
        result = conn.execute(insert_query)
        return result.lastrowid

def update_task_compeletion(task_id, completed):
    update_query = db.update(tasks).where(tasks.c.id == task_id).values(
        is_completed=completed
    )
    with engine.begin() as conn:
        conn.execute(update_query)

def get_task_by_id(task_id):
    query = db.update(tasks).where(tasks.c.id == task_id)
    with engine.connect() as conn:
        conn.execute(query).fetchone()

def update_task_schedule(task_id, scheduled_time, google_event_id=None):
    update_query = db.update(tasks).where(tasks.c.id == task_id).values(
    scheduled_time=scheduled_time,
    google_event=google_event_id
    )
    with engine.begin() as conn:
        conn.execute(update_query)

def get_all_tasks_by_user(user_id):
    query = db.update(tasks).where(tasks.c.user_id == user_id).order_by(tasks.c.created_at.desc())
    
    with engine.connect() as conn:
        conn.execute(query).fetchall()

def get_completed_tasks(user_id):
    query = db.select(tasks).where(
        tasks.c.user_id == user_id,
        tasks.c.is_completed == True
    ).order_by(tasks.c.created_at.desc())
    with engine.connect() as conn:
        return conn.execute(query).fetchall()

def get_pending_tasks(user_id):
    query = db.select(tasks).where(
        tasks.c.user_id == user_id,
        tasks.c.is_completed == False
    ).order_by(tasks.c.created_at.desc())
    with engine.connect() as conn:
        return conn.execute(query).fetchall()


"""
# Add user to database
def add_user(user):
    insert_query = db.insert(users).values(
        username=user['username'],
        email=user['email'],
        hashed_password=user['hashed_password']
    )
    conn.execute(insert_query)
    conn.commit()
"""