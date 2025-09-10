"""
Flask server for Neurokit2 ECG Analysis
Provides REST API endpoints for ECG analysis functionality.
"""

import os
import tempfile
import traceback
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from neurokit_ecg_analysis import NeuroKit2ECGAnalyzer, analyze_ecg_file
import json

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
UPLOAD_FOLDER = tempfile.mkdtemp()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'ecg', 'bin', 'dat', 'csv', 'txt'}

# Global analyzer instance
analyzer = None

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the Neurokit2 analysis page."""
    return render_template_string(NEUROKIT_HTML_TEMPLATE)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and initial analysis."""
    global analyzer
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Get analysis parameters
        sampling_rate = int(request.form.get('sampling_rate', 200))
        num_leads = int(request.form.get('num_leads', 3))
        uv_per_lsb = float(request.form.get('uv_per_lsb', 1.0))
        lead_index = int(request.form.get('lead_index', 0))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Analyze the file
        results = analyze_ecg_file(
            file_path=file_path,
            sampling_rate=sampling_rate,
            num_leads=num_leads,
            uv_per_lsb=uv_per_lsb,
            lead_index=lead_index
        )
        
        if results['success']:
            # Store analyzer instance for further operations
            analyzer = results.pop('analyzer', None)
            
            # Clean up the file
            os.remove(file_path)
            
            return jsonify(results)
        else:
            # Clean up the file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify(results), 500
            
    except Exception as e:
        return jsonify({
            'error': f'Upload processing error: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Perform specific analysis on loaded ECG data."""
    global analyzer
    
    if analyzer is None:
        return jsonify({'error': 'No ECG data loaded. Please upload a file first.'}), 400
    
    try:
        data = request.get_json()
        analysis_type = data.get('type', 'hrv')
        lead_index = data.get('lead_index', 0)
        
        if analysis_type == 'hrv':
            results = analyzer.get_hrv_analysis()
            return jsonify({
                'success': True,
                'analysis_type': 'hrv',
                'results': results.to_dict('records')[0] if not results.empty else {}
            })
        
        elif analysis_type == 'arrhythmia':
            results = analyzer.detect_arrhythmia()
            return jsonify({
                'success': True,
                'analysis_type': 'arrhythmia',
                'results': results
            })
        
        elif analysis_type == 'summary':
            results = analyzer.get_summary_report()
            return jsonify({
                'success': True,
                'analysis_type': 'summary',
                'results': results
            })
        
        else:
            return jsonify({'error': f'Unknown analysis type: {analysis_type}'}), 400
            
    except Exception as e:
        return jsonify({
            'error': f'Analysis error: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/plot', methods=['POST'])
def generate_plot():
    """Generate specific plot for loaded ECG data."""
    global analyzer
    
    if analyzer is None:
        return jsonify({'error': 'No ECG data loaded. Please upload a file first.'}), 400
    
    try:
        data = request.get_json()
        plot_type = data.get('type', 'overview')
        lead_index = data.get('lead_index', 0)
        duration = data.get('duration', None)
        
        plot_base64 = analyzer.generate_plot(plot_type, lead_index, duration)
        
        return jsonify({
            'success': True,
            'plot_type': plot_type,
            'plot_data': plot_base64
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Plot generation error: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/process', methods=['POST'])
def process_ecg():
    """Process ECG with different parameters."""
    global analyzer
    
    if analyzer is None:
        return jsonify({'error': 'No ECG data loaded. Please upload a file first.'}), 400
    
    try:
        data = request.get_json()
        lead_index = data.get('lead_index', 0)
        method = data.get('method', 'neurokit')
        
        results = analyzer.process_ecg(lead_index, method)
        
        # Convert numpy arrays to lists for JSON serialization
        serializable_results = {}
        for key, value in results.items():
            if hasattr(value, 'tolist'):
                serializable_results[key] = value.tolist()
            elif hasattr(value, 'to_dict'):
                serializable_results[key] = value.to_dict('records')
            else:
                serializable_results[key] = value
        
        return jsonify({
            'success': True,
            'processing_method': method,
            'lead_index': lead_index,
            'results': serializable_results
        })
        
    except Exception as e:
        return jsonify({
            'error': f'ECG processing error: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'neurokit2-ecg-analyzer'})

# HTML template for the Neurokit2 analysis interface
NEUROKIT_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neurokit2 ECG Analysis</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
        }
        
        .header h1 {
            color: #4a5568;
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .header p {
            color: #718096;
            font-size: 1.1em;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        .card h2 {
            color: #2d3748;
            margin-bottom: 20px;
            font-size: 1.4em;
            font-weight: 400;
        }
        
        .upload-area {
            border: 3px dashed #cbd5e0;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background-color: #f8faff;
        }
        
        .upload-area.dragover {
            border-color: #667eea;
            background-color: #e6f3ff;
        }
        
        .file-input {
            display: none;
        }
        
        .upload-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            margin: 10px 5px;
            transition: all 0.3s ease;
        }
        
        .upload-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .btn {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            margin: 5px;
            transition: all 0.3s ease;
        }
        
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        }
        
        .btn:disabled {
            background: #cbd5e0;
            cursor: not-allowed;
            transform: none;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #4a5568;
        }
        
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .results-container {
            display: none;
        }
        
        .results-container.show {
            display: block;
        }
        
        .plot-container {
            text-align: center;
            margin: 20px 0;
        }
        
        .plot-container img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .analysis-summary {
            background: #f7fafc;
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid #667eea;
        }
        
        .metric {
            display: inline-block;
            background: white;
            padding: 15px;
            margin: 5px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            min-width: 150px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        
        .metric-label {
            color: #718096;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 4px solid #e53e3e;
        }
        
        .success {
            background: #c6f6d5;
            color: #276749;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 4px solid #48bb78;
        }
        
        .back-button {
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.9);
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            z-index: 1000;
        }
        
        .back-button:hover {
            background: white;
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
        }
    </style>
</head>
<body>
    <button class="back-button" onclick="goBack()">← Back to ECG Explorer</button>
    
    <div class="container">
        <div class="header">
            <h1>🧠 Neurokit2 ECG Analysis</h1>
            <p>Advanced ECG analysis powered by Neurokit2 machine learning algorithms</p>
        </div>

        <div class="card">
            <h2>📁 Upload ECG File</h2>
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <p>Click here to select ECG file or drag and drop</p>
                <p style="color: #718096; margin-top: 10px;">Supported formats: .ecg, .bin, .dat, .csv, .txt</p>
                <input type="file" id="fileInput" class="file-input" accept=".ecg,.bin,.dat,.csv,.txt">
                <button class="upload-button">Choose File</button>
            </div>
            
            <div class="form-row" style="margin-top: 20px;">
                <div class="form-group">
                    <label for="samplingRate">Sampling Rate (Hz):</label>
                    <input type="number" id="samplingRate" value="200" min="1" max="10000">
                </div>
                <div class="form-group">
                    <label for="numLeads">Number of Leads:</label>
                    <input type="number" id="numLeads" value="3" min="1" max="12">
                </div>
                <div class="form-group">
                    <label for="uvPerLsb">µV per LSB:</label>
                    <input type="number" id="uvPerLsb" value="1" min="0.1" step="0.1">
                </div>
                <div class="form-group">
                    <label for="leadIndex">Lead to Analyze:</label>
                    <select id="leadIndex">
                        <option value="0">Lead 1</option>
                        <option value="1">Lead 2</option>
                        <option value="2">Lead 3</option>
                    </select>
                </div>
            </div>
            
            <button class="btn" onclick="uploadAndAnalyze()" id="analyzeBtn" disabled>
                Analyze ECG <span id="loadingSpinner" class="loading" style="display: none;"></span>
            </button>
        </div>

        <div class="results-container" id="resultsContainer">
            <div class="card">
                <h2>📊 Analysis Results</h2>
                <div id="analysisResults"></div>
            </div>

            <div class="card">
                <h2>📈 Visualizations</h2>
                <div class="form-row">
                    <button class="btn" onclick="generatePlot('overview')">Original Signal</button>
                    <button class="btn" onclick="generatePlot('processed')">Processed ECG</button>
                    <button class="btn" onclick="generatePlot('hrv')">HRV Analysis</button>
                </div>
                <div class="plot-container" id="plotContainer"></div>
            </div>

            <div class="card">
                <h2>🔬 Advanced Analysis</h2>
                <div class="form-row">
                    <button class="btn" onclick="performAnalysis('hrv')">HRV Analysis</button>
                    <button class="btn" onclick="performAnalysis('arrhythmia')">Arrhythmia Detection</button>
                    <button class="btn" onclick="performAnalysis('summary')">Complete Summary</button>
                </div>
                <div id="advancedResults"></div>
            </div>
        </div>
    </div>

    <script>
        let currentFile = null;

        function goBack() {
            // Go back to the main ECG Explorer page
            window.location.href = 'index.html';
        }

        // File upload handling
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                currentFile = file;
                document.getElementById('analyzeBtn').disabled = false;
                showMessage(`File selected: ${file.name}`, 'success');
            }
        });

        // Drag and drop functionality
        const uploadArea = document.querySelector('.upload-area');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                currentFile = files[0];
                document.getElementById('fileInput').files = files;
                document.getElementById('analyzeBtn').disabled = false;
                showMessage(`File selected: ${files[0].name}`, 'success');
            }
        });

        function showMessage(message, type) {
            const resultDiv = document.getElementById('analysisResults') || document.getElementById('advancedResults') || uploadArea;
            const messageDiv = document.createElement('div');
            messageDiv.className = type;
            messageDiv.textContent = message;
            resultDiv.appendChild(messageDiv);
            setTimeout(() => messageDiv.remove(), 5000);
        }

        function showLoading(show) {
            document.getElementById('loadingSpinner').style.display = show ? 'inline-block' : 'none';
        }

        async function uploadAndAnalyze() {
            if (!currentFile) {
                showMessage('Please select a file first', 'error');
                return;
            }

            showLoading(true);
            document.getElementById('analyzeBtn').disabled = true;

            const formData = new FormData();
            formData.append('file', currentFile);
            formData.append('sampling_rate', document.getElementById('samplingRate').value);
            formData.append('num_leads', document.getElementById('numLeads').value);
            formData.append('uv_per_lsb', document.getElementById('uvPerLsb').value);
            formData.append('lead_index', document.getElementById('leadIndex').value);

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    displayResults(result);
                    document.getElementById('resultsContainer').classList.add('show');
                    showMessage('ECG analysis completed successfully!', 'success');
                } else {
                    showMessage(`Analysis failed: ${result.error}`, 'error');
                }
            } catch (error) {
                showMessage(`Network error: ${error.message}`, 'error');
            } finally {
                showLoading(false);
                document.getElementById('analyzeBtn').disabled = false;
            }
        }

        function displayResults(result) {
            const resultsDiv = document.getElementById('analysisResults');
            
            if (result.summary_report && result.summary_report.file_info) {
                const fileInfo = result.summary_report.file_info;
                const processing = result.summary_report.processing || {};
                
                resultsDiv.innerHTML = `
                    <div class="analysis-summary">
                        <h3>📋 File Information</h3>
                        <div class="metric">
                            <div class="metric-value">${fileInfo.duration_seconds.toFixed(1)}</div>
                            <div class="metric-label">Duration (s)</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${fileInfo.sampling_rate}</div>
                            <div class="metric-label">Sampling Rate (Hz)</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${fileInfo.num_leads}</div>
                            <div class="metric-label">Number of Leads</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${processing.r_peaks_detected || 0}</div>
                            <div class="metric-label">R-peaks Detected</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${(processing.average_heart_rate || 0).toFixed(1)}</div>
                            <div class="metric-label">Avg HR (bpm)</div>
                        </div>
                    </div>
                `;
            }

            // Display plots if available
            if (result.plots) {
                const plotContainer = document.getElementById('plotContainer');
                if (result.plots.overview) {
                    plotContainer.innerHTML = `<img src="${result.plots.overview}" alt="ECG Overview">`;
                }
            }
        }

        async function generatePlot(plotType) {
            showLoading(true);

            try {
                const response = await fetch('/api/plot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        type: plotType,
                        lead_index: parseInt(document.getElementById('leadIndex').value),
                        duration: plotType === 'hrv' ? null : 30
                    })
                });

                const result = await response.json();

                if (result.success) {
                    const plotContainer = document.getElementById('plotContainer');
                    plotContainer.innerHTML = `<img src="${result.plot_data}" alt="${plotType} plot">`;
                } else {
                    showMessage(`Plot generation failed: ${result.error}`, 'error');
                }
            } catch (error) {
                showMessage(`Network error: ${error.message}`, 'error');
            } finally {
                showLoading(false);
            }
        }

        async function performAnalysis(analysisType) {
            showLoading(true);

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        type: analysisType,
                        lead_index: parseInt(document.getElementById('leadIndex').value)
                    })
                });

                const result = await response.json();

                if (result.success) {
                    displayAdvancedResults(result);
                } else {
                    showMessage(`Analysis failed: ${result.error}`, 'error');
                }
            } catch (error) {
                showMessage(`Network error: ${error.message}`, 'error');
            } finally {
                showLoading(false);
            }
        }

        function displayAdvancedResults(result) {
            const resultsDiv = document.getElementById('advancedResults');
            
            let html = `<div class="analysis-summary">`;
            html += `<h3>🔬 ${result.analysis_type.toUpperCase()} Analysis Results</h3>`;
            
            if (result.analysis_type === 'hrv') {
                const hrv = result.results;
                html += `
                    <div class="metric">
                        <div class="metric-value">${(hrv.HRV_RMSSD || 0).toFixed(2)}</div>
                        <div class="metric-label">RMSSD (ms)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${(hrv.HRV_SDNN || 0).toFixed(2)}</div>
                        <div class="metric-label">SDNN (ms)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${(hrv.HRV_pNN50 || 0).toFixed(2)}</div>
                        <div class="metric-label">pNN50 (%)</div>
                    </div>
                `;
            } else if (result.analysis_type === 'arrhythmia') {
                const arr = result.results;
                html += `
                    <div class="metric">
                        <div class="metric-value">${arr.mean_heart_rate.toFixed(1)}</div>
                        <div class="metric-label">Mean HR (bpm)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${arr.total_beats}</div>
                        <div class="metric-label">Total Beats</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${arr.bradycardia ? 'Yes' : 'No'}</div>
                        <div class="metric-label">Bradycardia</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${arr.tachycardia ? 'Yes' : 'No'}</div>
                        <div class="metric-label">Tachycardia</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${arr.irregular_rhythm ? 'Yes' : 'No'}</div>
                        <div class="metric-label">Irregular Rhythm</div>
                    </div>
                `;
            } else if (result.analysis_type === 'summary') {
                // Display comprehensive summary
                html += '<div style="text-align: left; padding: 20px;">';
                html += '<pre>' + JSON.stringify(result.results, null, 2) + '</pre>';
                html += '</div>';
            }
            
            html += '</div>';
            resultsDiv.innerHTML = html;
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("Starting Neurokit2 ECG Analysis Server...")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)