def test_create_job_success(client):
    """
    Submitting a valid job returns 202 Accepted, a job UUID, and initial PENDING status.
    Polling GET /jobs/{job_id} afterwards verifies the background task completed processing.
    """
    payload = {
        "title": "Python Developer Bootcamp",
        "issuer_name": "Tech Academy",
        "issue_date": "2026-10-08",
        "recipients": [
            {"name": "Alice Johnson", "email": "alice@example.com"},
            {"name": "Bob Smith", "email": "bob@example.com"}
        ]
    }

    response = client.post("/jobs", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["title"] == "Python Developer Bootcamp"
    assert data["issuer_name"] == "Tech Academy"
    assert data["total_count"] == 2
    assert data["success_count"] == 0
    assert data["failure_count"] == 0
    assert data["status"] == "PENDING"

    # Query GET /jobs/{job_id} after background task execution
    job_id = data["id"]
    status_resp = client.get(f"/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["success_count"] == 2
    assert status_data["failure_count"] == 0
    assert status_data["progress_percentage"] == 100.0


def test_create_job_health_check(client):
    """
    Health check endpoint returns 200 OK.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
