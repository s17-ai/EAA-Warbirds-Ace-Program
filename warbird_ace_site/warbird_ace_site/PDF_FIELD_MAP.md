# PDF field mapping - current fillable SAC form

The website now fills the named AcroForm fields in `static/forms/woa-sac-blank.pdf` instead of stamping most values at hard-coded coordinates.

Key changes in this form revision:

- Requested SAC level: 250 ft or 500 ft only.
- Form 8710.7 limitations: Dogfight or Combination of Loops and Rolls only.
- Altitude restrictions: 250 or 500 only.
- Rolls Only and 800 ft selections are not present on the web page or PDF mapping.
- The current PDF contains eight show/practice experience rows.
- Applicant and evaluator handwritten signatures are captured on the website and embedded as images in the existing signature locations.
- EAA office-use fields remain blank and editable in the generated PDF.

If a future PDF revision changes field names, inspect it with the PDF form-field tools and update `pdf_service.py` accordingly.
