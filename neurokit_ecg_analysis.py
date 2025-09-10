"""
Neurokit2 ECG Analysis Module
Provides modular ECG analysis functionality using Neurokit2 library.
"""

import os
import numpy as np
import pandas as pd
import neurokit2 as nk
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import io
import base64
import struct
import csv
from typing import Tuple, Dict, Optional, List, Union


class NeuroKit2ECGAnalyzer:
    """
    A modular ECG analyzer using Neurokit2 library.
    Handles various ECG file formats and provides comprehensive analysis.
    """
    
    def __init__(self, sampling_rate: int = 200):
        """
        Initialize the ECG analyzer.
        
        Args:
            sampling_rate (int): Default sampling rate in Hz
        """
        self.sampling_rate = sampling_rate
        self.ecg_signal = None
        self.processed_ecg = None
        self.analysis_results = {}
        
    def load_ecg_binary(self, file_path: str, num_leads: int = 3, 
                       sampling_rate: int = 200, uv_per_lsb: float = 1.0) -> np.ndarray:
        """
        Load ECG data from binary format (.ecg, .bin, .dat files).
        
        Args:
            file_path (str): Path to the binary ECG file
            num_leads (int): Number of ECG leads in the file
            sampling_rate (int): Sampling rate in Hz
            uv_per_lsb (float): Microvolts per LSB for scaling
            
        Returns:
            np.ndarray: ECG data array (samples x leads)
        """
        self.sampling_rate = sampling_rate
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Convert to 16-bit signed integers (little-endian)
        num_samples = len(data) // (2 * num_leads)
        raw_data = struct.unpack(f'<{num_samples * num_leads}h', data)
        
        # Reshape to (samples, leads) and convert to mV
        ecg_data = np.array(raw_data).reshape(-1, num_leads)
        self.ecg_signal = ecg_data * (uv_per_lsb / 1000.0)  # Convert µV to mV
        
        return self.ecg_signal
    
    def load_ecg_csv(self, file_path: str, sampling_rate: int = 200) -> np.ndarray:
        """
        Load ECG data from CSV/TXT format.
        
        Args:
            file_path (str): Path to the CSV/TXT ECG file
            sampling_rate (int): Sampling rate in Hz
            
        Returns:
            np.ndarray: ECG data array (samples x leads)
        """
        self.sampling_rate = sampling_rate
        
        try:
            # Try to load as CSV with pandas
            df = pd.read_csv(file_path)
            # Remove non-numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            self.ecg_signal = df[numeric_cols].values
        except:
            # Fallback to numpy
            self.ecg_signal = np.loadtxt(file_path, delimiter=',')
            
        return self.ecg_signal
    
    def load_ecg_from_array(self, ecg_data: np.ndarray, sampling_rate: int = 200) -> np.ndarray:
        """
        Load ECG data from numpy array.
        
        Args:
            ecg_data (np.ndarray): ECG data array
            sampling_rate (int): Sampling rate in Hz
            
        Returns:
            np.ndarray: ECG data array
        """
        self.sampling_rate = sampling_rate
        self.ecg_signal = ecg_data
        return self.ecg_signal
    
    def process_ecg(self, lead_index: int = 0, method: str = "neurokit") -> Dict:
        """
        Process ECG signal using Neurokit2.
        
        Args:
            lead_index (int): Index of the ECG lead to process (default: 0)
            method (str): Processing method ('neurokit', 'pantompkins', 'hamilton2016', etc.)
            
        Returns:
            Dict: Processed ECG data and analysis results
        """
        if self.ecg_signal is None:
            raise ValueError("No ECG signal loaded. Please load ECG data first.")
        
        # Select the lead to analyze
        if self.ecg_signal.ndim > 1:
            signal = self.ecg_signal[:, lead_index]
        else:
            signal = self.ecg_signal
        
        # Process ECG signal
        self.processed_ecg = nk.ecg_process(signal, sampling_rate=self.sampling_rate, method=method)
        
        # Extract cleaned signal and R-peaks
        ecg_cleaned = self.processed_ecg[0]["ECG_Clean"]
        info = self.processed_ecg[1]
        
        # Perform ECG analysis
        self.analysis_results = nk.ecg_analyze(self.processed_ecg[0], sampling_rate=self.sampling_rate)
        
        return {
            "ecg_cleaned": ecg_cleaned,
            "ecg_rate": self.processed_ecg[0]["ECG_Rate"],
            "rpeaks": info["ECG_R_Peaks"],
            "analysis": self.analysis_results,
            "processed_signals": self.processed_ecg[0]
        }
    
    def get_hrv_analysis(self) -> Dict:
        """
        Perform Heart Rate Variability (HRV) analysis.
        
        Returns:
            Dict: HRV analysis results
        """
        if self.processed_ecg is None:
            raise ValueError("ECG must be processed first. Call process_ecg() method.")
        
        # Extract R-peaks for HRV analysis
        rpeaks = self.processed_ecg[1]["ECG_R_Peaks"]
        
        # Compute HRV indices
        hrv_indices = nk.hrv(rpeaks, sampling_rate=self.sampling_rate, show=False)
        
        return hrv_indices
    
    def detect_arrhythmia(self) -> Dict:
        """
        Basic arrhythmia detection using Neurokit2.
        
        Returns:
            Dict: Arrhythmia analysis results
        """
        if self.processed_ecg is None:
            raise ValueError("ECG must be processed first. Call process_ecg() method.")
        
        # Get processed signals
        signals = self.processed_ecg[0]
        
        # Extract basic arrhythmia indicators
        rpeaks = self.processed_ecg[1]["ECG_R_Peaks"]
        rr_intervals = np.diff(rpeaks) / self.sampling_rate * 1000  # in ms
        
        # Basic arrhythmia indicators
        mean_rr = np.mean(rr_intervals)
        std_rr = np.std(rr_intervals)
        mean_hr = 60000 / mean_rr if mean_rr > 0 else 0
        
        # Simple arrhythmia flags
        bradycardia = mean_hr < 60
        tachycardia = mean_hr > 100
        irregular_rhythm = std_rr > 50  # Simple threshold for irregularity
        
        return {
            "mean_heart_rate": mean_hr,
            "mean_rr_interval": mean_rr,
            "rr_std": std_rr,
            "bradycardia": bradycardia,
            "tachycardia": tachycardia,
            "irregular_rhythm": irregular_rhythm,
            "total_beats": len(rpeaks)
        }
    
    def generate_plot(self, plot_type: str = "overview", lead_index: int = 0, 
                     duration: Optional[float] = None) -> str:
        """
        Generate ECG plots and return as base64 encoded image.
        
        Args:
            plot_type (str): Type of plot ('overview', 'processed', 'hrv')
            lead_index (int): ECG lead index to plot
            duration (float): Duration in seconds to plot (None for all data)
            
        Returns:
            str: Base64 encoded plot image
        """
        plt.style.use('default')
        
        if plot_type == "overview" and self.ecg_signal is not None:
            # Plot original ECG signal
            signal = self.ecg_signal[:, lead_index] if self.ecg_signal.ndim > 1 else self.ecg_signal
            
            if duration:
                samples_to_plot = int(duration * self.sampling_rate)
                signal = signal[:samples_to_plot]
            
            time = np.arange(len(signal)) / self.sampling_rate
            
            plt.figure(figsize=(12, 6))
            plt.plot(time, signal, 'b-', linewidth=0.8)
            plt.title(f'ECG Signal - Lead {lead_index + 1}')
            plt.xlabel('Time (s)')
            plt.ylabel('Amplitude (mV)')
            plt.grid(True, alpha=0.3)
            
        elif plot_type == "processed" and self.processed_ecg is not None:
            # Plot processed ECG with R-peaks
            signals = self.processed_ecg[0]
            rpeaks = self.processed_ecg[1]["ECG_R_Peaks"]
            
            ecg_cleaned = signals["ECG_Clean"]
            if duration:
                samples_to_plot = int(duration * self.sampling_rate)
                ecg_cleaned = ecg_cleaned[:samples_to_plot]
                rpeaks = rpeaks[rpeaks < samples_to_plot]
            
            time = np.arange(len(ecg_cleaned)) / self.sampling_rate
            
            plt.figure(figsize=(12, 8))
            
            # Plot cleaned ECG
            plt.subplot(2, 1, 1)
            plt.plot(time, ecg_cleaned, 'b-', linewidth=0.8, label='Cleaned ECG')
            plt.scatter(rpeaks / self.sampling_rate, ecg_cleaned[rpeaks], 
                       color='red', s=30, label='R-peaks', zorder=5)
            plt.title('Processed ECG with R-peak Detection')
            plt.xlabel('Time (s)')
            plt.ylabel('Amplitude (mV)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Plot heart rate
            plt.subplot(2, 1, 2)
            hr_signal = signals["ECG_Rate"]
            if duration:
                hr_signal = hr_signal[:samples_to_plot]
            plt.plot(time, hr_signal, 'g-', linewidth=1.0)
            plt.title('Instantaneous Heart Rate')
            plt.xlabel('Time (s)')
            plt.ylabel('Heart Rate (bpm)')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
        elif plot_type == "hrv":
            # Plot HRV analysis
            try:
                hrv_data = self.get_hrv_analysis()
                rpeaks = self.processed_ecg[1]["ECG_R_Peaks"]
                rr_intervals = np.diff(rpeaks) / self.sampling_rate * 1000
                
                plt.figure(figsize=(12, 8))
                
                # RR intervals plot
                plt.subplot(2, 2, 1)
                plt.plot(rr_intervals, 'b-', linewidth=0.8)
                plt.title('RR Intervals')
                plt.xlabel('Beat Number')
                plt.ylabel('RR Interval (ms)')
                plt.grid(True, alpha=0.3)
                
                # RR intervals histogram
                plt.subplot(2, 2, 2)
                plt.hist(rr_intervals, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
                plt.title('RR Intervals Distribution')
                plt.xlabel('RR Interval (ms)')
                plt.ylabel('Frequency')
                plt.grid(True, alpha=0.3)
                
                # Poincaré plot
                plt.subplot(2, 2, 3)
                rr1 = rr_intervals[:-1]
                rr2 = rr_intervals[1:]
                plt.scatter(rr1, rr2, alpha=0.6, s=10)
                plt.plot([min(rr_intervals), max(rr_intervals)], 
                        [min(rr_intervals), max(rr_intervals)], 'r--', alpha=0.7)
                plt.title('Poincaré Plot')
                plt.xlabel('RR(n) (ms)')
                plt.ylabel('RR(n+1) (ms)')
                plt.grid(True, alpha=0.3)
                
                # HRV summary text
                plt.subplot(2, 2, 4)
                plt.axis('off')
                hrv_text = f"HRV Analysis Summary\n\n"
                if 'HRV_RMSSD' in hrv_data.columns:
                    hrv_text += f"RMSSD: {hrv_data['HRV_RMSSD'].iloc[0]:.2f} ms\n"
                if 'HRV_SDNN' in hrv_data.columns:
                    hrv_text += f"SDNN: {hrv_data['HRV_SDNN'].iloc[0]:.2f} ms\n"
                if 'HRV_pNN50' in hrv_data.columns:
                    hrv_text += f"pNN50: {hrv_data['HRV_pNN50'].iloc[0]:.2f}%\n"
                hrv_text += f"Total Beats: {len(rpeaks)}\n"
                hrv_text += f"Mean RR: {np.mean(rr_intervals):.2f} ms\n"
                hrv_text += f"Std RR: {np.std(rr_intervals):.2f} ms"
                
                plt.text(0.1, 0.8, hrv_text, fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
                
                plt.tight_layout()
                
            except Exception as e:
                plt.figure(figsize=(8, 4))
                plt.text(0.5, 0.5, f"HRV Analysis Error: {str(e)}", 
                        ha='center', va='center', fontsize=12)
                plt.axis('off')
        
        else:
            # Default empty plot
            plt.figure(figsize=(8, 4))
            plt.text(0.5, 0.5, "No data available for plotting", 
                    ha='center', va='center', fontsize=12)
            plt.axis('off')
        
        # Convert plot to base64 string
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    def get_summary_report(self) -> Dict:
        """
        Generate a comprehensive summary report of ECG analysis.
        
        Returns:
            Dict: Summary report with all analysis results
        """
        if self.ecg_signal is None:
            return {"error": "No ECG data loaded"}
        
        report = {
            "file_info": {
                "total_samples": len(self.ecg_signal),
                "duration_seconds": len(self.ecg_signal) / self.sampling_rate,
                "sampling_rate": self.sampling_rate,
                "num_leads": self.ecg_signal.shape[1] if self.ecg_signal.ndim > 1 else 1
            }
        }
        
        if self.processed_ecg is not None:
            # Add processing results
            rpeaks = self.processed_ecg[1]["ECG_R_Peaks"]
            report["processing"] = {
                "r_peaks_detected": len(rpeaks),
                "average_heart_rate": len(rpeaks) * 60 / (len(self.ecg_signal) / self.sampling_rate)
            }
            
            # Add analysis results
            if hasattr(self, 'analysis_results') and self.analysis_results is not None:
                report["ecg_analysis"] = self.analysis_results.to_dict('records')[0] if not self.analysis_results.empty else {}
            
            # Add arrhythmia detection
            try:
                arrhythmia_results = self.detect_arrhythmia()
                report["arrhythmia_detection"] = arrhythmia_results
            except:
                report["arrhythmia_detection"] = {"error": "Could not perform arrhythmia analysis"}
            
            # Add HRV if possible
            try:
                hrv_results = self.get_hrv_analysis()
                report["hrv_analysis"] = hrv_results.to_dict('records')[0] if not hrv_results.empty else {}
            except:
                report["hrv_analysis"] = {"error": "Could not perform HRV analysis"}
        
        return report


def analyze_ecg_file(file_path: str, file_type: str = 'auto', 
                    sampling_rate: int = 200, num_leads: int = 3, 
                    uv_per_lsb: float = 1.0, lead_index: int = 0) -> Dict:
    """
    Convenience function to analyze an ECG file and return comprehensive results.
    
    Args:
        file_path (str): Path to ECG file
        file_type (str): File type ('binary', 'csv', or 'auto')
        sampling_rate (int): Sampling rate in Hz
        num_leads (int): Number of leads (for binary files)
        uv_per_lsb (float): Microvolts per LSB (for binary files)
        lead_index (int): Lead index to analyze
        
    Returns:
        Dict: Complete analysis results including plots
    """
    analyzer = NeuroKit2ECGAnalyzer(sampling_rate)
    
    try:
        # Load ECG data
        if file_type == 'auto':
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in ['.csv', '.txt']:
                file_type = 'csv'
            else:
                file_type = 'binary'
        
        if file_type == 'binary':
            analyzer.load_ecg_binary(file_path, num_leads, sampling_rate, uv_per_lsb)
        else:
            analyzer.load_ecg_csv(file_path, sampling_rate)
        
        # Process ECG
        processing_results = analyzer.process_ecg(lead_index)
        
        # Generate plots
        plots = {
            "overview": analyzer.generate_plot("overview", lead_index, duration=30),
            "processed": analyzer.generate_plot("processed", lead_index, duration=30),
            "hrv": analyzer.generate_plot("hrv", lead_index)
        }
        
        # Get summary report
        summary = analyzer.get_summary_report()
        
        return {
            "success": True,
            "processing_results": processing_results,
            "summary_report": summary,
            "plots": plots,
            "analyzer": analyzer  # Return analyzer instance for further use
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "plots": {},
            "summary_report": {}
        }