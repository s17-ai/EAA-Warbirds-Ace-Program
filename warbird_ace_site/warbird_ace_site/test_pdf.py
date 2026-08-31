from pathlib import Path
from pdf_service import generate_pdf

sample = {
    "application_type":"new_issue","applicant_name":"TEST PILOT","email":"pilot@example.com","warbird_number":"12345","dob":"1980-01-01",
    "address":"123 Aviation Way, Oshkosh, WI 54902","phone":"555-0100","fsdo":"Milwaukee","pilot_certificate":"1234567","certificate_type":"ATP",
    "ratings":"ASEL, AMEL","medical_date":"2026-07-01","medical_type":"First","flight_review_date":"2026-06-01","requested_level":"500",
    "experience":[{"site":"Practice Site","date":"2026-08-20","show":False,"practice":True}],
    "ground_notes":"Satisfactory ground evaluation.","air_notes":"Satisfactory air evaluation.","evaluation_location":"KOSH","evaluation_date":"2026-08-31",
    "limitation_dogfight":False,"limitation_rolls":False,"limitation_loops_rolls":True,"altitude_250":False,"altitude_500":True,"altitude_800":False,
    "show_line_category":"Category I","approved_aircraft":"T-28","evaluator_name":"TEST EVALUATOR","aircraft_flown":"T-28","remarks":"Prototype coordinate check.",
    "applicant_initials":"TP","applicant_signature_date":"2026-08-31","applicant_signature":"","evaluator_signature":"","certify_complete":True
}
Path("sample-output.pdf").write_bytes(generate_pdf(sample,"TEST-REF"))
print("Wrote sample-output.pdf")
