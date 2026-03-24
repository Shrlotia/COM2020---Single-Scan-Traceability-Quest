from sstq.extensions import db
from sstq.models import User


def test_admin_access_denied_for_consumer(client, app_instance):
    with app_instance.app_context():
        consumer = User(username="consumer-user", role="consumer")
        consumer.set_password("1234")
        db.session.add(consumer)
        db.session.commit()

    client.post(
        "/login",
        data={"username": "consumer-user", "password": "1234", "action": "login"},
    )
    response = client.get("/admin")

    assert response.status_code == 403


def test_admin_access_allowed_for_verifier(logged_in_client):
    response = logged_in_client.get("/admin")
    assert response.status_code == 200


def test_admin_access_as_admin(admin_client):
    response = admin_client.get("/admin")
    assert response.status_code == 200


def test_admin_can_create_user(admin_client, app_instance):
    response = admin_client.post(
        "/admin/users/create",
        data={"username": "created-user", "password": "1234", "role": "consumer"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"User created." in response.data

    with app_instance.app_context():
        saved_user = User.query.filter_by(username="created-user").first()
        assert saved_user is not None
        assert saved_user.role == "consumer"
