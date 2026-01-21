#!/bin/bash

# Relibank Test Environment Setup Script
# This script sets up a Python virtual environment and installs all test dependencies

set -e  # Exit on error

echo "=========================================="
echo "Relibank Test Environment Setup"
echo "=========================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
VENV_DIR=".venv-relibank-tests"

if [ -d "$VENV_DIR" ]; then
    echo "⚠ Virtual environment already exists at $VENV_DIR"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "Installing test dependencies..."
echo "This may take a few minutes..."
echo ""

pip install \
    pytest \
    requests \
    --quiet

echo "✓ Dependencies installed"

# Print summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Virtual environment created at: $VENV_DIR"
echo ""
echo "To activate the environment:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest tests/ -v"
echo ""
echo "To run specific test files:"
echo "  pytest tests/test_end_to_end.py -v"
echo "  pytest tests/test_scenario_service.py -v"
echo "  pytest tests/test_payment_scenarios.py -v"
echo ""
echo "See tests/QUICKSTART.md for more information"
echo ""
