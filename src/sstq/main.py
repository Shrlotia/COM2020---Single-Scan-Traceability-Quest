import os

from sstq import create_app
from sstq.extensions import db

app = create_app()

# when this file is ran, the DB is created and application is started
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(
        debug=os.environ.get("FLASK_DEBUG", "").strip() == "1",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
