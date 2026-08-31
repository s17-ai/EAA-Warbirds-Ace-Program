# EAA Warbirds of America ACE Program - working prototype

This is a lean, evaluator-driven prototype for `www.eaawarbirdace.com`.

## What is implemented

- Home, About, Find an ACE, and SAC Application pages.
- Conservative Warbirds/flight-standards visual identity.
- Public access: no login and no saved drafts.
- Responsive digital version of the existing three-page SAC application.
- Seven renewal show/practice rows.
- Applicant and evaluator signature capture on touch, mouse, or stylus.
- Source waiver pages shown as images so the legal wording is not silently rewritten.
- PDF preview before submission.
- Server-side PDF generation based on the supplied EAA-Warbird form.
- Fixed chairman recipient configured only on the server through `CHAIRMAN_EMAIL` (`kschaick@eaa.org`).
- SMTP email with the completed PDF attached.
- Evaluator gets an on-screen confirmation and optional PDF download; no copy is emailed to the evaluator.
- No application database. No unfinished form is persisted.
- Basic public-form protections: honeypot, request-size limit, and per-IP rate limit.

## Important setup items before production

1. The sole chairman recipient is configured as `kschaick@eaa.org` through the server-side `CHAIRMAN_EMAIL` setting.
2. Configure an SMTP provider in the environment variables. The site will not pretend to send an application if mail is not configured.
3. Populate `static/data/evaluators.json` with the current ACE roster. An example schema is in `evaluators.example.json`.
4. Verify every PDF overlay coordinate against the committee's preferred blank master before launch. The supplied source PDF contained a pre-marked 500-foot box and a handwritten evaluator signature, so this prototype creates a cleaned working master from it.
5. Confirm acceptance of electronically captured signatures for this workflow.
6. Confirm authorization/usage requirements for EAA/Warbirds marks on an independent domain.

## Warbirds logo

The header references the official Warbirds of America high-resolution PNG published on EAA's Verified EAA Logos page rather than recreating or modifying the mark. For production, download and self-host the approved asset if EAA's branding policy permits it.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env              # or export the variables in your shell
export ALLOW_DEV_OUTBOX=true       # LOCAL TESTING ONLY
python app.py
```

Open `http://127.0.0.1:5000`.

Note: Flask does not automatically read `.env` without an additional package. For production, configure environment variables in the hosting provider. For local testing, export them in the shell or add your preferred dotenv loader.

## Production deployment

The app is compatible with ordinary Python hosting. A typical command is:

```bash
gunicorn -w 2 -b 0.0.0.0:$PORT app:app
```

Put the site behind HTTPS and a reverse proxy/CDN. Cloudflare Turnstile can be added later if bot traffic becomes an issue.

## Privacy model

The server generates the final PDF in memory and sends it directly to the fixed chairman email. This prototype does not intentionally persist form data or PDFs. Normal hosting/email provider logs can still contain operational metadata, so production privacy/retention settings should be reviewed.
