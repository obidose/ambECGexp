# ECG Explorer – Stable v1

A minimal, single-page ECG viewer for the browser:
- Load binary `.ecg/.bin` (16-bit **little-endian**, *interleaved* leads) or CSV.
- Controls: `fs` (Hz), `uV/LSB`, window length, lead height, baseline, gains.
- HR estimation (robust) + overview HR trend.
- Time and voltage calipers. Print-friendly.

## Local run
Open `index.html` in a modern browser (Chrome/Edge/Firefox).

## Deploy to GitHub Pages
1. Create a new repo (e.g., `ecg-explorer`).
2. In the unzipped folder:
   ```bash
   git init
   git add .
   git commit -m "init: ECG Explorer stable v1"
   git branch -M main
   git remote add origin git@github.com:<YOUR_USERNAME>/ecg-explorer.git
   git push -u origin main
   ```
3. On GitHub → **Settings → Pages → Source: “Deploy from a branch”** → Branch **main** / **/** (root).

## File formats
- **Binary**: 16‑bit signed little‑endian, *interleaved per lead* (L0,L1,L2,L0,L1,L2,…). Set **Leads** to your channel count. `uV/LSB` scales to mV.
- **CSV**: numeric columns = leads; assumed mV already.

## Defaults
fs=200 Hz, uV/LSB=2, leads=3 (V1,V3,V5).
