#!/bin/bash
# DHG AI Factory Workflows Installer
# Usage: ./install-dhg-workflows.sh /path/to/project

PROJECT_DIR="${1:-.}"
AGENT_DIR="$PROJECT_DIR/.agent"
WORKFLOWS_DIR="$AGENT_DIR/workflows"

echo "Installing DHG AI Factory workflows..."

# Create .agent directory if it doesn't exist
mkdir -p "$WORKFLOWS_DIR"

# Download workflows from GitHub (or copy from tarball)
if command -v git &> /dev/null; then
    echo "Cloning workflows from GitHub..."
    git clone https://github.com/YOUR_USERNAME/dhg-workflows.git "$WORKFLOWS_DIR"
else
    echo "Git not found. Please install git or use the tarball method."
    exit 1
fi

echo "✅ Workflows installed to: $WORKFLOWS_DIR"
echo ""
echo "Available commands:"
ls -1 "$WORKFLOWS_DIR"/*.md | sed 's/.*\//  \//' | sed 's/\.md$//'
