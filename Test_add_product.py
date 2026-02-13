def test_add_product_success(client):
    payload = {
        "productData": {
            "barcode": "12345",
            "name": "Test Product",
            "category": "Food",
            "brand": "Brand A",
            "description": "Test Description",
            "image": "test.jpg"
        }
    }

    response = client.get("/add_product", json=payload)
    data = response.get_json()

    assert response.status_code == 200
    assert data ["success"] is True
    assert data ["barcode"] == "12345"

def test_add_product_duplicate(client):
    payload = {
        "productData": {
            "barcode": "111",
            "name": "Product A",
            "category": "Food",
            "brand": "Brand",
            "description": "Desc"
        }
    }

    client.get("/add_product", json=payload)
    response = client.get("/add_product", json=payload)

    assert response.status_code == 400

