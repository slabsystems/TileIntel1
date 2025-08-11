# app.py
import io
import datetime
from pathlib import Path
import tempfile

import streamlit as st
from fpdf import FPDF
from PIL import Image, UnidentifiedImageError

# -----------------------------------------------------------------------------
# Utils
# -----------------------------------------------------------------------------

def _to_ascii(s):
    """Convert curly quotes, en/em dashes, bullets, etc. to ASCII so FPDF core fonts won't crash."""
    if s is None:
        return ""
    repl = {
        "—": "-", "–": "-", "•": "-",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "…": "...", "×": "x", "™": "(TM)", "®": "(R)",
        "°": " degrees",
    }
    return "".join(repl.get(ch, ch) for ch in str(s))

def mm(x):
    """Tiny helper in case you want to think in mm (not used, but handy)."""
    return x

# -----------------------------------------------------------------------------
# Calculations (very simple MVP defaults; tune in the sidebar)
# -----------------------------------------------------------------------------

def calc_tiles(area_m2, waste_pct, tile_len_mm, tile_w_mm):
    # tiles per m2 = 1 m2 / tile_area_m2
    tile_area_m2 = (tile_len_mm / 1000) * (tile_w_mm / 1000)
    if tile_area_m2 <= 0:
        return 0
    base = area_m2 / tile_area_m2
    return int(round(base * (1 + waste_pct / 100.0)))

def calc_primer_l(area_m2, primer_cov_m2_per_l):
    if primer_cov_m2_per_l <= 0:
        return 0.0
    return round(area_m2 / primer_cov_m2_per_l, 2)

def calc_adhesive_bags(area_m2, adhesive_cov_m2_per_bag):
    if adhesive_cov_m2_per_bag <= 0:
        return 0
    return int(round(area_m2 / adhesive_cov_m2_per_bag))

def calc_grout_bags(area_m2, grout_cov_m2_per_bag):
    if grout_cov_m2_per_bag <= 0:
        return 0
    return int(round(area_m2 / grout_cov_m2_per_bag))

def calc_levelling_bags(area_m2, avg_depth_mm, bag_coverage_m2_per_mm):
    # coverage: m2 per mm per bag -> total mm*m2 / coverage
    if bag_coverage_m2_per_mm <= 0:
        return 0.0
    needed = (area_m2 * max(0.0, avg_depth_mm)) / bag_coverage_m2_per_mm
    return round(needed, 1)

# -----------------------------------------------------------------------------
# PDF Helpers
# -----------------------------------------------------------------------------

def _safe_add_logo(pdf: FPDF, max_w=40):
    """Try to add assets/logo.png if it exists."""
    logo_path = Path(__file__).parent / "assets" / "logo.png"
    if logo_path.exists():
        try:
            pdf.image(str(logo_path), w=max_w)
            pdf.ln(2)
        except Exception:
            pass

def _pil_image_from_upload(upload):
    """
    Try to open an uploaded file (Streamlit UploadedFile) with PIL.
    Returns PIL.Image or None if unsupported or it's a PDF, etc.
    """
    try:
        if upload.type and "pdf" in upload.type.lower():
            return None
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
        if img.mode != "RGB":
            img = img.convert("RGB")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_path = tmp.name
            img.save(tmp_path, format="PNG")
        try:
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, _to_ascii(f"Uploaded Image: {file.name}"), ln=1)
            pdf.image(tmp_path, w=160)  # scale to page width
        except Exception:
            pass

def generate_pdf(job):
    """
    job: dict with fields shown below. Returns bytes (PDF).
    """
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Header
    _safe_add_logo(pdf)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _to_ascii("TileIntel - Method Statement (MVP)"), ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _to_ascii(f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M}"), ln=1)
    pdf.ln(2)

    # Project overview
    def row(label, value):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 6, _to_ascii(f"{label}: "), align="R")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, _to_ascii(value if value is not None else ""))

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _to_ascii("Project Overview"), ln=1)
    row("Project", job.get("project_desc"))
    row("Room", job.get("room"))
    row("Substrate", job.get("substrate"))
    row("UFH", job.get("ufh"))
    row("Area (m2)", job.get("area_m2"))
    row("Tile size", job.get("tile_size"))
    row("Adhesive", job.get("adhesive"))
    row("Grout", job.get("grout"))
    row("Levelling depth (mm)", job.get("levelling_depth_mm"))
    pdf.ln(2)

    # Calculations
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _to_ascii("Calculated Materials"), ln=1)
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
        pdf.cell(0, 8, _to_ascii("Notes"), ln=1)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, _to_ascii(notes))
        pdf.ln(2)

    # Compliance / standards (placeholder copy)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _to_ascii("Compliance (UK - BS 5385 and related guidance)"), ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0, 5,
        _to_ascii(
            "- Check substrate moisture/surface per BS 8203 / BS 5385.\n"
            "- Anhydrite screeds: sand/abrade laitance; verify moisture content.\n"
            "- Follow UFH commissioning sequence before tiling; switch off 48h pre-fix.\n"
            "- Use manufacturer data sheets (primer/adhesive/grout) for mixing & coverage.\n"
            "- Movement joints per BS 5385 and site layout.\n"
        )
    )

    # Uploaded images (if any)
    uploads = job.get("uploads") or []
    if uploads:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, _to_ascii("Uploaded Plans / Photos"), ln=1)
        _add_uploaded_images(pdf, uploads)

    return pdf.output(dest="S").encode("latin-1")

