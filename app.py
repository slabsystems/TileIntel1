# app.py
# TileIntel — MVP Calculator (Streamlit) with bulletproof PDF export
# - Global try/except to avoid blank screen
# - FPDF "not enough horizontal space" guarded with safe widths
# - ASCII-safe text for PDF

from __future__ import annotations
import math
from io import BytesIO
from typing import Dict, Any, Tuple

import streamlit as st
import pandas as pd
from fpdf import FPDF

# -----------------------------
# Helpers (robust + PDF guards)
# -----------------------------

def ascii_safe(text: str) -> str:
    """
    Convert text to a PDF-safe ASCII-ish form.
    Replaces characters outside Latin-1 and strips newlines appropriately.
    """
    if text is None:
        return ""
    # Replace hard newlines with spaces for table cells; PDF rows can wrap separately
    text = str(text).replace("\r", " ").replace("\n", " ")
    # Best effort: encode to latin-1, replace unencodable chars with '?'
    return text.encode("latin-1", "replace").decode("latin-1")


def safe_multicell(pdf: FPDF, w: float, h: float, txt: str, border=0, align="L"):
    """
    Guarded version of FPDF.multi_cell that never raises
    'Not enough horizontal space to render a single character'.
    """
    # FPDF can choke if w is too small; clamp to a safe minimum.
    MIN_W = 16  # points ~ enough for a digit/short word at default font size
    if w < MIN_W:
        w = MIN_W
    txt = ascii_safe(txt)
    # Split long strings into chunks that can at least place one char
    # (With MIN_W above, a single char will always fit).
    pdf.multi_cell(w, h, txt, border=border, align=align)


def pdf_kv_row(pdf: FPDF, label: str, value: str, page_w: float, margin: float, lh: float = 7):
    """
    Draw a key/value row with two cells, using safe widths.
    """
    col1 = max(40.0, (page_w - 2 * margin) * 0.35)
    col2 = max(40.0, (page_w - 2 * margin) - col1)

    pdf.set_font("Helvetica", "B", 11)
    safe_multicell(pdf, col1, lh, ascii_safe(label))
    pdf.set_xy(pdf.get_x() + col1, pdf.get_y() - lh)  # move back up to same line start

    pdf.set_font("Helvetica", "", 11)
    safe_multicell(pdf, col2, lh, ascii_safe(value))
    # Move cursor to next line baseline
    pdf.ln(lh)


def materials_calc(
    area_m2: float,
    tile_mm: Tuple[int, int],
    adhesive: str,
    grout: str,
    substrate: str,
    ufh: str,
) -> Dict[str, Any]:
    """
    Really simple, transparent sample assumptions.
    Replace these with proper BS/EN datasheet yields when you’re ready.
    """
    t_w, t_h = tile_mm

    # Adhesive coverage (bag 20kg) – naive assumptions for demo
    notch_10mm_m2_per_bag = 3.0
    notch_8mm_m2_per_bag = 3.8
    coverage_per_bag = notch_10mm_m2_per_bag if max(t_w, t_h) >= 900 else notch_8mm_m2_per_bag
    adhesive_bags = math.ceil(area_m2 / coverage_per_bag) if area_m2 > 0 else 0

    # Grout coverage – very rough demo calc
    # perimeter per tile * joint width * depth / grout density
    joint_mm = 3 if max(t_w, t_h) <= 600 else 5
    joint_depth_mm = 6
    tiles_per_m2 = (1000 / t_w) * (1000 / t_h)
    perimeter_per_tile_mm = 2 * (t_w + t_h)
    grout_vol_per_m2_mm3 = tiles_per_m2 * perimeter_per_tile_mm * joint_mm * joint_depth_mm
    # Convert mm3/m2 to litres/m2 (1e6 mm3 = 1 litre); grout density ~ 1.8 kg/L → ~ consumption proxy
    grout_l_per_m2 = grout_vol_per_m2_mm3 / 1_000_000.0
    # Demo bag yield: 5kg bag ≈ 2.5 L placed (filler for demo only)
    grout_bag_l_yield = 2.5
    grout_bags = math.ceil((grout_l_per_m2 * area_m2) / grout_bag_l_yield) if area_m2 > 0 else 0

    # Primer – simple rule: 1L covers ~10 m2 (first coat), 2 coats on anhydrite
    primer_l_per_coat_per_m2 = 0.1
    coats = 2 if "anhyd" in substrate.lower() else 1
    primer_l = round(area_m2 * primer_l_per_coat_per_m2 * coats, 2)

    # Levelling – demo only (e.g., 3mm average depth → 1.6 kg/mm/m2)
    levelling_mm = 0
    if "anhyd" in substrate.lower():
        # if sanding/levelling required in many anhydrite screeds – demo 3mm
        levelling_mm = 3
    levelling_compound_bags_25kg = math.ceil(area_m2 * levelling_mm * 1.6 / 25.0) if levelling_mm > 0 else 0

    return {
        "adhesive_bags": adhesive_bags,
        "adhesive_type": adhesive,
        "grout_bags": grout_bags,
        "grout_type": grout,
        "primer_litres": primer_l,
        "levelling_bags": levelling_compound_bags_25kg,
        "joint_mm": joint_mm,
        "notes": f"Substrate: {substrate} | UFH: {ufh}",
    }


