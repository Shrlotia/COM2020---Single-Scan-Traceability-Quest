import pytest
import sstq.main
from sstq.config import app, db
from sstq.models import User

@pytest.fixture
def client():

    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
   
    with app.app_context():
        #make sure it will be a flash db
        db.drop_all()
        db.create_all()

        user = User(username="testuser", role="verifier")
        user.set_password("1234")

        db.session.add(user)
        db.session.commit()

    with app.test_client() as client:
        #simulated login - login via actual login endpoint
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        
        yield client

    with app.app_context():
        db.session.remove()
        db.drop_all()