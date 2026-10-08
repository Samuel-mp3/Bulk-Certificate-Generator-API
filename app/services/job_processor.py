import os
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.services.certificate_generator import generate_certificate_pdf


def process_job(job_id: str, generator_func=generate_certificate_pdf):
    """
    Background worker task to process PDF certificate generation for a job.
    
    Opens its own dedicated database session (SessionLocal) to avoid thread-safety
    or lifecycle issues with the HTTP request database session.
    
    Commit strategy:
    - Commits job status change to PROCESSING.
    - Commits after EACH individual certificate generation attempt so that external
      polling clients can monitor progress in real-time.
    - Commits final job status (COMPLETED, COMPLETED_WITH_ERRORS, or FAILED).
    """
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        # Do not re-process jobs that are already processing, completed, or failed
        if job.status != JobStatus.PENDING:
            return

        # Update job status to PROCESSING
        job.status = JobStatus.PROCESSING
        db.commit()

        # Retrieve all pending certificates for this job
        pending_certs = db.query(Certificate).filter(
            Certificate.job_id == job_id,
            Certificate.status == CertificateStatus.PENDING
        ).all()

        for cert in pending_certs:
            cert_data = {
                "recipient_name": cert.recipient_name,
                "recipient_email": cert.recipient_email,
                "title": job.title,
                "issuer_name": job.issuer_name,
                "issue_date": job.issue_date
            }

            # File names use certificate UUID to prevent collisions and illegal filesystem chars
            filename = f"{cert.id}.pdf"
            output_path = os.path.abspath(os.path.join(settings.CERTIFICATES_DIR, filename))

            try:
                # Execute generator function (injectable/monkeypatchable for tests)
                generated_file = generator_func(cert_data, output_path)
                cert.status = CertificateStatus.SUCCESS
                cert.file_path = generated_file
                cert.error_message = None
                job.success_count += 1
            except Exception as e:
                # Per-certificate error isolation: failure on one certificate does not stop others
                cert.status = CertificateStatus.FAILED
                cert.file_path = None
                cert.error_message = str(e)
                job.failure_count += 1

            # Commit per certificate to support granular real-time progress polling
            db.commit()

        # Refresh job state and compute final status
        db.refresh(job)
        if job.success_count == job.total_count:
            job.status = JobStatus.COMPLETED
        elif job.success_count > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS
        else:
            job.status = JobStatus.FAILED

        db.commit()
    finally:
        db.close()
