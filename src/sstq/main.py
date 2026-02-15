from sstq import create_app
from sstq.extensions import db

app = create_app()

# when this file is ran, the DB is created and application is started
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    # Listen on all interfaces so the app is reachable from your phone on the same Wi-Fi.
    # does not work on mobile no matter what I try, might have to fix later
    app.run(debug=True, host="0.0.0.0", port=8000)