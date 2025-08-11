import streamlit as st
from fpdf import FPDF
import math
from datetime import datetime

st.set_page_config(page_title="TileIntel MVP", page_icon="🧱", layout="centered")

st.title("🧱 TileIntel — MVP Calculator")
st.caption("Fast, consistent job specs, quantities & a branded PDF method statement.")

with st.expander("About this MVP", expanded=False):
    st.write("""
    This is a lightweight prototype for spec & quantity calculations:
    - Inputs: area, tile size, substrate, UFH, adhesive, grout, levelling depth
    - Outputs: materials (primer, adhesive, grout, levelling), tiles + 10% waste
    - Generate a **PDF method statement** with your branding
    """)

# --- Inputs ---
colA, colB = st.columns(2)
with colA:
    job_name = st.text_input("Job name / reference", value="Project Alpha")
    area_m2 = st.number_input("Area (m²)", min_value=0.1, value=50.0, step=0.1)
    substrate = st.selectbox("Substrate", ["Anhydrite screed", "Sand/cement screed", "Concrete", "Plywood", "Backer board", "Other"])
    ufh = st.selectbox("Underfloor heating", ["No", "Yes - Electric", "Yes - Water-fed"])
with colB:
    tile_size = st.selectbox("Tile size", ["600x600", "1000x1000", "1200x600", "750x750", "Other"])
    other_tile = st.text_input("Custom tile size (mm x mm)", value="", help="Only used if Tile size = Other, e.g. 450x450")
    adhesive = st.selectbox("Adhesive", ["Kerakoll H40", "Kerakoll BioGel No Limits", "Other"])
    grout = st.selectbox("Grout", ["Kerakoll Fugabella 43", "Kerakoll Fugalite Bio", "Other"])

lev_mm = st.slider("Levelling compound depth (mm)", min_value=0, max_value=20, value=0)
include_primer = st.checkbox("Primer required", value=True)
notes = st.text_area("Notes (optional)", value="Check drying time & moisture content per BS 5385. Sand/abrade anhydrite laitance before priming.")

uploaded_files = st.file_uploader("Upload floor plans, photos or PDFs (optional)", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)

# --- Helpers ---
def parse_tile_size(tile_size, other):
    if tile_size != "Other":
        w, h = tile_size.split("x")
        return int(w), int(h)
    if "x" in other:
        try:
            w, h = other.lower().replace("mm","").split("x")
            return int(w.strip()), int(h.strip())
        except:
            pass
    return 600, 600

def round_up(n, decimals=0):
    factor = 10 ** decimals
    return math.ceil(n * factor) / factor

# coverage assumptions (MVP; adjust later per datasheet)
COVERAGE = {
    "primer_L_per_m2": 0.15,      # 0.15 L/m²
    "adhesive_kg_per_m2": 4.0,    # 4 kg/m²
    "grout_kg_per_m2": 0.3,       # 0.3 kg/m² (approx depends on joint width)
    "levelling_kg_per_mm_m2": 1.6 # 1.6 kg per mm per m²
}

BAG_SIZES = {
    "adhesive_kg": 20,
    "grout_kg": 5,
    "levelling_kg": 25
}

# --- Calculations ---
w_mm, h_mm = parse_tile_size(tile_size, other_tile)
tile_m2 = (w_mm/1000) * (h_mm/1000)

tiles_exact = area_m2 / tile_m2 if tile_m2 > 0 else 0
tiles_with_waste = math.ceil(tiles_exact * 1.10)  # +10% waste

primer_l = COVERAGE["primer_L_per_m2"] * area_m2 if include_primer else 0.0

adh_kg = COVERAGE["adhesive_kg_per_m2"] * area_m2
adh_bags = math.ceil(adh_kg / BAG_SIZES["adhesive_kg"])

grout_kg = COVERAGE["grout_kg_per_m2"] * area_m2
grout_bags = math.ceil(grout_kg / BAG_SIZES["grout_kg"])

