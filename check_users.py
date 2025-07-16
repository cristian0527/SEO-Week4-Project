import sqlalchemy as db
from models.db_models import get_engine, users

engine = get_engine()
conn = engine.connect()

results = conn.execute(db.select(users)).fetchall()
for row in results:
    print(f"ID:{row.id}, Username: {row.username}, Email: {row.email}")