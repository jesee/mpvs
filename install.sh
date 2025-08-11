#!/bin/bash

# This script packages the moc-plus application into a single standalone executable
# using PyInstaller. The final executable will be placed in the 'dist' directory.

# Exit immediately if a command exits with a non-zero status.
set -e

# Get the absolute path of the directory where the script is located.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"
PROJECT_ROOT="$SCRIPT_DIR"

echo "--- MPVS Standalone Packager ---"

# 1. Check for and create the virtual environment if it doesn't exist.
if [ ! -f "$VENV_PYTHON" ]; then
    echo "🐍 Virtual environment not found. Creating one at '$SCRIPT_DIR/venv'..."
    python3 -m venv "$SCRIPT_DIR/venv"
    echo "   Virtual environment created."
fi

echo "🐍 Found Python interpreter at: $VENV_PYTHON"

# 2. Install/update dependencies from requirements.txt inside the moc_plus directory.
echo "📦 Installing dependencies from moc_plus/requirements.txt..."
"$VENV_PYTHON" -m pip install -r "$PROJECT_ROOT/moc_plus/requirements.txt"
echo "   Dependencies are up to date."

cd "$PROJECT_ROOT"

# 3. Ensure PyInstaller is installed in the virtual environment.
echo "📦 Checking and installing PyInstaller..."
"$VENV_PYTHON" -m pip install pyinstaller &> /dev/null
echo "   PyInstaller is ready."

# 4. Clean up previous build artifacts to ensure a fresh build.
echo "🧹 Cleaning up previous build artifacts (dist/, build/, *.spec)..."
rm -rf dist/ build/ moc-plus.spec mpvs.spec
echo "   Cleanup complete."

# 5. Run PyInstaller with the correct entry point (run.py) and options.
echo "🚀 Running PyInstaller to build the standalone executable..."
echo "   This might take a moment."

"$VENV_PYTHON" -m PyInstaller --onefile --name mpvs --add-data "moc_plus/tui.css:moc_plus" run.py

# 6. Verify the result and provide a clear success message.
if [ -f "dist/mpvs" ]; then
    echo ""
    echo "✅ Success! The standalone executable has been created."
    echo "👉 You can now run your application directly:"
    echo "   $PROJECT_ROOT/dist/mpvs"
else
    echo ""
    echo "❌ Error: Build failed. The executable was not found in the 'dist' directory."
    echo "Please check the output above for any errors from PyInstaller."
    exit 1
fi