import os
from datetime import date
from app.services.certificate_generator import generate_certificate_pdf


def test_pdf_generation(tmp_path):
    """
    Directly tests PDF generation via ReportLab to ensure file is created,
    is non-empty, and starts with valid %PDF header.
    """
    output_path = os.path.join(tmp_path, "test_cert.pdf")
    data = {
        "recipient_name": "Jane Doe",
        "title": "Advanced Microservices Architecture with Python FastAPI",
        "issuer_name": "Google DeepMind Academy",
        "issue_date": date(2026, 10, 8),
    }

    result_path = generate_certificate_pdf(data, output_path)

    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 0

    with open(result_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"


def test_pdf_generation_long_name(tmp_path):
    """
    Tests font scaling for exceptionally long recipient names to avoid overflow/exceptions.
    """
    output_path = os.path.join(tmp_path, "long_name_cert.pdf")
    data = {
        "recipient_name": "Dr. Bartholomew Alexander Montgomery-Wellington the Third, Esq.",
        "title": "Quantum Computing Essentials",
        "issuer_name": "Institute of Technology",
        "issue_date": "2026-10-08",
    }

    result_path = generate_certificate_pdf(data, output_path)

    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 0
    with open(result_path, "rb") as f:
        assert f.read(4) == b"%PDF"
