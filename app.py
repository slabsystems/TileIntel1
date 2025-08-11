# app.py — TileIntel MVP (Streamlit + safe PDF)
# -------------------------------------------------
# Drop-in file. Paste into your repo root and deploy.
# Shows a calculator, renders results, and exports a robust PDF.

import io
import math
import datetime as dt
from typing import Dict, Any, List, Tuple

import streamlit as st
import pandas as pd
from fpdf import FPDF

# -----------------------------
# Page & global guards
# -----------------------------
st.set_page_config(page_title="TileIntel — MVP", layout="wide")

def show_startup_error(e: Exception):
    st.error("Startup error: " + repr(e))
    st.stop()

try:
    # put any additional imports inside this try if you add more later
    pass
except Exception as e:
    show_startup_error(e)

# -----------------------------
# Helpers (safe text + PDF)
# -----------------------------
ASCII_FALLBACK = {"–": "-", "—": "-", "’": "'", "“": '"', "”": '"', "•": "-"}

def to_ascii(s: str) -> str:
    if s is None:
        return ""
    for k, v in ASCII_FALLBACK.items():
        s = s.replace(k, v)
    # Strip non-ascii
    return s.encode("ascii", errors="ignore").decode("ascii")

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "TileIntel — Job Pack", 0, 1, "L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(90)
        self.cell(0, 5, f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, "L")
        self.ln(2)
        self.set_text_color(0)

def safe_multicell(pdf: PDF, txt: str, w: float = 0, h: float = 5):
    """
    Wrapper around multi_cell that ensures a minimum width and
    strips any problematic characters to avoid FPDF width errors.
    """
    txt = to_ascii(txt)
    # Effective width
    eff = pdf.w - pdf.r_margin - pdf.x
    width = max(40, w or eff)  # never go below 40 to avoid "single char" crash
    pdf.multi_cell(width, h, txt)

def row(pdf: PDF, label: str, value: str, label_w: float = 40, value_w: float = 0):
    label = to_ascii(label)
    value = to_ascii(value)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(label_w, 6, label, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    if value_w == 0:
        value_w = pdf.w - pdf.r_margin - pdf.x
    safe_multicell(pdf, value, w=value_w, h=6)

def draw_table(pdf: PDF, rows: List[Tuple[str, str]]):
    for k, v in rows:
        row(pdf, k, v)

def as_downloadable_pdf(job: Dict[str, Any], results: Dict[str, Any], method_lines: List[str]) -> bytes:
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)

    # Job overview
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Job Overview", 0, 1)
    pdf.set_font("Helvetica", "", 10)

    overview = [
        ("Client / Project", job["project_desc"] or "-"),
        ("Room", job["room"] or "-"),
        ("Area (m²)", f'{job["area_m2"]:,.2f}'),
        ("Tile size (mm)", job["tile_size"]),
        ("Substrate", job["substrate"]),
        ("Underfloor heating", "Yes" if job["ufh"] else "No"),
        ("Adhesive", job["adhesive"]),
        ("Grout", job["grout"]),
    ]
    draw_table(pdf, overview)
    pdf.ln(2)

    # Results
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Calculated Materials", 0, 1)
    pdf.set_font("Helvetica", "", 10)
    r_tbl = [
        ("Primer (L)", f'{results["primer_l"]:,.2f}'),
        ("Adhesive (kg)", f'{results["adhesive_kg"]:,.2f}'),
        ("Grout (kg)", f'{results["grout_kg"]:,.2f}'),
        ("Levelling (kg)", f'{results["levelling_kg"]:,.2f}'),
        ("Perimeter Silicone (lm)", f'{results["silicone_lm"]:,.2f}'),
    ]
    draw_table(pdf, r_tbl)
    pdf.ln(2)

    # Method statement
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Method Statement (summary)", 0, 1)
    pdf.set_font("Helvetica", "", 10)
    for ln in method_lines:
        safe_multicell(pdf, f"• {ln}", h=6)
    pdf.ln(2)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

# -----------------------------
# Estimation logic (simple MVP)
# -----------------------------
TILE_CHOICES = [
    "600 x 600 x 10",
    "800 x 800 x 10",
    "1000 x 1000 x 6",
    "1200 x 600 x 10",
]

SUBSTRATE_CHOICES = [
    "Anhydrite screed",
    "Sand/cement screed",
    "Concrete slab",
    "Timber / tilebacker boards",
]

ADHESIVE_CHOICES = [
    "Kerakoll H40",
    "C2 TE S1",
    "C2F rapid",
]

GROUT_CHOICES = [
    "Kerakoll Fugabella 43",
    "CG2 WA",
    "Standard CG2",
]

def parse_tile_mm(tile: str) -> Tuple[int, int, int]:
    # "600 x 600 x 10" -> (600,600,10)
    try:
        parts = tile.lower().replace(" ", "").split("x")
        return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        return 600, 600, 10

def adhesive_kg_per_m2(tile: str, ufh: bool) -> float:
    # Simple heuristic for MVP
    w, h, t = parse_tile_mm(tile)
    # Large format tends to need thicker bed
    base = 3.0 if max(w, h) <= 600 else 4.0
    if ufh:
        base += 0.5
    return base  # kg/m2

def grout_kg_per_m2(tile: str) -> float:
    # Very rough rule: smaller tiles = more joints
    w, h, t = parse_tile_mm(tile)
    joint_factor = 2.0 if max(w, h) <= 600 else 1.2
    return 0.3 * joint_factor  # kg/m2

