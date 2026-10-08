def test_request_level_validation_empty_recipients(client):
    """Empty recipients list returns HTTP 422."""
    payload = {
        "title": "FastAPI Workshop",
        "issuer_name": "Backend Guild",
        "recipients": []
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_request_level_validation_missing_title(client):
    """Missing title field returns HTTP 422."""
    payload = {
        "issuer_name": "Backend Guild",
        "recipients": [{"name": "Carol", "email": "carol@example.com"}]
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_request_level_validation_exceeds_1000_recipients(client):
    """More than 1000 recipients returns HTTP 422."""
    recipients = [{"name": f"User {i}", "email": f"user{i}@example.com"} for i in range(1001)]
    payload = {
        "title": "Mega Conference",
        "issuer_name": "Tech Corp",
        "recipients": recipients
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_recipient_level_validation_partial_failures(client):
    """
    Invalid email, blank name, and duplicate email mark individual certificates as FAILED,
    while valid recipients still succeed.
    """
    payload = {
        "title": "Data Science Masterclass",
        "issuer_name": "AI Institute",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "   ", "email": "blankname@example.com"},           # Blank name
            {"name": "Bad Email User", "email": "not-an-email"},          # Invalid email
            {"name": "Duplicate User 1", "email": "dup@example.com"},     # First instance
            {"name": "Duplicate User 2", "email": "dup@example.com"},     # Duplicate instance
        ]
    }

    response = client.post("/jobs", json=payload)
    assert response.status_code == 202

    data = response.json()
    job_id = data["id"]
    assert data["total_count"] == 5

    # Check certificate list endpoint
    certs_resp = client.get(f"/jobs/{job_id}/certificates")
    assert certs_resp.status_code == 200
    certs_data = certs_resp.json()["certificates"]

    # Map certs by recipient email
    by_email = {c["recipient_email"]: c for c in certs_data}

    # Valid User -> SUCCESS
    assert by_email["valid@example.com"]["status"] == "SUCCESS"
    assert by_email["valid@example.com"]["error_message"] is None

    # Blank name -> FAILED with error message
    blank_cert = [c for c in certs_data if c["recipient_email"] == "blankname@example.com"][0]
    assert blank_cert["status"] == "FAILED"
    assert "blank or whitespace" in blank_cert["error_message"]

    # Bad email -> FAILED with error message
    bad_email_cert = [c for c in certs_data if c["recipient_email"] == "not-an-email"][0]
    assert bad_email_cert["status"] == "FAILED"
    assert "Invalid email format" in bad_email_cert["error_message"]

    # Duplicate emails -> First succeeds, second fails with error message
    dup_certs = [c for c in certs_data if c["recipient_email"] == "dup@example.com"]
    statuses = [c["status"] for c in dup_certs]
    assert "SUCCESS" in statuses
    assert "FAILED" in statuses
    failed_dup = [c for c in dup_certs if c["status"] == "FAILED"][0]
    assert "Duplicate email in request" in failed_dup["error_message"]
