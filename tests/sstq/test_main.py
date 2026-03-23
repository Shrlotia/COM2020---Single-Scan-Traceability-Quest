# login helper
from sstq.main import db
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
    response = client.post("/login", data={
        "username": "newuser",
        "password": "1234",
        "action": "register"
    })

    assert response.status_code == 302


def test_login(client):
    response = login(client)
    assert response.status_code == 302


def test_add_product_requires_login(client):
    response = client.get("/add_product")
    assert response.status_code in (302, 401, 403)


def test_add_product_logged_in(logged_in_client):
    response = logged_in_client.get("/add_product", json={
        "productData": {
            "barcode": "999",
            "name": "Test Product",
            "category": "Food",
            "brand": "Brand",
            "description": "Desc",
            "image": "img.jpg"
        }
    })

    assert response.status_code == 200
    assert response.json["success"] is True


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
