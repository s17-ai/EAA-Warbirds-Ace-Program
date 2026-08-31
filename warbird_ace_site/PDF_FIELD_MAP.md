# PDF overlay field map

The source is US Letter, 612 x 792 points. Coordinates in `app.py` use PyMuPDF's top-left coordinate system.

The current map covers:
- Page 1: application type; applicant identity/certificate/medical data; renewal experience rows; requested level; applicant signature/date; evaluator notes; evaluation location/date; limitations; altitude restrictions; show-line category; approved aircraft; evaluator name/signature/date; aircraft flown; remarks.
- Page 2: applicant initials/date.
- Page 3: applicant final signature/date.

Before production, run test applications with long and short entries and visually verify every overlay against the committee-approved master. Adjust `draw_text`, `draw_multiline`, and coordinate tuples in `generate_pdf()` as needed.
