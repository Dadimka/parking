#!/bin/bash

# Script to format backend code with black

set -e

echo "🎨 Formatting backend code with black..."

# Check if black is installed
if ! command -v black &> /dev/null
then
    echo "❌ Black is not installed. Installing..."
    pip install black
fi

# Format app directory
echo "📁 Formatting app/ directory..."
black app/

# Format tests directory
echo "📁 Formatting tests/ directory..."
black tests/

echo "✅ Formatting complete!"
echo ""
echo "To check formatting without modifying files, run:"
echo "  black --check app/ tests/"