# -----------------------------------------------------------------------------
# Streamlit App
# -----------------------------------------------------------------------------

st.set_page_config(page_title="TileIntel - MVP Calculator", page_icon="🧱", layout="centered")

st.title("TileIntel — MVP Calculator")
st.caption("For accurate fast quoting with manufacturer-specified products. *MVP for evaluation only.*")

with st.sidebar:
    st.header("Inputs / Assumptions")

    # Area & tiles
    area_m2 = st.number_input("Area (m²)", value=50.0, min_value=0.0, step=1.0)
    tile_size = st.selectbox(
        "Tile size",
        ["600x600 mm", "1000x1000 mm", "1200x600 mm", "750x750 mm", "300x600 mm"],
        index=0
    )
    tile_len_mm, tile_w_mm = [int(x) for x in tile_size.replace(" mm", "").split("x")]

    waste_pct = st.slider("Waste (%)", 0, 20, 10)

    # Materials (select names only; actual brands are user-facing text)
    adhesive = st.text_input("Adhesive", value="Kerakoll H40")
    grout = st.text_input("Grout", value="Kerakoll Fugabella 43")
    substrate = st.text_input("Substrate", value="Anhydrite screed")
    ufh = st.selectbox("Underfloor heating", ["None", "Water fed (in screed)", "Electric (mat)"], index=1)

    levelling_depth_mm = st.number_input("Average levelling depth (mm)", value=3.0, min_value=0.0, step=0.5)

    # Coverage assumptions
    st.subheader("Coverage assumptions")
    primer_cov_m2_per_l = st.number_input("Primer coverage (m² / L)", value=6.5, min_value=0.1, step=0.1)
    adhesive_cov_m2_per_bag = st.number_input("Adhesive coverage (m² / bag)", value=5.0, min_value=0.1, step=0.1)
    grout_cov_m2_per_bag = st.number_input("Grout coverage (m² / bag)", value=16.0, min_value=0.1, step=0.1)
    bag_coverage_m2_per_mm = st.number_input("Levelling coverage (m²·mm / bag)", value=13.0, min_value=0.1, step=0.1)

    st.markdown("---")
    project_desc = st.text_input("Project description", value="Floor with UFH; porcelain tiles")
    room = st.text_input("Room", value="Ground floor")

    notes = st.text_area(
        "Notes (optional)",
        value="Check drying times & moisture content per BS 5385. Sand/abrade anhydrite screed before priming."
    )

# File upload (plans/photos)
uploads = st.file_uploader(
    "Upload plans/photos (optional)", type=["png", "jpg", "jpeg", "webp", "pdf"], accept_multiple_files=True
)
st.session_state["uploads"] = uploads

# Calculations
tile_count = calc_tiles(area_m2, waste_pct, tile_len_mm, tile_w_mm)
primer_l = calc_primer_l(area_m2, primer_cov_m2_per_l)
adhesive_bags = calc_adhesive_bags(area_m2, adhesive_cov_m2_per_bag)
grout_bags = calc_grout_bags(area_m2, grout_cov_m2_per_bag)
levelling_bags = calc_levelling_bags(area_m2, levelling_depth_mm, bag_coverage_m2_per_mm)

st.subheader("Results")
c1, c2, c3 = st.columns(3)
with c1: st.metric("Tiles needed (incl. waste)", tile_count)
with c2: st.metric("Adhesive (bags)", adhesive_bags)
with c3: st.metric("Grout (bags)", grout_bags)

c4, c5 = st.columns(2)
with c4: st.metric("Primer (L)", primer_l)
with c5: st.metric("Levelling compound (bags)", levelling_bags)

st.caption("These are indicative MVP calculations. Always follow manufacturer datasheets and British Standards.")

# Build job dict for PDF
job = {
    "project_desc": project_desc,
    "room": room,
    "substrate": substrate,
    "ufh": ufh,
    "area_m2": area_m2,
    "tile_size": tile_size,
    "adhesive": adhesive,
    "grout": grout,
    "levelling_depth_mm": levelling_depth_mm,
    "tile_count": tile_count,
    "primer_l": primer_l,
    "adhesive_bags": adhesive_bags,
    "grout_bags": grout_bags,
    "levelling_bags": levelling_bags,
    "notes": notes,
    "uploads": uploads,
}

# PDF button
pdf_bytes = generate_pdf(job)
st.download_button(
    "Download Method Statement (PDF)",
    data=pdf_bytes,
    file_name="TileIntel_Method_Statement.pdf",
    mime="application/pdf"
)

# Footer (optional)
st.markdown("---")
st.caption("TileIntel MVP — Streamlit build for demo purposes only.")
