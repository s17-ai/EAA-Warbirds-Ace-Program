import base64
from pathlib import Path
import fitz

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PDF = BASE_DIR / "static" / "forms" / "woa-sac-blank.pdf"

def clean(value, limit=300):
    value = "" if value is None else str(value)
    return " ".join(value.replace("\x00", "").split())[:limit]


def decode_signature(data_url):
    if not data_url or "," not in data_url:
        return None
    header, encoded = data_url.split(",", 1)
    if "image/png" not in header:
        return None
    raw = base64.b64decode(encoded)
    if len(raw) > 1_000_000:
        raise ValueError("Signature image is too large")
    return raw


def draw_text(page, text, x, y, size=8.4, max_width=None, font="helv", color=(0, 0, 0)):
    text = clean(text, 600)
    if not text:
        return
    if max_width:
        page.insert_textbox(fitz.Rect(x, y, x + max_width, y + size * 2.6), text,
                            fontsize=size, fontname=font, color=color, align=0, overlay=True)
    else:
        page.insert_text(fitz.Point(x, y), text, fontsize=size, fontname=font, color=color, overlay=True)


def draw_check(page, x, y, checked):
    if checked:
        page.insert_text(fitz.Point(x, y), "X", fontsize=10, fontname="helv", color=(0, 0, 0), overlay=True)


def draw_multiline(page, text, rect, size=7.5):
    text = clean(text, 900)
    if text:
        page.insert_textbox(fitz.Rect(*rect), text, fontsize=size, fontname="helv", color=(0, 0, 0), overlay=True)


def insert_signature(page, sig_bytes, rect):
    if not sig_bytes:
        return
    page.insert_image(fitz.Rect(*rect), stream=sig_bytes, keep_proportion=True, overlay=True)


def generate_pdf(data, application_id="PREVIEW"):
    doc = fitz.open(TEMPLATE_PDF)
    p1, p2, p3 = doc[0], doc[1], doc[2]

    # PAGE 1 - Part I / applicant section
    app_types = {
        "new_issue": (224, 84),
        "change": (284, 84),
        "renewal": (395, 84),
        "reevaluation": (502, 84),
    }
    if data.get("application_type") in app_types:
        draw_check(p1, *app_types[data["application_type"]], True)

    draw_text(p1, data.get("applicant_name"), 78, 113, 8.6)
    draw_text(p1, data.get("email"), 111, 127, 8.2)
    draw_text(p1, data.get("warbird_number"), 83, 141, 8.2)
    draw_text(p1, data.get("dob"), 215, 141, 8.2)
    draw_multiline(p1, data.get("address"), (84, 146, 304, 168), 8.0)
    draw_text(p1, data.get("phone"), 78, 181, 8.2)
    draw_text(p1, data.get("fsdo"), 161, 196, 8.2)
    draw_text(p1, data.get("pilot_certificate"), 103, 210, 8.2)
    draw_text(p1, data.get("certificate_type"), 219, 210, 8.2)
    draw_text(p1, data.get("ratings"), 83, 224, 8.0)
    draw_text(p1, data.get("medical_date"), 112, 251, 8.0)
    draw_text(p1, data.get("medical_type"), 218, 251, 8.0)
    draw_text(p1, data.get("flight_review_date"), 126, 266, 8.0)

    # Experience rows (7 rows)
    row_y = [176, 191, 206, 221, 236, 251, 266]
    exp = data.get("experience", [])[:7]
    for i, row in enumerate(exp):
        y = row_y[i]
        draw_text(p1, row.get("site"), 314, y, 7.3)
        draw_text(p1, row.get("date"), 451, y, 7.3)
        draw_check(p1, 501, y + 1, row.get("show"))
        draw_check(p1, 536, y + 1, row.get("practice"))

    levels = {"250": (151, 338), "500": (194, 338), "800": (248, 338)}
    if data.get("requested_level") in levels:
        draw_check(p1, *levels[data["requested_level"]], True)

    applicant_sig = decode_signature(data.get("applicant_signature"))
    evaluator_sig = decode_signature(data.get("evaluator_signature"))
    insert_signature(p1, applicant_sig, (156, 357, 390, 374))
    draw_text(p1, data.get("applicant_signature_date") or data.get("evaluation_date"), 432, 371, 8.2)

    # PAGE 1 - Part II evaluation
    draw_multiline(p1, data.get("ground_notes"), (319, 402, 567, 432), 7.0)
    draw_multiline(p1, data.get("air_notes"), (146, 436, 567, 466), 7.0)
    draw_text(p1, data.get("evaluation_location"), 171, 474, 8.0)
    draw_text(p1, data.get("evaluation_date"), 472, 474, 8.0)

    draw_check(p1, 55, 510, data.get("limitation_dogfight"))
    draw_check(p1, 142, 510, data.get("limitation_rolls"))
    draw_check(p1, 224, 510, data.get("limitation_loops_rolls"))
    draw_check(p1, 149, 531, data.get("altitude_250"))
    draw_check(p1, 202, 531, data.get("altitude_500"))
    draw_check(p1, 254, 531, data.get("altitude_800"))
    draw_text(p1, data.get("show_line_category"), 360, 531, 8.0)
    draw_text(p1, data.get("approved_aircraft"), 112, 555, 8.0)

    # PAGE 1 - Part III evaluator
    draw_text(p1, data.get("evaluator_name"), 173, 596, 8.2)
    insert_signature(p1, evaluator_sig, (150, 619, 385, 638))
    draw_text(p1, data.get("evaluation_date"), 473, 634, 8.0)
    draw_text(p1, data.get("aircraft_flown"), 126, 657, 8.0)
    draw_multiline(p1, data.get("remarks"), (83, 715, 557, 760), 7.5)

    # PAGE 2 - applicant initials / date
    draw_text(p2, data.get("applicant_initials"), 414, 739, 9.0)
    draw_text(p2, data.get("applicant_signature_date") or data.get("evaluation_date"), 511, 739, 8.2)

    # PAGE 3 - applicant final signature / date
    insert_signature(p3, applicant_sig, (337, 683, 493, 704))
    draw_text(p3, data.get("applicant_signature_date") or data.get("evaluation_date"), 516, 702, 8.2)

    # Tiny traceability mark in margin - does not alter official form fields.
    draw_text(p3, f"ACE web ref: {application_id}", 42, 781, 5.3, color=(0.35, 0.35, 0.35))

    output = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return output

