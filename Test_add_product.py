#test whether the new product was successfully added
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

#test for duplicate barcodes
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

#test for validate_barcode
def test_validate_barcode(client):
    response = client.post("/validate_barcode",
    json={"barcode": "999"})

    data = response.get_json()

    assert data["valid"] is True


