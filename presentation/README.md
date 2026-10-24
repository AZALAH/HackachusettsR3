# Presentation

| File | What it is |
|---|---|
| `DataMon.pptx` | The 9-slide pitch deck. Fully editable; speaker notes hold the script. |
| `VIDEO_SCRIPT.md` | The timed 3-minute video script, with recording tips. |
| `SUBMISSION.md` | Paste-ready text for the submission form, including the Kiro write-up. |
| `build_slides.py` | Rebuilds `DataMon.pptx` (Python standard library only). |
| `assets/` | Images used in the deck. |

## Open the deck in Google Slides

1. Download `DataMon.pptx` from GitHub (open the file, then click **Download raw file**).
2. Go to [drive.google.com](https://drive.google.com) → **New** → **File upload** → choose `DataMon.pptx`.
3. Right-click the uploaded file → **Open with** → **Google Slides**.
4. In Google Slides: **File** → **Save as Google Slides** for a native copy you can edit.

The deck uses Montserrat and Open Sans, which Google Slides has built in.

## Rebuild after editing the text

    python presentation/build_slides.py
