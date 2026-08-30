from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

CLAIMS = {
    "auto_claim_clean.pdf": """
    Claim ID: CLM-PDF-001
    Policy Number: POL-30011
    Claimant: Kavita Sharma
    Claim Type: auto
    Date of Incident: 2026-08-15
    Amount Claimed: $650.00
    Description: Side mirror snapped off when clipped by another vehicle while parked on the street.
    Contact: kavita.sharma@example.com
    """,
    "auto_claim_glass_damage.pdf": """
    Claim ID: CLM-PDF-002
    Policy Number: POL-88213
    Claimant: Anita Rao
    Claim Type: auto
    Date of Incident: 2026-07-14
    Amount Claimed: $2,340.50
    Description: Rear windshield shattered by a fallen tree branch during a storm.
    Contact: anita.rao@example.com
    """,
    "home_claim_storm.pdf": """
    Claim ID: CLM-PDF-003
    Policy Number: POL-30045
    Claimant: Sara Thomas
    Claim Type: home
    Date of Incident: 2026-08-10
    Amount Claimed: $3,200.00
    Description: Hailstorm damaged roof shingles on the south side of the house.
    Contact: sara.thomas@example.com
    """,
}


def build_pdf(text: str, out_path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for line in text.strip().splitlines():
        line = line.strip()
        if line:
            pdf.multi_cell(0, 8, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            pdf.ln(4)
    pdf.output(str(out_path))


def main() -> None:
    out_dir = Path(__file__).parent / "sample_claims"
    out_dir.mkdir(exist_ok=True)
    for filename, text in CLAIMS.items():
        build_pdf(text, out_dir / filename)
        print(f"wrote {out_dir / filename}")


if __name__ == "__main__":
    main()
