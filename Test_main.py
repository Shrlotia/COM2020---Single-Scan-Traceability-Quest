# login helper
def login(client, username="testuser", password="1234"):
    return client.post("/login", data={
        "username": username,
        "password": password,
        "action": "login"
    })


#test for homepage
def test_home(client):
    response = client.get("/")
    assert response.status_code == 200


#test for register
def test_register(client):
    response = client.post("/login", data={
        "username": "newuser",
        "password": "1234",
        "action": "register"
    })

    assert response.status_code == 302  #it will be redirected


#test for login
def test_login(client):
    response = login(client)
    assert response.status_code == 302


#test for add product(JSON)
def test_add_product(client):
    response = client.get(
        "/add_product",
        json={
            "productData": {
                "barcode": "999",
                "name": "Test Product",
                "category": "Food",
                "brand": "Brand",
                "description": "Desc",
                "image": "img.jpg"
            }
        }
    )

    assert response.status_code == 200
    assert response.json["success"] is True
