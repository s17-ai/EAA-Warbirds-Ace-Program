import base64
import io
import textwrap
from datetime import datetime
from pathlib import Path

import fitz
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PDF = BASE_DIR / "static" / "forms" / "woa-sac-blank.pdf"


def clean(value, limit=500):
    value = "" if value is None else str(value)
    return " ".join(value.replace("\x00", "").split())[:limit]


def format_date(value):
    value = clean(value, 30)
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return f"{dt.month}/{dt.day}/{dt.strftime('%y')}"
    except ValueError:
        return value


def split_lines(value, count=2, width=42):
    raw = "" if value is None else str(value).replace("\r", "")
    pieces = []
    for part in raw.split("\n"):
        part = " ".join(part.split())
        if not part:
            continue
        pieces.extend(textwrap.wrap(part, width=width, break_long_words=False, break_on_hyphens=False) or [part])
    pieces = pieces[:count]
    while len(pieces) < count:
        pieces.append("")
    return pieces


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


def crop_signature(sig_bytes):
    """Trim the blank canvas around a captured signature while retaining a small margin."""
    if not sig_bytes:
        return None
    image = Image.open(io.BytesIO(sig_bytes)).convert("RGBA")
    # Browser signature pads are transparent or white with dark ink.
    alpha = image.getchannel("A")
    if alpha.getbbox():
        bbox = alpha.getbbox()
    else:
        bbox = None
    # If canvas is fully opaque, calculate a bbox from non-white pixels.
    if bbox == (0, 0, image.width, image.height):
        gray = image.convert("L")
        mask = gray.point(lambda px: 255 if px < 245 else 0)
        bbox = mask.getbbox()
    if not bbox:
        return sig_bytes
    left, top, right, bottom = bbox
    margin = 8
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(image.width, right + margin)
    bottom = min(image.height, bottom + margin)
    image = image.crop((left, top, right, bottom))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def find_widget(doc, field_name):
    for page_number, page in enumerate(doc):
        for widget in list(page.widgets() or []):
            if widget.field_name == field_name:
                return page_number, page, widget
    return None


def set_text(doc, field_name, value):
    """Flatten one user-entered text field into the page while leaving EAA office fields untouched."""
    text = clean(value, 1000)
    item = find_widget(doc, field_name)
    if not item:
        return
    _, page, widget = item
    rect = fitz.Rect(widget.rect)
    base_size = widget.text_fontsize or 8.5
    flags = widget.field_flags or 0
    page.delete_widget(widget)
    if not text:
        return

    max_width = max(12, rect.width - 3)
    fontsize = min(base_size, max(5.5, rect.height * 0.72))
    while fontsize > 5.5 and fitz.get_text_length(text, fontname="helv", fontsize=fontsize) > max_width:
        fontsize -= 0.25

    # PDF text fields on this form sit directly over printed answer lines.
    # Small field-specific nudges compensate for the source PDF's annotation rectangles.
    y_nudge = {
        "location_of_flight_evaluation": -5.5,
        "date_of_flight_evaluation": -5.5,
        "waiver_initials": -3.0,
        "waiver_initials_date": -3.0,
    }.get(field_name, 0.0)

    if field_name == "remarks":
        page.insert_textbox(
            fitz.Rect(rect.x0 + 40, rect.y0 + 2, rect.x1 - 1, rect.y1 - 1),
            text, fontsize=fontsize, fontname="helv", color=(0, 0, 0), overlay=True,
        )
    elif flags & 4096:  # multiline field
        page.insert_textbox(
            fitz.Rect(rect.x0 + 1, rect.y0 + 1, rect.x1 - 1, rect.y1 - 1),
            text, fontsize=fontsize, fontname="helv", color=(0, 0, 0), overlay=True,
        )
    else:
        baseline = rect.y0 + fontsize * 0.78 + y_nudge
        page.insert_text(
            fitz.Point(rect.x0 + 1, baseline), text, fontsize=fontsize,
            fontname="helv", color=(0, 0, 0), overlay=True,
        )


def set_checkbox(doc, field_name, checked):
    item = find_widget(doc, field_name)
    if not item:
        return
    _, page, widget = item
    widget.field_value = "Yes" if bool(checked) else "Off"
    widget.update()




def split_for_fields(doc, value, field_names):
    """Split text across the named single-line form fields using each field's actual width/font size."""
    words = clean(value, 1200).split()
    lines = []
    pos = 0
    for field_name in field_names:
        item = find_widget(doc, field_name)
        if not item or pos >= len(words):
            lines.append("")
            continue
        _, page, widget = item
        max_width = max(10, widget.rect.width - 6)
        fontsize = widget.text_fontsize or 8.5
        chosen = []
        while pos < len(words):
            candidate = " ".join(chosen + [words[pos]])
            if chosen and fitz.get_text_length(candidate, fontname="helv", fontsize=fontsize) > max_width:
                break
            # Always consume at least one word, even if unusually long.
            chosen.append(words[pos])
            pos += 1
            if fitz.get_text_length(" ".join(chosen), fontname="helv", fontsize=fontsize) > max_width:
                break
        lines.append(" ".join(chosen))
    return lines

def insert_signature(doc, field_name, sig_bytes):
    item = find_widget(doc, field_name)
    if not item or not sig_bytes:
        return
    page_number, page, widget = item
    rect = fitz.Rect(widget.rect)
    # Remove the editable signature text field so the captured image cannot be overwritten accidentally.
    page.delete_widget(widget)
    sig_bytes = crop_signature(sig_bytes)
    inset = fitz.Rect(rect.x0 + 2, rect.y0 + 1, rect.x1 - 2, rect.y1 - 1)
    page.insert_image(inset, stream=sig_bytes, keep_proportion=True, overlay=True)

