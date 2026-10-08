import os
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def generate_certificate_pdf(certificate_data: dict, output_path: str) -> str:
    """
    Generates a PDF certificate using ReportLab on a landscape A4 canvas.

    Parameters:
        certificate_data (dict): Dictionary containing:
            - recipient_name (str): Full name of the certificate recipient.
            - title (str): Course or event name.
            - issuer_name (str): Issuer or organization name.
            - issue_date (date|str): Date of issuance.
        output_path (str): Full target file path where the generated PDF will be saved.

    Returns:
        str: Absolute path to the generated PDF file.
        
    Note on Font & Non-ASCII Handling:
        Standard ReportLab built-in fonts (Helvetica) use WinAnsiEncoding (Latin-1).
        If non-Latin characters (e.g., Cyrillic, CJK) are passed without a custom TTF font registered,
        ReportLab will raise a UnicodeEncodeError. The background job processor catches all
        generation exceptions, recording a FAILED certificate status with the exact error message
        without stopping the rest of the batch.
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Landscape A4 dimensions: 841.89 x 595.27 points
    width, height = landscape(A4)
    c = canvas.Canvas(output_path, pagesize=landscape(A4))

    # ---------------------------------------------------------
    # 1. Decorative Borders & Accents
    # ---------------------------------------------------------
    # Outer dark blue border
    c.setStrokeColor(colors.HexColor("#1A365D"))
    c.setLineWidth(4)
    c.rect(20, 20, width - 40, height - 40)

    # Inner gold accent border
    c.setStrokeColor(colors.HexColor("#D69E2E"))
    c.setLineWidth(1.5)
    c.rect(28, 28, width - 56, height - 56)

    # Four Corner Accent Squares
    c.setFillColor(colors.HexColor("#1A365D"))
    c.rect(32, height - 42, 10, 10)
    c.rect(width - 42, height - 42, 10, 10)
    c.rect(32, 32, 10, 10)
    c.rect(width - 42, 32, 10, 10)

    # ---------------------------------------------------------
    # 2. Main Heading: Certificate of Completion
    # ---------------------------------------------------------
    c.setFillColor(colors.HexColor("#1A365D"))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(width / 2.0, height - 100, "CERTIFICATE OF COMPLETION")

    # Decorative Underline below Header
    c.setStrokeColor(colors.HexColor("#D69E2E"))
    c.setLineWidth(2)
    c.line(width / 2.0 - 140, height - 115, width / 2.0 + 140, height - 115)

    # ---------------------------------------------------------
    # 3. Subheading: "This is to certify that"
    # ---------------------------------------------------------
    c.setFillColor(colors.HexColor("#4A5568"))
    c.setFont("Helvetica", 15)
    c.drawCentredString(width / 2.0, height - 160, "This is to certify that")

    # ---------------------------------------------------------
    # 4. Recipient Name (with dynamic font sizing for long names)
    # ---------------------------------------------------------
    recipient_name = str(certificate_data.get("recipient_name", "")).strip()
    font_name = "Helvetica-Bold"
    start_font_size = 32
    max_text_width = width - 140  # Max printable width within margins

    current_font_size = start_font_size
    while current_font_size > 10:
        text_width = c.stringWidth(recipient_name, font_name, current_font_size)
        if text_width <= max_text_width:
            break
        current_font_size -= 2

    c.setFillColor(colors.HexColor("#2B6CB0"))
    c.setFont(font_name, current_font_size)
    c.drawCentredString(width / 2.0, height - 220, recipient_name)

    # Name Underline
    c.setStrokeColor(colors.HexColor("#CBD5E0"))
    c.setLineWidth(1)
    c.line(width / 2.0 - 180, height - 235, width / 2.0 + 180, height - 235)

    # ---------------------------------------------------------
    # 5. Body Text: "has successfully completed"
    # ---------------------------------------------------------
    c.setFillColor(colors.HexColor("#4A5568"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2.0, height - 275, "has successfully completed")

    # ---------------------------------------------------------
    # 6. Event / Course Title
    # ---------------------------------------------------------
    title = str(certificate_data.get("title", "")).strip()
    c.setFillColor(colors.HexColor("#1A365D"))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2.0, height - 325, title)

    # ---------------------------------------------------------
    # 7. Footer: Issue Date & Issuer Signature Line
    # ---------------------------------------------------------
    issue_date_val = certificate_data.get("issue_date")
    if isinstance(issue_date_val, (date, str)):
        date_str = str(issue_date_val)
    else:
        date_str = date.today().isoformat()

    issuer_name = str(certificate_data.get("issuer_name", "")).strip()

    # Left Side: Date Issued
    c.setStrokeColor(colors.HexColor("#718096"))
    c.setLineWidth(1)
    c.line(80, 115, 240, 115)
    c.setFillColor(colors.HexColor("#4A5568"))
    c.setFont("Helvetica", 11)
    c.drawString(80, 98, f"Date Issued: {date_str}")

    # Right Side: Authorized Signature & Issuer Name
    c.line(width - 240, 115, width - 80, 115)
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(width - 240, 122, "Authorized Signature")
    c.setFont("Helvetica", 11)
    c.drawString(width - 240, 98, f"Issuer: {issuer_name}")

    c.showPage()
    c.save()
    return os.path.abspath(output_path)
