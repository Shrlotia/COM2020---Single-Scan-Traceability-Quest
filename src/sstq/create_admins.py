# this class exists to create the 'admin' accounts for all of the team members
# so far, they don't provide any real differences compared to 'verifier' accounts but this could change in the future
# if you accidentally delete all the users, just type 'python3 create_admins.py' in the terminal
from sstq.main import app
from sstq.config import db
from sstq.models import User

# usernames and passwords (might change later)
admins = [
    ("dawid", "flaskapp123"),
    ("cai", "flaskapp123"),
    ("simba", "flaskapp123"),
    ("ali", "flaskapp123"),
    ("johnny", "flaskapp123"),
    ("sylvester", "flaskapp123")
]

# the 'app_context' part essentially simulates how the app would react if it was actually running in your browser
# without this, you couldn't query the DB because the tables haven't been 'initialised' so to speak
with app.app_context():
    for username, password in admins:
        if User.query.filter_by(username=username).first():
            print(f"{username} already exists")
            continue
        
        # creates every user account with the role of 'admin'
        user = User(username=username, role="admin")
        user.set_password(password)
        db.session.add(user)
        
    # the DB transaction is committed once the RDBMS knows there are no errors
    db.session.commit()
    print("All admin accounts created")