def build_pdf(job: Dict[str, Any]) -> bytes:
    """
    Create a robust Method Statement PDF with guarded cell widths and ASCII-safe text.
    """
    pdf = FPDF(unit="pt", format="A4")  # points for easy width math
    pdf.set_auto_page_break(auto=True, margin=36)
    pdf.add_page()
    margin = 36.0
    page_w = pdf.w

    # Header
    pdf.set_font("Helvetica", "B", 18)
    safe_multicell(pdf, page_w - 2 * margin, 20, "TileIntel — Method Statement")
    pdf.ln(6)

    # Job info
    pdf.set_font("Helvetica", "", 11)
    pdf_kv_row(pdf, "Project", job.get("project", "-"), page_w, margin)
    pdf_kv_row(pdf, "Room/Area", job.get("room", "-"), page_w, margin)
    pdf_kv_row(pdf, "Substrate", job.get("substrate", "-"), page_w, margin)
    pdf_kv_row(pdf, "UFH", job.get("ufh", "-"), page_w, margin)
    pdf_kv_row(pdf, "Tile", f'{job.get("tile_w")} x {job.get("tile_h")} mm, {job.get("tile_thick")} mm', page_w, margin)
    pdf_kv_row(pdf, "Area (m²)", str(job.get("area_m2", 0)), page_w, margin)
    pdf.ln(6)

    # Materials
    pdf.set_font("Helvetica", "B", 13)
    safe_multicell(pdf, page_w - 2 * margin, 16, "Materials")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    mats = job["materials"]
    lines = [
        f"Primer: {mats['primer_litres']} L",
        f"Adhesive: {mats['adhesive_bags']} bags ({mats['adhesive_type']})",
        f"Grout: {mats['grout_bags']} bags ({mats['grout_type']}) — {mats['joint_mm']} mm joints (assumed)",
        f"Levelling compound: {mats['levelling_bags']} x 25 kg",
    ]
    for ln in lines:
        safe_multicell(pdf, page_w - 2 * margin, 14, f"• {ln}")
    pdf.ln(6)

    # Method (demo)
    pdf.set_font("Helvetica", "B", 13)
    safe_multicell(pdf, page_w - 2 * margin, 16, "Method (summary)")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    method = [
        "1) Verify substrate (flatness, strength, moisture, laitance removal for anhydrite).",
        "2) Prime as per manufacturer datasheet; allow to dry.",
        "3) If required, apply levelling compound; cure as specified.",
        "4) Fix tiles with selected adhesive and correct trowel notch.",
        "5) Respect movement joints and perimeter requirements (BS 5385).",
        "6) Grout with specified colour and joint width after adhesive has cured.",
    ]
    for step in method:
        safe_multicell(pdf, page_w - 2 * margin, 14, step)

    # Notes
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 13)
    safe_multicell(pdf, page_w - 2 * margin, 16, "Notes")
    pdf.set_font("Helvetica", "", 11)
    safe_multicell(pdf, page_w - 2 * margin, 14, ascii_safe(mats["notes"]))

    # Output bytes
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


