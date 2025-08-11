from fpdf import FPDF

def _to_ascii(s: str) -> str:
    if s is None:
        return ""
    return (
        s.replace("–", "-").replace("—", "-").replace("•", "-")
         .replace("’", "'").replace("“", '"').replace("”", '"')
         .encode("latin-1", "replace").decode("latin-1")
    )

def _soft_wrap_tokens(text: str, target_w: float, pdf: FPDF) -> str:
    """Split tokens that are wider than target_w so fpdf can render them."""
    words = text.split()
    out = []
    for w in words:
        if not w:
            continue
        while pdf.get_string_width(w) > target_w and len(w) > 1:
            # cut proportionally
            cut = max(1, int(len(w) * target_w / (pdf.get_string_width(w) + 0.001)))
            out.append(w[:cut])
            w = w[cut:]
        out.append(w)
    return " ".join(out)

def generate_pdf(job: dict) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_top_margin(15)
    pdf.add_page()

    # Fonts & padding
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_font_size(16)
    pdf.cell(0, 10, "TileIntel — Method Statement (MVP)", ln=1)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_font_size(10)
    pdf.set_cell_padding(0.6)  # helps with very narrow widths

    # Effective page width
    usable_w = pdf.epw  # fpdf2: page width - left/right margins
    l_mar = pdf.l_margin
    r_mar = pdf.r_margin

    # Column layout
    gap = 4
    label_w = min(48, max(32, usable_w * 0.38))
    value_w = usable_w - label_w - gap

    # MIN width for multi_cell: at least padding + a glyph width
    min_value_w = pdf.c_margin * 2 + pdf.get_string_width("W") + 0.5
    if value_w < min_value_w:
        # if the layout is somehow too tight, widen label/value split
        label_w = max(28, usable_w * 0.30)
        value_w = usable_w - label_w - gap

    def row(label: str, value: str):
        """Render a key/value row; fallback to full-width if too narrow."""
        label_txt = _to_ascii(label or "")
        raw_val = _to_ascii(value or "")
        x_left = l_mar

        # Always start from left margin
        pdf.set_x(x_left)

        # If the value column is still too small, switch to stacked layout
        if value_w < min_value_w:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, label_txt, ln=1)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_x(x_left)
            wrapped = _soft_wrap_tokens(raw_val, usable_w - pdf.c_margin * 2, pdf)
            pdf.multi_cell(usable_w, 6, wrapped)
            pdf.ln(1)
            return

        # Two-column layout
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w, 6, label_txt, ln=0)

        pdf.set_font("Helvetica", "", 10)
        # align X for value
        pdf.set_x(x_left + label_w + gap)
        wrapped = _soft_wrap_tokens(raw_val, value_w - pdf.c_margin * 2, pdf)
        pdf.multi_cell(value_w, 6, wrapped)
        pdf.ln(1)

    # ---- Content ----
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
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Calculated Materials", ln=1)
    pdf.set_font("Helvetica", "", 10)
    row("Tiles needed (pcs)", str(job.get("calc_tiles_pcs", "")))
    row("Adhesive (kg)", str(job.get("calc_adhesive_kg", "")))
    row("Grout (kg)", str(job.get("calc_grout_kg", "")))
    row("Primer (L)", str(job.get("calc_primer_l", "")))
    row("Levelling compound (bags)", str(job.get("calc_screed_bags", "")))

    notes = job.get("notes", "")
    if notes:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Notes", ln=1)
        pdf.set_font("Helvetica", "", 10)
        wrapped_notes = _soft_wrap_tokens(_to_ascii(notes), usable_w - pdf.c_margin * 2, pdf)
        pdf.multi_cell(usable_w, 6, wrapped_notes)

    return pdf.output(dest="S").encode("latin-1", "replace")