def generate_pdf(data, application_id="PREVIEW"):
    doc = fitz.open(TEMPLATE_PDF)
    # Application type.
    app_type_map = {
        "new_issue": "application_new_issue",
        "change": "application_change",
        "renewal": "application_renewal_no_change",
        "reevaluation": "application_reevaluation",
    }
    selected_type = data.get("application_type")
    for key, field in app_type_map.items():
        set_checkbox(doc, field, selected_type == key)

    # Applicant information.
    set_text(doc, "applicant_name", data.get("applicant_name"))
    set_text(doc, "email_address", data.get("email"))
    set_text(doc, "warbirds_number", data.get("warbird_number"))
    set_text(doc, "date_of_birth", format_date(data.get("dob")))

    address_1, address_2 = split_for_fields(doc, data.get("address"), ["address_line_1", "address_line_2"])
    set_text(doc, "address_line_1", address_1)
    set_text(doc, "address_line_2", address_2)
    set_text(doc, "phone", data.get("phone"))
    set_text(doc, "fsdo_office_city", data.get("fsdo"))
    set_text(doc, "pilot_certificate_number", data.get("pilot_certificate"))
    set_text(doc, "pilot_certificate_type", data.get("certificate_type"))

    ratings_1, ratings_2 = split_for_fields(doc, data.get("ratings"), ["ratings_line_1", "ratings_line_2"])
    set_text(doc, "ratings_line_1", ratings_1)
    set_text(doc, "ratings_line_2", ratings_2)
    set_text(doc, "medical_date", format_date(data.get("medical_date")))
    set_text(doc, "medical_type", data.get("medical_type"))
    set_text(doc, "date_last_bfr", format_date(data.get("flight_review_date")))

    # Renewal/show-practice experience - revised form contains eight rows.
    experience = data.get("experience", [])[:8]
    for i in range(1, 9):
        row = experience[i - 1] if i <= len(experience) else {}
        prefix = f"experience_{i}"
        set_text(doc, f"{prefix}_show_name_or_practice_site", row.get("site"))
        set_text(doc, f"{prefix}_date", format_date(row.get("date")))
        set_checkbox(doc, f"{prefix}_show", row.get("show"))
        set_checkbox(doc, f"{prefix}_practice", row.get("practice"))

    # Requested level - current form only contains 250 and 500 feet.
    requested_level = str(data.get("requested_level") or "")
    set_checkbox(doc, "level_250_feet", requested_level == "250")
    set_checkbox(doc, "level_500_feet", requested_level == "500")

    applicant_date = format_date(data.get("applicant_signature_date") or data.get("evaluation_date"))
    set_text(doc, "page1_applicant_date", applicant_date)

    # Part II evaluation.
    ground_1, ground_2 = split_for_fields(doc, data.get("ground_notes"), ["ground_evaluation_notes_line_1", "ground_evaluation_notes_line_2"])
    air_1, air_2 = split_for_fields(doc, data.get("air_notes"), ["air_evaluation_notes_line_1", "air_evaluation_notes_line_2"])
    set_text(doc, "ground_evaluation_notes_line_1", ground_1)
    set_text(doc, "ground_evaluation_notes_line_2", ground_2)
    set_text(doc, "air_evaluation_notes_line_1", air_1)
    set_text(doc, "air_evaluation_notes_line_2", air_2)
    set_text(doc, "location_of_flight_evaluation", data.get("evaluation_location"))
    set_text(doc, "date_of_flight_evaluation", format_date(data.get("evaluation_date")))

    # Current limitations: Rolls Only and all 800-foot selections were removed from the revised form.
    set_checkbox(doc, "limitation_dogfight", data.get("limitation_dogfight"))
    set_checkbox(doc, "limitation_combination_loops_rolls", data.get("limitation_loops_rolls"))
    set_checkbox(doc, "altitude_restriction_250", data.get("altitude_250"))
    set_checkbox(doc, "altitude_restriction_500", data.get("altitude_500"))
    set_text(doc, "show_line_category", data.get("show_line_category"))
    set_text(doc, "approved_aircraft", data.get("approved_aircraft"))

    # Part III evaluator.
    set_text(doc, "warbird_evaluator_name", data.get("evaluator_name"))
    set_text(doc, "date_of_evaluation", format_date(data.get("evaluation_date")))
    set_text(doc, "aircraft_flown", data.get("aircraft_flown"))
    set_text(doc, "remarks", data.get("remarks"))

    # Waiver / applicant acknowledgement.
    set_text(doc, "waiver_initials", data.get("applicant_initials"))
    set_text(doc, "waiver_initials_date", applicant_date)
    set_text(doc, "final_signature_date", applicant_date)

    # Office-use fields intentionally remain blank and fillable for EAA.

    # Capture signatures as images in the three existing signature locations.
    applicant_sig = decode_signature(data.get("applicant_signature"))
    evaluator_sig = decode_signature(data.get("evaluator_signature"))
    insert_signature(doc, "page1_applicant_signature", applicant_sig)
    insert_signature(doc, "evaluator_signature", evaluator_sig)
    insert_signature(doc, "final_applicant_signature", applicant_sig)

    # Keep the remaining AcroForm fields editable so EAA can complete its office-use areas.
    output = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return output
