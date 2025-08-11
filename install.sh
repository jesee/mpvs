#!/bin/bash

# This script packages the moc-plus application into a single standalone executable
# using PyInstaller. The final executable will be placed in the 'dist' directory.

# Exit immediately if a command exits with a non-zero status.
set -e

# Get the absolute path of the directory where the script is located.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
PROJECT_ROOT="$SCRIPT_DIR"

echo "--- MOC-Plus Standalone Packager ---"

# 1. Check for the virtual environment's Python interpreter.
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Error: Virtual environment not found or python executable is missing at '$VENV_PYTHON'."
    echo "Please create the virtual environment first: python3 -m venv venv"
    exit 1
fi

echo "🐍 Found Python interpreter at: $VENV_PYTHON"
cd "$PROJECT_ROOT"

# 2. Ensure PyInstaller is installed in the virtual environment.
echo "📦 Checking and installing PyInstaller..."
"$VENV_PYTHON" -m pip install pyinstaller &> /dev/null
echo "   PyInstaller is ready."

# 3. Clean up previous build artifacts to ensure a fresh build.
echo "🧹 Cleaning up previous build artifacts (dist/, build/, *.spec)..."
rm -rf dist/ build/ moc-plus.spec
echo "   Cleanup complete."

# 4. Run PyInstaller with the correct entry point (run.py) and options.
echo "🚀 Running PyInstaller to build the standalone executable..."
echo "   This might take a moment."

"$VENV_PYTHON" -m PyInstaller --onefile --name moc-plus --add-data "moc_plus/tui.css:moc_plus" run.py

# 5. Verify the result and provide a clear success message.
if [ -f "dist/moc-plus" ]; then
    echo ""
    echo "✅ Success! The standalone executable has been created."
    echo "👉 You can now run your application directly:"
    echo "   $PROJECT_ROOT/dist/moc-plus"
else
    echo ""
    echo "❌ Error: Build failed. The executable was not found in the 'dist' directory."
    echo "Please check the output above for any errors from PyInstaller."
    exit 1
fi