# TileIntel — Streamlit MVP

This is a minimal, working MVP for TileIntel built with **Streamlit** + **FPDF**.

## Features
- Input job specs (area, tile size, substrate, UFH, adhesive, grout)
- Auto-calculated materials (primer, adhesive, grout, levelling)
- Generate a branded PDF method statement
- Upload plans/images (stored in-session only, not saved)

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud
1. Create a new **public GitHub repo** and upload `app.py` + `requirements.txt`.
2. Go to https://share.streamlit.io/ and **New app**.
3. Pick your repo, branch (main), and set **entrypoint** to `app.py`.
4. Click **Deploy** — your app will build, then you'll get a `.streamlit.app` URL.
5. In **App Settings → Custom Domain**, map it to `www.tileintel.com` or a subdomain.
