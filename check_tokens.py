import sqlalchemy as db
from models.db_models import get_engine, oauth_tokens

engine = get_engine()
conn = engine.connect()

tokens = conn.execute(db.select(oauth_tokens)).fetchall()
for t in tokens:
    #print(f"User ID:{t.user_id}, Email: {t.google_email}, Expires:{t.expiry}")
    print(f"User ID: {t.user_id}")
    print(f"Google Email: {t.google_email}")
    print(f"Access Token: {t.access_token}")
    print(f"Expires: {t.expiry}")

    