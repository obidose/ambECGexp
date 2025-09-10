# 🧠 Neurokit2 ECG Analysis Integration

This integration adds advanced ECG analysis capabilities to the ECG Explorer using the Neurokit2 Python library. The functionality is completely modularized and runs as a separate service to avoid impacting the main JavaScript application.

## ✨ Features

### Advanced ECG Analysis
- **Signal Processing**: Advanced filtering, baseline correction, and noise reduction using Neurokit2 algorithms
- **R-peak Detection**: Multiple algorithms (Neurokit, Pan-Tompkins, Hamilton2016, etc.)
- **Heart Rate Variability (HRV)**: Comprehensive HRV analysis including time-domain and frequency-domain metrics
- **Arrhythmia Detection**: Basic arrhythmia screening including bradycardia, tachycardia, and rhythm irregularities

### Visualization & Reporting
- **Interactive Plots**: Original signal, processed ECG with R-peaks, HRV analysis plots
- **Comprehensive Reports**: Detailed analysis summaries with clinical metrics
- **Real-time Analysis**: Process ECG files and get immediate results

### File Format Support
- **Binary Files**: `.ecg`, `.bin`, `.dat` (same format as main application)
- **Text Files**: `.csv`, `.txt` with numeric data
- **Flexible Parameters**: Configurable sampling rate, number of leads, and scaling factors

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Install required Python packages
pip3 install neurokit2 flask flask-cors numpy pandas matplotlib
```

### 2. Start the Neurokit2 Server
```bash
# Option A: Use the startup script (recommended)
python3 start_neurokit_server.py

# Option B: Start server directly
python3 neurokit_server.py
```

### 3. Access from ECG Explorer
1. Open ECG Explorer in your browser (`index.html`)
2. Click the **🧠 NK2** button in the top toolbar
3. The Neurokit2 analysis interface will open in a new tab

## 📋 Usage Instructions

### Basic Workflow
1. **Upload ECG File**: Click or drag-and-drop your ECG file
2. **Configure Parameters**: Set sampling rate, number of leads, and other parameters
3. **Analyze**: Click "Analyze ECG" to process the file
4. **Explore Results**: View plots, HRV analysis, and arrhythmia detection
5. **Advanced Analysis**: Use the additional analysis buttons for detailed reports

### Parameters Configuration
- **Sampling Rate (Hz)**: ECG sampling frequency (default: 200 Hz)
- **Number of Leads**: Total leads in the file (default: 3 for V1, V3, V5)
- **µV per LSB**: Scaling factor for binary files (default: 1.0)
- **Lead to Analyze**: Which lead to process (0-based index)

### Analysis Types
- **HRV Analysis**: Heart rate variability metrics (RMSSD, SDNN, pNN50, etc.)
- **Arrhythmia Detection**: Basic screening for common arrhythmias
- **Complete Summary**: Comprehensive report with all available metrics

## 🔧 Technical Details

### Architecture
```
ECG Explorer (Frontend)     Neurokit2 Server (Backend)
├── index.html              ├── neurokit_server.py
├── script.js               ├── neurokit_ecg_analysis.py
├── styles.css              └── start_neurokit_server.py
└── 🧠 NK2 Button ─────────────► HTTP API Calls
```

### API Endpoints
- `POST /api/upload` - Upload and analyze ECG file
- `POST /api/analyze` - Perform specific analysis (HRV, arrhythmia, summary)
- `POST /api/plot` - Generate visualization plots
- `POST /api/process` - Process ECG with different algorithms
- `GET /health` - Server health check

### File Structure
```
neurokit_ecg_analysis.py    # Core analysis module (completely modular)
neurokit_server.py          # Flask web server and API
start_neurokit_server.py    # Convenience startup script
NEUROKIT2_README.md         # This documentation
```

## 🧪 Supported Analysis Methods

### ECG Processing Methods
- **neurokit** (default): Neurokit2's optimized algorithm
- **pantompkins**: Classical Pan-Tompkins algorithm
- **hamilton2016**: Hamilton & Tompkins 2016 method
- **christov**: Christov algorithm
- **engzeemod**: Modified Engzee algorithm

### HRV Metrics
- **Time Domain**: RMSSD, SDNN, pNN50, HR statistics
- **Frequency Domain**: LF, HF, LF/HF ratio (when applicable)
- **Nonlinear**: Poincaré plot analysis

### Arrhythmia Indicators
- **Bradycardia**: Heart rate < 60 bpm
- **Tachycardia**: Heart rate > 100 bpm
- **Irregular Rhythm**: High RR interval variability
- **Beat Statistics**: Total beats, mean RR intervals

## 🛠️ Troubleshooting

### Server Won't Start
- **Missing Dependencies**: Run `pip3 install neurokit2 flask flask-cors numpy pandas matplotlib`
- **Python Version**: Ensure Python 3.7+ is installed
- **Port Conflict**: Check if port 5000 is already in use

### Analysis Errors
- **File Format**: Ensure ECG file is in supported format (.ecg, .csv, .txt)
- **Parameters**: Verify sampling rate and lead count match your file
- **File Size**: Large files (>50MB) may take longer to process

### Connection Issues
- **Server Status**: Check if server is running at http://localhost:5000
- **Browser Blocking**: Some browsers block localhost requests; try Chrome/Firefox
- **Firewall**: Ensure local connections to port 5000 are allowed

## 🔒 Privacy & Security

- **No Data Storage**: ECG files are processed in memory and deleted after analysis
- **Local Processing**: All analysis runs locally on your machine
- **No Internet Required**: Works completely offline once dependencies are installed
- **Temporary Files**: Uploaded files are automatically cleaned up

## 📚 References

- **Neurokit2**: [https://neurokit2.readthedocs.io/](https://neurokit2.readthedocs.io/)
- **ECG Processing**: Makowski, D. et al. (2021). NeuroKit2: A Python toolbox for neurophysiological signal processing
- **Pan-Tompkins**: Pan, J., & Tompkins, W. J. (1985). A real-time QRS detection algorithm

## 🤝 Contributing

The Neurokit2 integration is designed to be completely modular. To extend functionality:

1. **Add new analysis methods** in `neurokit_ecg_analysis.py`
2. **Create new API endpoints** in `neurokit_server.py`
3. **Update the web interface** by modifying the HTML template
4. **Test thoroughly** with various ECG file formats

## ⚠️ Disclaimer

This tool is for **research and educational purposes only**. It is not a medical device and should not be used for clinical diagnosis or patient care. Always consult qualified healthcare professionals for medical decisions.