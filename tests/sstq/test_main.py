from sstq.extensions import db
from sstq.models import Breakdown, Claim, Product


def login(client, username="testuser", password="1234"):
    return client.post("/login", data={
        "username": username,
        "password": password,
        "action": "login"
    })


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200


def test_register(client):
    response = client.post(
        "/login",
        data={
            "username": "newuser",
            "password": "1234",
            "action": "register",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Account successfully created" in response.data


def test_register_cannot_self_assign_verifier(client, app_instance):
    client.post(
        "/login",
        data={
            "username": "newverifier",
            "password": "1234",
            "action": "register",
            "is_verifier": "on",
        },
        follow_redirects=True,
    )

    with app_instance.app_context():
        from sstq.models import User

        saved_user = User.query.filter_by(username="newverifier").first()
        assert saved_user is not None
        assert saved_user.role == "consumer"


def test_login(client):
    response = login(client)
    assert response.status_code == 302


def test_add_product_requires_login(client):
    response = client.get("/add_product")
    assert response.status_code in (302, 401, 403)


def test_add_product_logged_in(logged_in_client):
    response = logged_in_client.get("/add_product")
    assert response.status_code == 200
    assert b"Add Product" in response.data


def test_add_product_post_creates_product(logged_in_client, app_instance):
    response = logged_in_client.post(
        "/add_product",
        data={
            "barcode": "999",
            "name": "Test Product",
            "category": "Food",
            "brand": "Brand",
            "description": "Desc",
            "timeline_rows": "Raw Materials|Spain||2025-01-01|2025-01-02|Harvested",
            "breakdown_rows": "Olive Oil|Spain|100|Single-origin",
            "claim_rows": "Origin|Sourced from Spain|verified|Checked by verifier",
            "evidence_rows": "1|Certificate|Verifier Org|2025-01-03|Confirms origin|",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Product created successfully." in response.data

    with app_instance.app_context():
        product = db.session.get(Product, "999")
        assert product is not None
        assert product.name == "Test Product"


def test_product_compare_page(logged_in_client, app_instance):
    with app_instance.app_context():
        product_a = Product(
            barcode="111",
            name="Compare Product A",
            category="Food",
            brand="Brand A",
            description="First comparison product",
        )
        product_b = Product(
            barcode="222",
            name="Compare Product B",
            category="Luxury",
            brand="Brand B",
            description="Second comparison product",
        )
        db.session.add_all([product_a, product_b])
        db.session.flush()

        db.session.add_all(
            [
                Breakdown(product_barcode="111", breakdown_name="Cocoa", country="Brazil", percentage=65),
                Breakdown(product_barcode="222", breakdown_name="Leather", country="Italy", percentage=90),
                Claim(
                    product_barcode="111",
                    claim_type="Sustainability",
                    claim_text="Uses certified farms",
                    confidence_label="verified",
                ),
                Claim(
                    product_barcode="222",
                    claim_type="Origin",
                    claim_text="Finished in Italy",
                    confidence_label="partially-verified",
                ),
            ]
        )
        db.session.commit()

    response = logged_in_client.get("/products/compare?ids=111,222")

    assert response.status_code == 200
    assert b"Product Comparison" in response.data
    assert b"Compare Product A" in response.data
    assert b"Compare Product B" in response.data


def test_product_compare_requires_two_products(logged_in_client):
    response = logged_in_client.get("/products/compare?ids=111", follow_redirects=True)

    assert response.status_code == 200
    assert b"Select exactly two products to compare." in response.data