def primer_l_per_m2(substrate: str) -> float:
    m = {
        "Anhydrite screed": 0.15,
        "Sand/cement screed": 0.12,
        "Concrete slab": 0.12,
        "Timber / tilebacker boards": 0.10,
    }
    return m.get(substrate, 0.12)

def levelling_kg_per_m2(need_levelling: bool) -> float:
    return 3.0 if need_levelling else 0.0

def perimeter_silicone_lm(length_m: float, width_m: float) -> float:
    if length_m > 0 and width_m > 0:
        return 2.0 * (length_m + width_m)
    return 0.0

def compute(area_m2: float,
            tile: str,
            substrate: str,
            ufh: bool,
            need_levelling: bool,
            length_m: float,
            width_m: float) -> Dict[str, float]:

    res = {}
    res["primer_l"] = area_m2 * primer_l_per_m2(substrate)
    res["adhesive_kg"] = area_m2 * adhesive_kg_per_m2(tile, ufh)
    res["grout_kg"] = area_m2 * grout_kg_per_m2(tile)
    res["levelling_kg"] = area_m2 * levelling_kg_per_m2(need_levelling)
    res["silicone_lm"] = perimeter_silicone_lm(length_m, width_m)
    return res

def method_statement(job: Dict[str, Any]) -> List[str]:
    lines = []
    lines.append("Verify substrate is sound, dry and within SR tolerance. Record moisture readings.")
    if job["substrate"] == "Anhydrite screed":
        lines.append("Mechanically abrade and thoroughly vacuum anhydrite surface to remove laitance.")
    lines.append("Prime substrate to manufacturer guidance; allow to dry.")
    if job["need_levelling"]:
        lines.append("Apply self-levelling compound to achieve flatness; respect drying/traffic times.")
    if job["ufh"]:
        lines.append("Ensure UFH is commissioned, heated/cooled per BS 5385 before tiling.")
    lines.append(f"Fix tiles ({job['tile_size']}) with {job['adhesive']} using appropriate trowel.")
    lines.append("Check coverage (≥85% floors / 100% wet areas). Lift tiles to confirm bed.")
    lines.append(f"Grout with {job['grout']} once adhesive has cured; clean as you go.")
    lines.append("Perimeters/movement joints: silicone (or pre-formed profiles) as per BS 5385.")
    return lines

# -----------------------------
# UI
# -----------------------------
st.title("TileIntel — MVP Calculator")
st.caption("Indicative MVP calculations only. Always follow manufacturer datasheets and British Standards.")

with st.form("job"):
    c1, c2, c3 = st.columns(3)
    with c1:
        project_desc = st.text_input("Client / Project", placeholder="e.g. Smith Kitchen")
        room = st.text_input("Room", placeholder="Ground floor")
        area_m2 = st.number_input("Area (m²)", min_value=1.0, value=50.0, step=1.0)
        length_m = st.number_input("Room length (m) (optional)", min_value=0.0, value=0.0, step=0.1)
        width_m = st.number_input("Room width (m) (optional)", min_value=0.0, value=0.0, step=0.1)
    with c2:
        tile_size = st.selectbox("Tile size", TILE_CHOICES, index=0)
        substrate = st.selectbox("Substrate", SUBSTRATE_CHOICES, index=0)
        ufh = st.checkbox("Underfloor heating present?")
        need_levelling = st.checkbox("Levelling compound needed?")
    with c3:
        adhesive = st.selectbox("Adhesive", ADHESIVE_CHOICES, index=0)
        grout = st.selectbox("Grout", GROUT_CHOICES, index=0)
        notes = st.text_area("Notes (optional)")

    submitted = st.form_submit_button("Calculate")

if submitted:
    try:
        job = dict(
            project_desc=project_desc.strip(),
            room=room.strip(),
            area_m2=float(area_m2),
            tile_size=tile_size,
            substrate=substrate,
            ufh=bool(ufh),
            need_levelling=bool(need_levelling),
            adhesive=adhesive,
            grout=grout,
            length_m=float(length_m),
            width_m=float(width_m),
            notes=notes.strip(),
        )

        results = compute(
            area_m2=job["area_m2"],
            tile=job["tile_size"],
            substrate=job["substrate"],
            ufh=job["ufh"],
            need_levelling=job["need_levelling"],
            length_m=job["length_m"],
            width_m=job["width_m"],
        )

        # Show results
        st.subheader("Results")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Primer (L)", f'{results["primer_l"]:,.2f}')
        c2.metric("Adhesive (kg)", f'{results["adhesive_kg"]:,.2f}')
        c3.metric("Grout (kg)", f'{results["grout_kg"]:,.2f}')
        c4.metric("Levelling (kg)", f'{results["levelling_kg"]:,.2f}')
        c5.metric("Perimeter silicone (lm)", f'{results["silicone_lm"]:,.2f}')

        # Method
        st.subheader("Method Statement (summary)")
        mlines = method_statement(job)
        for ln in mlines:
            st.write(f"- {ln}")

        # PDF
        st.subheader("Export")
        pdf_bytes = as_downloadable_pdf(job, results, mlines)
        st.download_button(
            "Download Job PDF",
            data=pdf_bytes,
            file_name="TileIntel_JobPack.pdf",
            mime="application/pdf",
        )

    except Exception as e:
        st.exception(e)
