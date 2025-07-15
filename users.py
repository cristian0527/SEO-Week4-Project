# mock users database 

users_db = []

def add_user(user):
    users_db.append(user)

def get_user_by_email(email):
    for user in users_db:
        if user['email'] == email:
            return user
    return None