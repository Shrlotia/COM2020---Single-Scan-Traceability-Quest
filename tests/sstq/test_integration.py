def test_full_product_flow(logged_in_client):
    logged_in_client.post(
        "/add_product",
        data={
            "barcode": "555",
            "name": "Milk",
            "category": "Dairy",
            "brand": "BrandX",
            "description": "Fresh milk",
            "timeline_rows": "Raw Materials|United Kingdom||2025-01-01|2025-01-02|Collected",
            "breakdown_rows": "Milk|United Kingdom|100|Whole milk",
            "claim_rows": "Origin|Produced in the UK|verified|Verifier checked",
            "evidence_rows": "1|Certificate|Verifier Org|2025-01-03|Supports the claim|",
        },
        follow_redirects=True,
    )

    response = logged_in_client.get("/product/555")

    assert response.status_code == 200
    assert b"Milk" in response.data
