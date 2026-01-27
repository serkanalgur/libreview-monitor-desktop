#!/bin/bash
source venv/bin/activate
echo "Starting PyInstaller build..."
pyinstaller --noconfirm LibreViewMonitor.spec
echo "Build complete. Check the dist/ directory."
