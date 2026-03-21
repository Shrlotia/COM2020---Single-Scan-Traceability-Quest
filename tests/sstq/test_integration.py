def test_full_product_flow(logged_in_client):
    logged_in_client.get("/add_product", json={
        "productData": {
            "barcode": "555",
            "name": "Milk",
            "category": "Dairy",
            "brand": "BrandX",
            "description": "Fresh milk"
        }
    })

    response = logged_in_client.get("/product/555")

    assert response.status_code == 200
    assert b"Milk" in response.data