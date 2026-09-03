"""Small local PDF-generation smoke test for the current fillable SAC template."""
from pdf_service import generate_pdf

sample = {
    "application_type": "new_issue",
    "applicant_name": "Test Pilot",
    "warbird_number": "1234",
    "address": "123 Aviation Way\nAiken, SC 29801",
    "pilot_certificate": "1234567",
    "requested_level": "500",
    "evaluation_date": "2026-09-03",
    "limitation_dogfight": False,
    "limitation_loops_rolls": True,
    "altitude_250": False,
    "altitude_500": True,
    "evaluator_name": "Test Evaluator",
    "aircraft_flown": "T-28",
    "applicant_initials": "TP",
}

if __name__ == "__main__":
    with open("sample-sac.pdf", "wb") as f:
        f.write(generate_pdf(sample, "LOCAL-TEST"))
    print("Wrote sample-sac.pdf")
