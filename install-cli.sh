#!/bin/bash
# Dumont Cloud CLI - System Installation Script

set -e

echo "🚀 Installing Dumont Cloud CLI system-wide..."
echo ""

# Get the script directory (where the project is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/cli.py"
VENV_PATH="$SCRIPT_DIR/venv"

# Check if cli.py exists
if [ ! -f "$CLI_SCRIPT" ]; then
    echo "❌ Error: cli.py not found in $SCRIPT_DIR"
    exit 1
fi

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Error: venv not found in $SCRIPT_DIR"
    echo "   Please create venv first: python3 -m venv venv"
    exit 1
fi

# Create the global command script
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

COMMAND_NAME="dumont"
COMMAND_PATH="$BIN_DIR/$COMMAND_NAME"

echo "📝 Creating global command: $COMMAND_NAME"
cat > "$COMMAND_PATH" << 'EOFCMD'
#!/bin/bash
# Dumont Cloud CLI - Global Command

# Path to the project (will be replaced during installation)
PROJECT_DIR="__PROJECT_DIR__"
CLI_SCRIPT="$PROJECT_DIR/cli.py"
VENV_PATH="$PROJECT_DIR/venv"

# Activate venv and run CLI
source "$VENV_PATH/bin/activate"
python "$CLI_SCRIPT" "$@"
EOFCMD

# Replace the placeholder with actual path
sed -i "s|__PROJECT_DIR__|$SCRIPT_DIR|g" "$COMMAND_PATH"

# Make it executable
chmod +x "$COMMAND_PATH"

echo "✅ Command created at: $COMMAND_PATH"
echo ""

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  WARNING: $HOME/.local/bin is not in your PATH"
    echo ""
    echo "To fix this, add this line to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then run: source ~/.bashrc (or restart your terminal)"
    echo ""
else
    echo "✅ $HOME/.local/bin is already in PATH"
    echo ""
fi

echo "════════════════════════════════════════════════════════════════"
echo ""
echo "✅ Installation Complete!"
echo ""
echo "You can now use 'dumont' from anywhere:"
echo ""
echo "  dumont list                          # List all endpoints"
echo "  dumont call GET /api/health          # Call API"
echo "  dumont call POST /api/auth/login ... # Login"
echo "  dumont interactive                   # Interactive mode"
echo ""
echo "Quick start:"
echo "  dumont list"
echo ""
echo "════════════════════════════════════════════════════════════════"
