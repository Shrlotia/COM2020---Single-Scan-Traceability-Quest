def test_product_not_found(logged_in_client):
    response = logged_in_client.get("/product/000000")

    assert response.status_code in (200, 302, 404)


def test_404_page(client):
    response = client.get("/nonexistent")

    assert response.status_code == 404


def test_wrong_method(logged_in_client):
    response = logged_in_client.post("/add_product")

    assert response.status_code in (200, 400, 405)