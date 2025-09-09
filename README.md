# ECG Explorer

A fast, lightweight ECG viewer that runs entirely in your browser.  
Load long recordings, pan/zoom smoothly, visualize heart rate, and measure with precision calipers — no server required.

> **Clean, minimal interface** optimized for essential ECG analysis tasks.

---

## ✨ Features

- **File support**
  - **Binary**: 16‑bit signed **little‑endian**, *interleaved per sample* (L0,L1,L2, L0,L1,L2, …).
  - **CSV/TXT**: numeric columns = leads (values assumed in **mV**).
- **Multi‑row ECG display** with automatic splitting for long time windows
- **Real-time heart rate visualization** synchronized across all ECG rows  
- **Multi-lead support** (V1, V3, V5) with individual lead toggles
- **Precision measurement tools**
  - **Time calipers** (Δt in ms, with bpm calculation)
  - **Voltage calipers** (ΔV in mV) with lane awareness
- **Smart navigation**
  - Mouse-centered zoom with smooth layout transitions
  - Drag-to-pan, overview navigator with zoom capability
  - Scroll bar for quick positioning
- **Professional themes** (Dark, Light, Ocean, ECG Paper, Mint, Sunset, Purple)
- **Advanced signal processing** 
  - Baseline correction and filtering (configurable in advanced settings)
  - Robust HR detection with outlier rejection
- **Clean, minimal interface** 
  - Essential controls visible, advanced options in settings dialogs
  - Device properties (sampling rate, voltage scaling) in dedicated panel
- **Complete privacy** - 100% client-side processing

---

## 🚀 Getting started

1. Open `index.html` in any modern web browser
2. Click the **📁** button for demo files, or use **Choose File** to load your ECG data
3. Configure device properties using the **⚙️** button if needed (sampling rate, voltage scaling)
4. Use the **⚡** button for advanced HR settings if required
5. Navigate with mouse wheel (zoom), drag (pan), or the overview bar

---

## 🗂️ File formats

### Binary (`.ecg`, `.bin`, `.dat`)
- **Encoding**: 16‑bit signed integers, **little‑endian**.
- **Layout**: **interleaved per sample** across leads:
  ```text
  s0L0, s0L1, s0L2,  s1L0, s1L1, s1L2,  …
  ```
- **Controls to set**
  - **Leads**: number of channels in the file.
  - **fs (Hz)**: sampling rate (e.g., **200**).
  - **uV/LSB**: hardware scale (e.g., **1** → each integer step = 1 µV).
  - Values are converted to **mV** for plotting and calipers.

### CSV/TXT
- **Columns**: one numeric column per lead; **assumed mV**.
- Non‑numeric rows are skipped.

---

## 🎛️ Controls (top bar)

- **File**: open binary `.ecg/.bin/.dat` or `.csv/.txt`.
- **Leads**: total leads in the file (used for binary interleaving).
- **fs (Hz)**: sampling frequency.
- **uV/LSB**: hardware gain (binary only).
- **Window (s)**: visible time span.
- **Lead height (%)**: vertical lane fill (avoids overlap).
- **Auto‑gain**: auto scale amplitudes to fit lanes.
- **Gain mode**:
  - **Global**: same gain for all visible leads.
  - **Per‑lead**: independent gain per lane.
- **Show HR**: toggle the window HR pane.
- **Lock HR scale**: use a global range (from the overview) so HR doesn’t “jump” between windows.
- **HR smooth (beats)**: moving average length for HR.
- **Robust HR**: enable outlier rejection; good for exercise/artefact.
- **Outlier tol (%)**: deviation allowed (e.g., ±30% of local median).
- **Baseline**: *None* or **High‑pass 0.5 Hz**.
- **Calipers**: tool selector (Pan / Time / Voltage).
- **1s scale bar**: toggle the 1‑second scale in the main pane.
- **Lead toggles**: show/hide V1, V3, V5.
- **Theme**: Dark / ECG paper.
- **Open sample**: generates a synthetic 3‑lead rhythm for testing.
- **Reset view**: back to start with the current window length.
- **Print**: opens the browser print dialog.

