import sqlalchemy as db
import datetime

# Connect to SQLite DB (this creates the file automatically)
engine = db.create_engine('sqlite:///studyplanner.db')
metadata = db.MetaData()

# Users table: web app's regristered users
users = db.Table('users', metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column('username', db.String, unique=True, nullable=False),
    db.Column('email', db.String, unique=True, nullable=False),  # login email
    db.Column('hashed_password', db.String, nullable=False),
    db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)
)

# OAuth tokens table: stores Google token info for each user
oauth_tokens = db.Table('oauth_tokens', metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), nullable=False),
    db.Column('google_email', db.String),
    db.Column('access_token', db.Text, nullable=False),
    db.Column('refresh_token', db.Text),
    db.Column('token_uri', db.String),
    db.Column('client_id', db.String, nullable=False),
    db.Column('client_secret', db.String, nullable=False),
    db.Column('scopes', db.Text),
    db.Column('expiry', db.DateTime),
    db.Column('created_at', db.DateTime, default=datetime.datetime.utcnow)
)

# Create both tables 
metadata.create_all(engine)

#Set up a database connection to import into other files
def get_engine():
    return engine

def get_metadata():
    return metadata

if __name__ == "__main__":
    print("Database and tables have been created.")



