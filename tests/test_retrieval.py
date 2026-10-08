def test_download_single_certificate(client):
    """
    Downloading a successfully generated certificate returns 200 OK, application/pdf media type,
    and valid PDF binary data.
    """
    payload = {
        "title": "API Design Mastery",
        "issuer_name": "API Guild",
        "recipients": [{"name": "Grace Hopper", "email": "grace@example.com"}]
    }

    create_resp = client.post("/jobs", json=payload)
    job_id = create_resp.json()["id"]

    # Retrieve certificate ID
    certs_resp = client.get(f"/jobs/{job_id}/certificates")
    cert = certs_resp.json()["certificates"][0]
    cert_id = cert["id"]

    # Download single certificate
    dl_resp = client.get(f"/certificates/{cert_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/pdf"
    assert dl_resp.content.startswith(b"%PDF")


def test_download_job_zip(client):
    """
    Downloading a job ZIP archive returns 200 OK and application/zip media type.
    """
    payload = {
        "title": "Fullstack Engineering",
        "issuer_name": "Code School",
        "recipients": [
            {"name": "Hank Hill", "email": "hank@example.com"},
            {"name": "Ivy Chen", "email": "ivy@example.com"}
        ]
    }

    create_resp = client.post("/jobs", json=payload)
    job_id = create_resp.json()["id"]

    zip_resp = client.get(f"/jobs/{job_id}/download")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"
    assert len(zip_resp.content) > 0


def test_retrieval_404_not_found(client):
    """
    Requesting non-existent certificate or job returns 404 Not Found.
    """
    cert_resp = client.get("/certificates/non-existent-uuid/download")
    assert cert_resp.status_code == 404

    job_resp = client.get("/jobs/non-existent-uuid/download")
    assert job_resp.status_code == 404


def test_retrieval_409_conflict_failed_cert(client):
    """
    Attempting to download a failed certificate returns HTTP 409 Conflict.
    """
    payload = {
        "title": "Security Operations",
        "issuer_name": "SecOps",
        "recipients": [{"name": "   ", "email": "invalid-blank-name@example.com"}]
    }

    create_resp = client.post("/jobs", json=payload)
    job_id = create_resp.json()["id"]

    certs_resp = client.get(f"/jobs/{job_id}/certificates")
    cert_id = certs_resp.json()["certificates"][0]["id"]

    dl_resp = client.get(f"/certificates/{cert_id}/download")
    assert dl_resp.status_code == 409
    assert "download unavailable" in dl_resp.json()["detail"].lower()


def test_retrieval_409_conflict_job_zip_no_success(client):
    """
    Attempting to download ZIP when 0 certificates succeeded returns HTTP 409 Conflict.
    """
    payload = {
        "title": "Failed Operations",
        "issuer_name": "FailCorp",
        "recipients": [{"name": "Bad Recipient", "email": "invalid-email"}]
    }

    create_resp = client.post("/jobs", json=payload)
    job_id = create_resp.json()["id"]

    zip_resp = client.get(f"/jobs/{job_id}/download")
    assert zip_resp.status_code == 409
    assert "No ready certificates available" in zip_resp.json()["detail"]
