#!/usr/bin/env python3
"""
Startup script for Neurokit2 ECG Analysis Server
Run this script to start the backend server for advanced ECG analysis.
"""

import os
import sys
import subprocess
import time

def check_dependencies():
    """Check if required Python packages are installed."""
    required_packages = ['neurokit2', 'flask', 'flask_cors', 'numpy', 'pandas', 'matplotlib']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n🔧 Installing missing packages...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ All packages installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install packages: {e}")
            return False
    
    return True

def main():
    print("🧠 Neurokit2 ECG Analysis Server")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('neurokit_server.py'):
        print("❌ Error: neurokit_server.py not found in current directory")
        print("Please run this script from the ECG Explorer directory")
        return 1
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    if not check_dependencies():
        return 1
    
    print("✅ All dependencies satisfied!")
    print("\n🚀 Starting Neurokit2 ECG Analysis Server...")
    print("   Access the analysis interface at: http://localhost:5000")
    print("   Press Ctrl+C to stop the server")
    print("-" * 40)
    
    try:
        # Start the Flask server
        import neurokit_server
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())