---

## 🖱️ Mouse & keyboard

- **Pan**: drag on the ECG (Pan tool active).
- **Zoom**: mouse **wheel** (cursor‑centered).
- **Jump**: click/drag in the **overview** bar.
- **Overview zoom**: wheel over the overview bar (double‑click to reset).
- **Time calipers**: **Shift + drag** (or select **Time** tool).
  - Shows **Δt (ms)** and **≈ bpm** (assuming RR).
- **Voltage calipers**: **Ctrl + drag** (or select **Voltage** tool).
  - Lane‑aware **ΔV (mV)** between two horizontal lines.

---

## ❤️ Heart‑rate estimation

- Detector is a Pan‑Tompkins–style variant:
  - Differentiate → square → short moving integration → adaptive threshold.
  - Local refractory to avoid double‑counting.
- RR → bpm for successive beats; **robust mode** discards outliers relative to local median.
- **HR smooth** averages last *N* beats (use 5–7 for exercise).
- **Lock HR scale** keeps a fixed y‑range derived from the **overview** so comparisons are meaningful across windows.

> Tip: noisy sections can still show a stable overview trend; lock the HR scale for consistent context.

---

## 📏 Scales & calibration

- Grid: **0.04 s minor / 0.20 s major**; **0.1 mV minor / 0.5 mV major**.
- Per‑lead calibration box: **1 mV × 200 ms** near the left of each lane.
- With **Auto‑gain off**, the lane baseline uses standard 10 mm/mV proportions.

---

## 🖨️ Printing

- Use the **Print** button (or `Ctrl/Cmd+P`).
- The print stylesheet hides controls and overview for a clean plot.  
  Switch to **ECG paper** theme before printing if you want traditional look.

---

## 🧰 Troubleshooting

**Nothing draws after loading**  
- Check **Leads** is correct for your binary file (3 for V1/V3/V5).  
- Confirm **fs** (e.g., **200 Hz**) and **uV/LSB** (**1**).  
- If CSV, ensure values are numeric and in **mV**.

**ECG amplitude looks wrong**  
- Binary: adjust **uV/LSB** until the 1 mV calibration matches the grid.  
- Try toggling **Auto‑gain** or switching **Gain mode**.

**Baseline “waves” at big zoom‑outs**  
- Use **Baseline → High‑pass 0.5 Hz**.  
- Reduce **Window (s)** or zoom in for truer morphology.

**HR is jumpy**  
- Enable **Robust HR**, increase **HR smooth** (e.g., 5–7), and tighten **Outlier tol** (20–30%).  
- **Lock HR scale** to stabilize the y‑axis.

**Overview HR doesn’t match window HR**  
- The overview is computed across the whole recording. Once it completes, **Lock HR scale** to unify ranges.

---

## 🧭 Roadmap

- SQI (signal‑quality index) overlay in both HR panes.
- Overview HR fusion using **median of all recorded leads** regardless of visibility.
- 12‑lead support and lead renaming.
- Annotations & measurements export (CSV/PDF).
- Session share links and theming presets.

---

## 🧪 Development & deploy

Project structure:
```text
index.html    # UI shell and controls
styles.css    # Themes and ECG paper styles
script.js     # Rendering, HR detection, calipers, overview
```

Run locally — just open `index.html`.

Deploy to **GitHub Pages**:
```bash
git init
git add .
git commit -m "init: ECG Explorer stable v1"
git branch -M main
git remote add origin git@github.com:<YOUR_USERNAME>/ecg-explorer.git
git push -u origin main
# GitHub → Settings → Pages → Source: Deploy from a branch (main / /)
```

---

---

## ⚠️ Disclaimer

This tool is for **engineering and research** use only and **not** a medical device.  
Do not use for diagnosis or patient management.
