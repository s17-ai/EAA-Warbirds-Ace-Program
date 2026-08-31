import base64
import io
import json
import os
import smtplib
import ssl
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

BASE_DIR = Path(__file__).resolve().parent
EVALUATORS_JSON = BASE_DIR / "static" / "data" / "evaluators.json"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

RATE_LOG = defaultdict(deque)


def env_bool(name: str, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def load_evaluators():
    try:
        return json.loads(EVALUATORS_JSON.read_text())
    except Exception:
        return []


def check_rate_limit(ip):
    limit = int(os.getenv("MAX_SUBMISSIONS_PER_HOUR", "5"))
    now = time.time()
    q = RATE_LOG[ip]
    while q and q[0] < now - 3600:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def require_fields(data):
    required = {
        "applicant_name": "Applicant name",
        "warbird_number": "Warbirds number",
        "address": "Address",
        "pilot_certificate": "Pilot certificate number",
        "application_type": "Application type",
        "evaluator_name": "Warbird evaluator name",
        "evaluation_date": "Evaluation date",
        "aircraft_flown": "Aircraft flown",
        "applicant_initials": "Applicant initials",
        "applicant_signature": "Applicant signature",
        "evaluator_signature": "Evaluator signature",
    }
    missing = [label for key, label in required.items() if not data.get(key)]
    if not data.get("certify_complete"):
        missing.append("Final certification checkbox")
    return missing


from pdf_service import clean, generate_pdf

def send_to_chairman(pdf_bytes, data, application_id):
    chairman = os.getenv("CHAIRMAN_EMAIL", "kschaick@eaa.org").strip()
    if not chairman or chairman.endswith("@example.com"):
        if env_bool("ALLOW_DEV_OUTBOX", False):
            out = BASE_DIR / "dev_outbox" / f"{application_id}.pdf"
            out.write_bytes(pdf_bytes)
            return {"mode": "dev_outbox", "path": str(out)}
        raise RuntimeError("CHAIRMAN_EMAIL is not configured")

    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = env_bool("SMTP_USE_TLS", True)
    use_ssl = env_bool("SMTP_USE_SSL", False)
    if not all([host, sender]):
        raise RuntimeError("SMTP settings are not configured")

    pilot = clean(data.get("applicant_name"), 100)
    aircraft = clean(data.get("aircraft_flown"), 80)
    eval_date = clean(data.get("evaluation_date"), 30)
    evaluator = clean(data.get("evaluator_name"), 100)

    msg = EmailMessage()
    msg["To"] = chairman
    msg["From"] = sender
    msg["Subject"] = f"Warbirds SAC Application - {pilot} - {aircraft}"
    msg.set_content(
        "A completed EAA Warbirds of America Statement of Aerobatic Competency application has been submitted.\n\n"
        f"Applicant: {pilot}\n"
        f"Evaluator: {evaluator}\n"
        f"Aircraft: {aircraft}\n"
        f"Evaluation Date: {eval_date}\n"
        f"Submission Reference: {application_id}\n\n"
        "The completed three-page application is attached as a PDF."
    )
    safe_name = "_".join(pilot.split()) or "Applicant"
    filename = f"WOA_SAC_{safe_name}_{eval_date or 'undated'}.pdf".replace("/", "-")
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

    context = ssl.create_default_context()
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            if username:
                server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            if use_tls:
                server.starttls(context=context)
                server.ehlo()
            if username:
                server.login(username, password)
            server.send_message(msg)
    return {"mode": "smtp"}


@app.route("/")
def index():
    return render_template("index.html", active="home")


@app.route("/about")
def about():
    return render_template("about.html", active="about")


@app.route("/evaluators")
def evaluators():
    return render_template("evaluators.html", active="evaluators", evaluators=load_evaluators())


@app.get("/official-sac-form")
def official_sac_form():
    return send_file(
        BASE_DIR / "static" / "forms" / "woa-sac-blank.pdf",
        mimetype="application/pdf",
        as_attachment=False,
        download_name="EAA-Warbirds-SAC-Application.pdf",
    )


@app.route("/application")
def application_page():
    return render_template("application.html", active="application")


@app.post("/api/preview")
def preview_api():
    data = request.get_json(silent=True) or {}
    if data.get("website"):
        return jsonify({"error": "Invalid submission"}), 400
    try:
        pdf = generate_pdf(data, "PREVIEW")
    except Exception as exc:
        return jsonify({"error": f"Could not generate preview: {exc}"}), 400
    return jsonify({"pdf_base64": base64.b64encode(pdf).decode("ascii")})


@app.post("/api/submit")
def submit_api():
    data = request.get_json(silent=True) or {}
    if data.get("website"):
        return jsonify({"error": "Invalid submission"}), 400
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not check_rate_limit(ip):
        return jsonify({"error": "Submission limit reached. Please try again later."}), 429

    missing = require_fields(data)
    if missing:
        return jsonify({"error": "Please complete: " + ", ".join(missing)}), 400

    application_id = "WOA-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
    try:
        pdf = generate_pdf(data, application_id)
        send_to_chairman(pdf, data, application_id)
    except Exception as exc:
        app.logger.exception("Submission failed")
        return jsonify({"error": f"The application was not sent. {exc}"}), 500

    return jsonify({
        "ok": True,
        "application_id": application_id,
        "pdf_base64": base64.b64encode(pdf).decode("ascii"),
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
