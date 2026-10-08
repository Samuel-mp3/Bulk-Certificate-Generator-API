from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipientInput(BaseModel):
    name: str = Field(..., description="Full name of the recipient")
    email: str = Field(..., description="Email address of the recipient")


class CreateJobRequest(BaseModel):
    title: str = Field(..., description="Title of the course or event")
    issuer_name: str = Field(..., description="Name of the issuing organization")
    issue_date: Optional[date] = Field(default_factory=date.today, description="Certificate issuance date")
    recipients: List[RecipientInput] = Field(..., description="List of recipient objects")

    @field_validator("title", "issuer_name")
    @classmethod
    def validate_non_empty_str(cls, value: str, info) -> str:
        if not value or not value.strip():
            raise ValueError(f"'{info.field_name}' cannot be empty or whitespace")
        return value.strip()

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, value: List[RecipientInput]) -> List[RecipientInput]:
        if not value or len(value) == 0:
            raise ValueError("Recipients list cannot be empty")
        if len(value) > 1000:
            raise ValueError("Recipients list cannot exceed 1000 items")
        return value


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    issuer_name: str
    issue_date: date
    status: str
    total_count: int
    success_count: int
    failure_count: int
    created_at: datetime
    updated_at: datetime


class JobDetailResponse(JobResponse):
    progress_percentage: float


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    status: str
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CertificateListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    certificates: List[CertificateResponse]
