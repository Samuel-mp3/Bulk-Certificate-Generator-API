import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, CertificateStatus

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("/{certificate_id}/download")
def download_certificate_pdf(certificate_id: str, db: Session = Depends(get_db)):
    """
    Streams the generated PDF certificate for a recipient.
    
    Returns 404 if the certificate ID is not found.
    Returns 409 Conflict if the certificate is not ready, has failed, or its file does not exist.
    """
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found."
        )

    status_str = cert.status.value if isinstance(cert.status, CertificateStatus) else str(cert.status)
    if status_str != CertificateStatus.SUCCESS.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificate download unavailable. Current status is '{status_str}'."
        )

    if not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate PDF file is missing or has not been generated."
        )

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=f"{cert.id}.pdf"
    )
