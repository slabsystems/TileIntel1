# app.py
import io
import datetime
from pathlib import Path
import tempfile

import streamlit as st
from fpdf import FPDF

def _to_ascii(s: str) -> str:
    if s is None:
        return ""
    # Normalize a few common unicode chars
    return (
        s.replace("–", "-").replace("—", "-").replace("•", "-")
         .replace("’", "'").replace("“", '"').replace("”", '"')
         .encode("latin-1", "replace").decode("latin-1")
    )

def generate_pdf(job: dict) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "TileIntel — Method Statement (MVP)", ln=1)
    pdf.ln(2)

    # Body font
    pdf.set_font("Helvetica", "", 11)

    # Calculate safe column widths
    page_w = pdf.w         # total page width
    l_mar = pdf.l_margin   # left margin
    r_mar = pdf.r_margin   # right margin
    usable_w = page_w - l_mar - r_mar
    label_w = 40           # left column width (label)
    gap = 4                # spacing between columns
    value_w = max(10, usable_w - label_w - gap)  # ensure positive width

    def row(label: str, value: str):
        # Always reset X to left margin before drawing
        pdf.set_x(l_mar)
        # Draw label (single line)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(label_w, 6, _to_ascii(label), ln=0)
        # Draw value (multi-line, wraps within available width)
        pdf.set_font("Helvetica", "", 11)
        # Make sure X is exactly after the label + gap
        pdf.set_x(l_mar + label_w + gap)
        txt = _to_ascii(value if value is not None else "")
        # If a word is ridiculously long, insert soft breaks to avoid the single-char error
        txt = _hard_wrap(txt, value_w, pdf)
        pdf.multi_cell(value_w, 6, txt)
        pdf.ln(1)

    def _hard_wrap(text: str, target_w: float, _pdf: FPDF) -> str:
        """
        Very long unbroken strings (like 200-char filenames) can still break FPDF.
        This inserts soft breaks on long tokens so every token can fit.
        """
        words = text.split()
        out = []
        for w in words:
            # if a single word is wider than the column, split it
            while _pdf.get_string_width(w) > target_w and len(w) > 1:
                # binary chop approx
                cut = max(1, int(len(w) * target_w / (_pdf.get_string_width(w) + 0.001)))
                out.append(w[:cut])
                w = w[cut:]
            out.append(w)
        return " ".join(out)

    # ---- Rows (example – adapt fields to yours) ----
    row("Project", job.get("project_desc", ""))
    row("Room", job.get("room", ""))
    row("Area (m²)", str(job.get("area_m2", "")))
    row("Tile size (mm)", f"{job.get('tile_w', '')} x {job.get('tile_h', '')}")
    row("Thickness (mm)", str(job.get("tile_t", "")))
    row("Substrate", job.get("substrate", ""))
    row("UFH", "Yes" if job.get("ufh") else "No")
    row("Adhesive", job.get("adhesive", ""))
    row("Grout", job.get("grout", ""))

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Calculated Materials", ln=1)
    pdf.set_font("Helvetica", "", 11)
    row("Tiles needed (pcs)", str(job.get("calc_tiles_pcs", "")))
    row("Adhesive (kg)", str(job.get("calc_adhesive_kg", "")))
    row("Grout (kg)", str(job.get("calc_grout_kg", "")))
    row("Primer (L)", str(job.get("calc_primer_l", "")))
    row("Levelling compound (bags)", str(job.get("calc_screed_bags", "")))

    # Notes
    notes = job.get("notes", "")
    if notes:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Notes", ln=1)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_x(l_mar)
        pdf.multi_cell(usable_w, 6, _to_ascii(notes))

    return pdf.output(dest="S").encode("latin-1", "replace")
