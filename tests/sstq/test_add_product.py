def test_add_product_success(logged_in_client):
    response = logged_in_client.post(
        "/add_product",
        data={
            "barcode": "12345",
            "name": "Test Product",
            "category": "Food",
            "brand": "Brand A",
            "description": "Test Description",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Product created successfully." in response.data


def test_add_product_duplicate(logged_in_client):
    payload = {
        "barcode": "111",
        "name": "Product A",
        "category": "Food",
        "brand": "Brand",
        "description": "Desc",
    }

    logged_in_client.post("/add_product", data=payload, follow_redirects=True)
    response = logged_in_client.post("/add_product", data=payload, follow_redirects=True)

    assert response.status_code == 200
    assert b"Barcode already exists." in response.data


def test_add_product_missing_field(logged_in_client):
    response = logged_in_client.post(
        "/add_product",
        data={
            "barcode": "",
            "name": "",
            "category": "Food",
            "brand": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Barcode, product name, category and brand are required." in response.data


def test_add_product_invalid_timeline_date(logged_in_client):
    response = logged_in_client.post(
        "/add_product",
        data={
            "barcode": "444",
            "name": "Bad Dates",
            "category": "Food",
            "brand": "Brand",
            "description": "Desc",
            "timeline_rows": "Processing|UK||2025-02-02|2025-01-01|Invalid dates",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"end date before start date" in response.data


def test_validate_barcode(logged_in_client):
    response = logged_in_client.post("/validate_barcode", json={"barcode": "999"})
    data = response.get_json()

    assert data["valid"] is True
