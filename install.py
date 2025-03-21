#!/usr/bin/env python3
"""
Installation script for flock project.
This script installs both regular packages and Git dependencies.
"""
import subprocess
import sys
import os

def main():
    print("Installing flock project...")
    
    # First, install git dependencies from requirements.txt
    print("\nStep 1: Installing dependencies from requirements.txt (including Git dependencies)")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                          check=False, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error installing dependencies from requirements.txt:")
        print(result.stderr)
        sys.exit(1)
    else:
        print("Dependencies installed successfully.")
    
    # Then install the project in development mode
    print("\nStep 2: Installing the project in development mode")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                          check=False, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error installing the project:")
        print(result.stderr)
        sys.exit(1)
    else:
        print("Project installed successfully.")
    
    print("\nInstallation completed successfully!")

if __name__ == "__main__":
    main() 