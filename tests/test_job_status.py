def test_job_status_all_successful(client):
    """
    When all recipients are valid, progress percentage is 100.0% and status is COMPLETED.
    """
    payload = {
        "title": "Machine Learning Fundamentals",
        "issuer_name": "AI Academy",
        "recipients": [
            {"name": "David Miller", "email": "david@example.com"},
            {"name": "Eva Green", "email": "eva@example.com"}
        ]
    }

    create_resp = client.post("/jobs", json=payload)
    assert create_resp.status_code == 202
    job_id = create_resp.json()["id"]

    status_resp = client.get(f"/jobs/{job_id}")
    assert status_resp.status_code == 200

    data = status_resp.json()
    assert data["status"] == "COMPLETED"
    assert data["total_count"] == 2
    assert data["success_count"] == 2
    assert data["failure_count"] == 0
    assert data["progress_percentage"] == 100.0


def test_job_status_all_failed(client):
    """
    When all recipients fail pre-validation, final status is FAILED.
    """
    payload = {
        "title": "Cloud Computing 101",
        "issuer_name": "Cloud Org",
        "recipients": [
            {"name": "   ", "email": "bad1@example.com"},
            {"name": "User 2", "email": "invalid-email"}
        ]
    }

    create_resp = client.post("/jobs", json=payload)
    assert create_resp.status_code == 202
    job_id = create_resp.json()["id"]

    status_resp = client.get(f"/jobs/{job_id}")
    assert status_resp.status_code == 200

    data = status_resp.json()
    assert data["status"] == "FAILED"
    assert data["total_count"] == 2
    assert data["success_count"] == 0
    assert data["failure_count"] == 2
    assert data["progress_percentage"] == 100.0