lev_kg = COVERAGE["levelling_kg_per_mm_m2"] * lev_mm * area_m2 if lev_mm > 0 else 0.0
lev_bags = math.ceil(lev_kg / BAG_SIZES["levelling_kg"]) if lev_kg > 0 else 0

# --- Results ---
st.subheader("Results")
st.write(f"**Tiles needed (incl. 10% waste):** {tiles_with_waste} units ({w_mm}×{h_mm} mm)")
c1, c2 = st.columns(2)
with c1:
    st.metric("Adhesive (kg)", f"{adh_kg:.1f}")
    st.metric("Adhesive bags (20kg)", f"{adh_bags}")
    if include_primer:
        st.metric("Primer (L)", f"{primer_l:.1f}")
with c2:
    st.metric("Grout (kg)", f"{grout_kg:.1f}")
    st.metric("Grout bags (5kg)", f"{grout_bags}")
    if lev_mm > 0:
        st.metric("Levelling (kg)", f"{lev_kg:.1f} ({lev_mm} mm)")
        st.metric("Levelling bags (25kg)", f"{lev_bags}")

st.divider()

# --- PDF Generation ---
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "TileIntel — Installation Method Statement (MVP)", ln=True, align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"TileIntel • Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} • www.tileintel.com", align="C")

def build_pdf() -> bytes:
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Project Overview", ln=True)
    pdf.set_font("Arial", "", 11)
    lines = [
        f"Job Name: {job_name}",
        f"Area: {area_m2:.2f} m²",
        f"Substrate: {substrate}",
        f"Underfloor Heating: {ufh}",
        f"Tile Size: {w_mm} x {h_mm} mm",
        f"Adhesive: {adhesive}",
        f"Grout: {grout}",
        f"Levelling Depth: {lev_mm} mm",
    ]
    for line in lines:
        pdf.cell(0, 7, line, ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Quantities", ln=True)
    pdf.set_font("Arial", "", 11)
    qty_lines = [
        f"Tiles (incl. 10% waste): {tiles_with_waste} units",
        f"Primer: {primer_l:.1f} L" if include_primer else "Primer: Not included",
        f"Adhesive: {adh_kg:.1f} kg  ({adh_bags} × 20 kg)",
        f"Grout: {grout_kg:.1f} kg  ({grout_bags} × 5 kg)",
    ]
    if lev_mm > 0:
        qty_lines.append(f"Levelling: {lev_kg:.1f} kg  ({lev_bags} × 25 kg) at {lev_mm} mm")
    for line in qty_lines:
        pdf.cell(0, 7, line, ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Method Notes (MVP)", ln=True)
    pdf.set_font("Arial", "", 10)
    methods = [
        "• Verify substrate is sound, rigid and level. Prep per BS 5385.",
        "• Anhydrite screeds: mechanically abrade laitance; moisture ≤ 0.5% CM / 75% RH before tiling.",
        "• Prime per manufacturer guidance; allow to dry.",
        "• Trowel size and back-buttering may change adhesive consumption.",
        "• Movement joints per BS 5385 and perimeter isolation around UFH zones.",
        "• Follow Kerakoll technical datasheets for H40 & Fugabella 43."
    ]
    for m in methods:
        pdf.multi_cell(0, 6, m)
    pdf.ln(2)

    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 5, "This MVP provides indicative quantities only. Confirm site conditions and product datasheets before ordering.")
    return bytes(pdf.output(dest="S").encode("latin-1"))

pdf_bytes = build_pdf()
st.download_button("📄 Download Method Statement (PDF)", data=pdf_bytes, file_name=f"{job_name.replace(' ','_')}_TileIntel_Method.pdf", mime="application/pdf")

st.success("MVP ready. Adjust coverage constants or add product libraries in code for more precision.")
st.caption("© TileIntel. Prototype generated with Streamlit.")
