import pytest
import main
from config import app, db
from models import User

@pytest.fixture
def client():

    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    #make a fake user
    with app.app_context():
        #make sure it will be a flash db
        db.drop_all()
        db.create_all()

        user = User(username="testuser", role="verifier")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

    with app.test_client() as client:
        #simulated login
        with client.session_transaction() as session:
            session["_user_id"] =  "1"

        yield client

    with app.app_context():
        db.session.remove()
        db.drop_all()




