import io
import os
import re
import zipfile
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.schemas import (
    CertificateListResponse,
    CertificateResponse,
    CreateJobRequest,
    JobDetailResponse,
    JobResponse,
)
from app.services.job_processor import process_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# Simple, standard regex for basic email format validation
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_recipient(recipient_name: str, recipient_email: str, seen_emails: set) -> tuple[bool, Optional[str]]:
    """
    Validates recipient-level attributes.
    Returns (is_valid, error_message).
    """
    clean_name = recipient_name.strip() if recipient_name else ""
    clean_email = recipient_email.strip().lower() if recipient_email else ""

    if not clean_name:
        return False, "Recipient name cannot be blank or whitespace."
    if len(clean_name) > 255:
        return False, "Recipient name exceeds maximum allowed length of 255 characters."
    if not clean_email or not EMAIL_REGEX.match(clean_email):
        return False, f"Invalid email format: '{recipient_email}'."
    if clean_email in seen_emails:
        return False, f"Duplicate email in request: '{recipient_email}'."

    seen_emails.add(clean_email)
    return True, None


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
def create_job(
    payload: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Submits a new bulk certificate generation job.
    
    Request-level issues (missing fields, empty list, >1000 items) trigger a 422 Unprocessable Entity.
    Recipient-level issues (blank name, invalid email, duplicate email) do NOT fail the job creation;
    instead, failed recipients are saved as FAILED Certificate rows with descriptive error messages.
    
    Valid recipients are saved as PENDING and queued for background generation.
    """
    job = Job(
        title=payload.title,
        issuer_name=payload.issuer_name,
        issue_date=payload.issue_date,
        status=JobStatus.PENDING,
        total_count=len(payload.recipients),
        success_count=0,
        failure_count=0,
    )
    db.add(job)
    db.flush()  # Generate job.id

    seen_emails = set()
    pre_failed_count = 0

    for r in payload.recipients:
        is_valid, err_msg = validate_recipient(r.name, r.email, seen_emails)

        if is_valid:
            cert = Certificate(
                job_id=job.id,
                recipient_name=r.name.strip(),
                recipient_email=r.email.strip(),
                status=CertificateStatus.PENDING,
            )
        else:
            cert = Certificate(
                job_id=job.id,
                recipient_name=r.name.strip() if r.name else "",
                recipient_email=r.email.strip() if r.email else "",
                status=CertificateStatus.FAILED,
                error_message=err_msg,
            )
            pre_failed_count += 1

        db.add(cert)

    job.failure_count = pre_failed_count
    db.commit()
    db.refresh(job)

    # Queue background task to process pending certificates
    background_tasks.add_task(process_job, job.id)

    return job


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Returns job status, total/success/failure counts, and overall progress percentage.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    processed_count = job.success_count + job.failure_count
    progress = round((processed_count / job.total_count) * 100.0, 2) if job.total_count > 0 else 100.0

    return JobDetailResponse(
        id=job.id,
        title=job.title,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        status=job.status.value if isinstance(job.status, JobStatus) else str(job.status),
        total_count=job.total_count,
        success_count=job.success_count,
        failure_count=job.failure_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        progress_percentage=progress,
    )


@router.get("/{job_id}/certificates", response_model=CertificateListResponse)
def list_job_certificates(
    job_id: str,
    status_filter: Optional[CertificateStatus] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Lists certificates for a job with pagination and optional status filtering.
    Successful certificates include a download_url.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    query = db.query(Certificate).filter(Certificate.job_id == job_id)
    if status_filter:
        query = query.filter(Certificate.status == status_filter)

    total_matching = query.count()
    certs = query.order_by(Certificate.created_at.asc()).offset(offset).limit(limit).all()

    items = []
    for cert in certs:
        status_str = cert.status.value if isinstance(cert.status, CertificateStatus) else str(cert.status)
        dl_url = f"/certificates/{cert.id}/download" if cert.status == CertificateStatus.SUCCESS else None

        items.append(
            CertificateResponse(
                id=cert.id,
                job_id=cert.job_id,
                recipient_name=cert.recipient_name,
                recipient_email=cert.recipient_email,
                status=status_str,
                file_path=cert.file_path,
                error_message=cert.error_message,
                download_url=dl_url,
                created_at=cert.created_at,
                updated_at=cert.updated_at,
            )
        )

    return CertificateListResponse(
        total=total_matching,
        limit=limit,
        offset=offset,
        certificates=items,
    )


@router.get("/{job_id}/download")
def download_job_zip(job_id: str, db: Session = Depends(get_db)):
    """
    Generates and returns a ZIP archive of all successfully generated certificates for the job.
    Returns 409 Conflict if no ready certificates are available.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    successful_certs = db.query(Certificate).filter(
        Certificate.job_id == job_id,
        Certificate.status == CertificateStatus.SUCCESS,
        Certificate.file_path.isnot(None)
    ).all()

    # Filter for files that actually exist on disk
    ready_files = [c for c in successful_certs if c.file_path and os.path.exists(c.file_path)]

    if not ready_files:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No ready certificates available for download in this job."
        )

    # Build ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for cert in ready_files:
            archive_name = f"{cert.id}.pdf"
            zf.write(cert.file_path, arcname=archive_name)

    zip_buffer.seek(0)
    zip_filename = f"job_{job_id}_certificates.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
