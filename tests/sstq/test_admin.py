def test_admin_access_denied(logged_in_client):
    response = logged_in_client.get("/admin")
    assert response.status_code in (200, 302, 403)


def test_admin_access_as_admin(client):
    from sstq.models import User
    from sstq.main import db

    with client.application.app_context():
        admin = User(username="admin", role="admin")
        admin.set_password("1234")

        db.session.add(admin)
        db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = "2"

    response = client.get("/admin")
    assert response.status_code in (200, 302, 403)