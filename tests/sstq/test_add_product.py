import pytest

#test whether the new product was successfully added
def test_add_product_success(logged_in_client):
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

    response = logged_in_client.post("/add_product", json=payload)
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True


def test_add_product_duplicate(logged_in_client):
    payload = {
        "productData": {
            "barcode": "111",
            "name": "Product A",
            "category": "Food",
            "brand": "Brand",
            "description": "Desc"
        }
    }

    logged_in_client.post("/add_product", json=payload)
    response = logged_in_client.post("/add_product", json=payload)

    assert response.status_code == 400


def test_add_product_missing_field(logged_in_client):
    with pytest.raises(Exception):
        logged_in_client.post("/add_product", json={
            "productData": {
                "barcode": ""
            }
        })


def test_validate_barcode(logged_in_client):
    response = logged_in_client.post("/validate_barcode", json={"barcode": "999"})
    data = response.get_json()

    assert data["valid"] is True
