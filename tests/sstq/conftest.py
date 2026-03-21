import pytest
from sstq.main import app, db
from sstq.models import User


@pytest.fixture
def app_instance():
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    with app.app_context():
        db.drop_all()
        db.create_all()

        user = User(username="testuser", role="verifier")
        user.set_password("1234")

        db.session.add(user)
        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture
def logged_in_client(client):
    client.post("/login", data={
        "username": "testuser",
        "password": "1234",
        "action": "login"
    })
    return client
