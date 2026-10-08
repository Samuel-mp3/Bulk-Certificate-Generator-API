from app.services.job_processor import process_job


def test_individual_generation_failure_does_not_stop_others(client, db_session):
    """
    Monkeypatches generator function to raise an exception for a specific recipient name.
    Verifies that:
    1. Other recipients in the same job still succeed.
    2. The failed certificate records FAILED status with error_message.
    3. The job ends in COMPLETED_WITH_ERRORS.
    """
    def mock_generator(cert_data, output_path):
        if cert_data["recipient_name"] == "Failing Recipient":
            raise RuntimeError("Simulated PDF generation crash for testing")
        # For valid ones, generate standard PDF
        from app.services.certificate_generator import generate_certificate_pdf
        return generate_certificate_pdf(cert_data, output_path)

    payload = {
        "title": "Robust System Design",
        "issuer_name": "Resilience Tech",
        "recipients": [
            {"name": "Good Recipient 1", "email": "good1@example.com"},
            {"name": "Failing Recipient", "email": "fail@example.com"},
            {"name": "Good Recipient 2", "email": "good2@example.com"},
        ]
    }

    # Submit job request
    response = client.post("/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    # Re-run process_job directly using the monkeypatched generator
    # First reset job status to PENDING and cert statuses to PENDING for process_job run
    from app.models import Job, Certificate, JobStatus, CertificateStatus
    job = db_session.query(Job).filter(Job.id == job_id).first()
    job.status = JobStatus.PENDING
    job.success_count = 0
    job.failure_count = 0
    for cert in job.certificates:
        cert.status = CertificateStatus.PENDING
        cert.error_message = None
        cert.file_path = None
    db_session.commit()

    # Call process_job with mock_generator
    process_job(job_id, generator_func=mock_generator)

    # Check job status
    status_resp = client.get(f"/jobs/{job_id}")
    assert status_resp.status_code == 200
    job_data = status_resp.json()

    assert job_data["status"] == "COMPLETED_WITH_ERRORS"
    assert job_data["total_count"] == 3
    assert job_data["success_count"] == 2
    assert job_data["failure_count"] == 1

    # Check certificate status
    certs_resp = client.get(f"/jobs/{job_id}/certificates")
    assert certs_resp.status_code == 200
    certs = certs_resp.json()["certificates"]

    by_email = {c["recipient_email"]: c for c in certs}
    assert by_email["good1@example.com"]["status"] == "SUCCESS"
    assert by_email["good2@example.com"]["status"] == "SUCCESS"

    failed_cert = by_email["fail@example.com"]
    assert failed_cert["status"] == "FAILED"
    assert "Simulated PDF generation crash" in failed_cert["error_message"]
