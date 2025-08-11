from fpdf import FPDF
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import tempfile
import io
import datetime

def _safe_add_logo(pdf: FPDF, max_w=40):
    """Try to add assets/logo.png if it exists."""
    logo_path = Path(__file__).parent / "assets" / "logo.png"
    if logo_path.exists():
        try:
            pdf.image(str(logo_path), w=max_w)
        except Exception:
            # Don't crash if image is somehow invalid
            pass

def _pil_image_from_upload(upload):
    """
    Try to open an uploaded file (Streamlit UploadedFile) with PIL.
    Returns PIL.Image or None if unsupported or it's a PDF, etc.
    """
    try:
        # Some uploads can be PDFs: ignore those for embedding
        if upload.type and "pdf" in upload.type.lower():
            return None
        # BytesIO -> PIL
        return Image.open(io.BytesIO(upload.getbuffer()))
    except UnidentifiedImageError:
        return None
    except Exception:
        return None

def _add_uploaded_images(pdf: FPDF, uploads):
    """
    Converts uploaded images to PNG temporarily and embeds them.
    Silently skips non-images.
    """
    if not uploads:
        return

    for file in uploads:
        img = _pil_image_from_upload(file)
        if img is None:
            continue  # skip non-images (e.g., PDFs) without crashing

        # Convert to RGB to avoid issues with PNGs that have alpha
        if img.mode != "RGB":
            img = img.convert("RGB")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_path = tmp.name
            img.save(tmp_path, format="PNG")
        try:
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, f"Uploaded Image: {file.name}", ln=1)
            pdf.image(tmp_path, w=160)  # scale to page width
        except Exception:
            pass  # don't crash if FPDF can't place it

def generate_pdf(job):
    """
    job: dict with your computed fields + user inputs, e.g.:
      {
        "project_desc": "...",
        "room": "Ground floor",
        "substrate": "Anhydrite screed",
        "area_m2": 50,
        "tile_size": "600x600",
        "adhesive": "Kerakoll H40",
        "grout": "Kerakoll Fugabella 43",
        "levelling_depth_mm": 3,
        "tile_count": 200,
        "adhesive_bags": 10,
        "grout_bags": 3,
        "levelling_bags": 7.5,
        "primer_l": 7.5,
        "notes": "...",
        "uploads": st.session_state.get("uploads", [])  # list[UploadedFile]
      }
    Returns bytes (PDF).
    """

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Header
    _safe_add_logo(pdf)
    pdf.set_font("Helvetica", "B", 16)
    pdf.ln(2)
    pdf.cell(0, 10, "TileIntel — Method Statement (MVP)", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}", ln=1)
    pdf.ln(2)

    # Project overview
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Project Overview", ln=1)
    pdf.set_font("Helvetica", "", 11)
    def row(label, value):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 6, f"{label}:", align="R")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, f" {value}" if value is not None else "")
    row("Project", job.get("project_desc"))
    row("Room", job.get("room"))
    row("Substrate", job.get("substrate"))
    row("Area (m²)", job.get("area_m2"))
    row("Tile size", job.get("tile_size"))
    row("UFH", job.get("ufh"))
    row("Adhesive", job.get("adhesive"))
    row("Grout", job.get("grout"))
    row("Levelling depth (mm)", job.get("levelling_depth_mm"))
    pdf.ln(2)

    # Calculations
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Calculated Materials", ln=1)
    pdf.set_font("Helvetica", "", 11)
    row("Tiles needed (incl. waste)", job.get("tile_count"))
    row("Primer (L)", job.get("primer_l"))
    row("Adhesive (bags)", job.get("adhesive_bags"))
    row("Grout (bags)", job.get("grout_bags"))
    row("Levelling compound (bags)", job.get("levelling_bags"))
    pdf.ln(2)

    # Notes
    notes = job.get("notes")
    if notes:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Notes", ln=1)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, notes)
        pdf.ln(2)

    # Compliance / standards (placeholder copy)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Compliance (UK – BS 5385 & related guidance)", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0, 5,
        "- Check substrate moisture/surface per BS 8203 / BS 5385.\n"
        "- Anhydrite screeds: sand/abrade laitance; verify moisture content.\n"
        "- Follow UFH commissioning sequence before tiling; switch off 48h pre-fix.\n"
        "- Use manufacturer data sheets (primer/adhesive/grout) for mixing & coverage.\n"
        "- Movement joints per BS 5385 and site layout.\n"
    )

    # Uploaded images (if any)
    uploads = job.get("uploads") or []
    if uploads:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Uploaded Plans / Photos", ln=1)
        _add_uploaded_images(pdf, uploads)

    return pdf.output(dest="S").encode("latin-1")
