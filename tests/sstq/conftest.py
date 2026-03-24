import pytest
from sstq import create_app
from sstq.extensions import db
from sstq.models import User


@pytest.fixture
def app_instance(tmp_path):
    database_path = tmp_path / "test_trace_quest.db"
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        "ALLOW_VERIFIER_SELF_REGISTER": False,
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


@pytest.fixture
def admin_client(client, app_instance):
    with app_instance.app_context():
        admin = User(username="admin", role="admin")
        admin.set_password("1234")
        db.session.add(admin)
        db.session.commit()

    client.post("/login", data={
        "username": "admin",
        "password": "1234",
        "action": "login",
    })
    return client
