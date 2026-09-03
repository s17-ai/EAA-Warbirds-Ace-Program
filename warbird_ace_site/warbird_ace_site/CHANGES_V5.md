# V5 update - revised SAC application

This release updates the website to the current fillable SAC PDF supplied by the committee chair.

- Replaced the bundled SAC master PDF with the revised three-page fillable form.
- Website application now offers only 250 ft and 500 ft requested levels.
- Removed Rolls Only from Form 8710.7 limitations.
- Removed all 800 ft altitude restriction options.
- Increased renewal show/practice rows from seven to eight to match the current PDF.
- Re-rendered the waiver preview images from the current PDF.
- PDF generation now uses the PDF's named AcroForm fields as the source of truth for placement.
- Applicant/evaluator signatures are embedded into the existing signature locations.
- EAA office-use fields remain blank and fillable in the generated PDF.
- Email destination remains server-side through `CHAIRMAN_EMAIL` (currently intended for `kschaick@eaa.org`).