# -----------------------------
# UI
# -----------------------------

def ui() -> None:
    st.set_page_config(page_title="TileIntel — MVP", page_icon="🧱", layout="centered")
    st.title("TileIntel — MVP Calculator")

    with st.form("job"):
        c1, c2 = st.columns(2)
        with c1:
            project = st.text_input("Project", placeholder="Client / address / ref")
            room = st.text_input("Room/Area", placeholder="Kitchen, GF hallway…")
            area_m2 = st.number_input("Area (m²)", min_value=0.0, value=20.0, step=1.0)
            substrate = st.selectbox("Substrate", ["Concrete", "Anhydrite screed", "Plywood overlay", "Backer board"])
            ufh = st.selectbox("Underfloor heating", ["None", "Water-fed in screed", "Electric mat"])
        with c2:
            tile_w = st.number_input("Tile width (mm)", min_value=50, value=600, step=50)
            tile_h = st.number_input("Tile height (mm)", min_value=50, value=600, step=50)
            tile_thick = st.number_input("Tile thickness (mm)", min_value=3.0, value=9.0, step=0.5)
            adhesive = st.selectbox("Adhesive", ["C2 TE S1", "C2 TE S2", "H40 (Kerakoll)", "Rapid set C2"])
            grout = st.selectbox("Grout", ["CG2", "Kerakoll Fugabella 43", "Epoxy RG"])

        plan = st.file_uploader("Upload plan / images (optional)", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
        notes = st.text_area("Additional notes (optional)")

        submitted = st.form_submit_button("Calculate")

    if submitted:
        # Compute materials
        mats = materials_calc(
            area_m2=area_m2,
            tile_mm=(int(tile_w), int(tile_h)),
            adhesive=adhesive,
            grout=grout,
            substrate=substrate,
            ufh=ufh,
        )
        # Display
        st.subheader("Results")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Primer (L)", f"{mats['primer_litres']}")
            st.metric("Adhesive (bags)", f"{mats['adhesive_bags']}")
        with c2:
            st.metric("Grout (bags)", f"{mats['grout_bags']}")
            st.metric("Levelling (25kg)", f"{mats['levelling_bags']}")
        with c3:
            st.metric("Joint (mm)", str(mats["joint_mm"]))
            st.caption("Demo assumptions. Always verify with manufacturer datasheets & BS 5385.")

        # Build PDF package for download
        job = {
            "project": project,
            "room": room,
            "area_m2": area_m2,
            "substrate": substrate,
            "ufh": ufh,
            "tile_w": int(tile_w),
            "tile_h": int(tile_h),
            "tile_thick": tile_thick,
            "materials": mats | {"notes": (notes or "")},
        }

        try:
            pdf_bytes = build_pdf(job)
            st.download_button(
                label="⬇️ Download Method Statement (PDF)",
                data=pdf_bytes,
                file_name="TileIntel_Method_Statement.pdf",
                mime="application/pdf",
            )
        except Exception as e:  # noqa
            st.error("PDF generation hit a snag (kept the app running). Full details below:")
            st.exception(e)

    st.divider()
    st.caption("TileIntel MVP • Streamlit • This build includes guards for PDF rendering edge-cases.")


# -----------------------------
# Main with global guard
# -----------------------------
if __name__ == "__main__":
    try:
        ui()
    except Exception as e:  # noqa
        st.error("Something went wrong in the app. The error is shown below so the UI never goes blank.")
        st.exception(e)
