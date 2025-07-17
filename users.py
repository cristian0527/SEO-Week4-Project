import sqlalchemy as db
from models.db_models import get_engine, users

engine = get_engine()
conn = engine.connect()
metadata = db.MetaData()

# Add user to database
def add_user(user):
    insert_query = db.insert(users).values(
        username=user['username'],
        email=user['email'],
        hashed_password=user['password']
    )
    with engine.begin() as conn:  
        conn.execute(insert_query)

# Get User by email (from login / register)
def get_user_by_email(email):
    get_email = db.select(users).where(users.c.email == email)
    return conn.execute(get_email).mappings().fetchone()

# Get user by ID 
def get_user_by_id(user_id):
    get_id = db.select(users).where(users.c.id == user_id)
    return conn.execute(get_email).mappings().fetchone()

def delete_user(user_email):
    delete_stmt = db.delete(users).where(users.c.email == user_email)
    with engine.begin() as conn:
        result = conn.execute(delete_stmt)
        return result.rowcount