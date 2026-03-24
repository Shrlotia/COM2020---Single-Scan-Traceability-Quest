"""Create the default admin accounts used by the team.

Usage:
  python ./src/sstq/scripts/create_admins.py
"""

from sstq import create_app
from sstq.extensions import db
from sstq.models import User

admins = [
    ("dawid", "flaskapp123"),
    ("cai", "flaskapp123"),
    ("simba", "flaskapp123"),
    ("ali", "flaskapp123"),
    ("johnny", "flaskapp123"),
    ("sylvester", "flaskapp123")
]

def main() -> None:
    app = create_app()

    with app.app_context():
        for username, password in admins:
            if User.query.filter_by(username=username).first():
                print(f"{username} already exists")
                continue

            user = User(username=username, role="admin")
            user.set_password(password)
            db.session.add(user)

        db.session.commit()
        print("All admin accounts created")


if __name__ == "__main__":
    main()
