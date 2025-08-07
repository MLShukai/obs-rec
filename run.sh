#!/bin/bash

# OBS Recording Discord Bot Launcher for Linux
# This script sets up dependencies and runs the obs-rec Discord bot

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if process is running
process_exists() {
    pgrep -f "$1" >/dev/null 2>&1
}

# =============================================================================
#                              DEPENDENCY RESOLUTION
# =============================================================================

print_info "Checking dependencies..."

# 1. Check and install uv
if ! command_exists uv; then
    print_warning "uv is not installed."
    read -p "Do you want to install uv? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        if [ $? -ne 0 ]; then
            print_error "Failed to install uv"
            exit 1
        fi
        print_success "uv installed successfully"
    else
        print_error "uv installation was declined. Cannot proceed."
        exit 1
    fi
fi

# 2. Update PATH for uv
export PATH="$HOME/.local/bin:$PATH"

# Verify uv is accessible
if ! command_exists uv; then
    print_error "uv is still not accessible after installation. Please check your PATH."
    exit 1
fi

print_success "uv is available"

# 3. Install dependencies
print_info "Installing Python dependencies..."
if ! uv sync --all-extras; then
    print_error "Failed to install dependencies with uv sync --all-extras"
    exit 1
fi
print_success "Dependencies installed"

# 4. Check ffmpeg availability (required for video compression)
if ! command_exists ffmpeg; then
    print_warning "ffmpeg is not installed!"
    print_warning "ffmpeg is required for video compression."
    echo "Install it using:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  Fedora: sudo dnf install ffmpeg"
    echo "  Arch: sudo pacman -S ffmpeg"
    read -p "Continue without ffmpeg? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "ffmpeg is available"
fi

# =============================================================================
#                            ENVIRONMENT SETUP
# =============================================================================

if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating one interactively..."

    # Discord Bot Token
    echo
    print_info "Discord Bot Configuration"
    echo "To get a Discord bot token:"
    echo "1. Go to https://discord.com/developers/applications"
    echo "2. Create a new application or select existing one"
    echo "3. Go to 'Bot' section → 'Token' → 'Copy'"
    echo
    read -p "Enter Discord Bot Token: " DISCORD_BOT_TOKEN
    while [ -z "$DISCORD_BOT_TOKEN" ]; do
        print_error "Discord Bot Token is required!"
        read -p "Enter Discord Bot Token: " DISCORD_BOT_TOKEN
    done

    # Discord Channel ID
    echo
    echo "To get Discord Channel ID:"
    echo "1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)"
    echo "2. Right-click on the target channel → 'Copy Channel ID'"
    echo
    read -p "Enter Discord Channel ID: " DISCORD_CHANNEL_ID
    while [ -z "$DISCORD_CHANNEL_ID" ]; do
        print_error "Discord Channel ID is required!"
        read -p "Enter Discord Channel ID: " DISCORD_CHANNEL_ID
    done

    # OBS WebSocket Configuration
    echo
    print_info "OBS WebSocket Configuration"
    echo "In OBS: Tools → WebSocket Server Settings"
    echo
    read -p "OBS Host [localhost]: " OBS_HOST
    OBS_HOST=${OBS_HOST:-localhost}

    read -p "OBS Port [4455]: " OBS_PORT
    OBS_PORT=${OBS_PORT:-4455}

    read -sp "OBS Password (leave empty if none): " OBS_PASSWORD
    echo

    # Recording Configuration
    echo
    print_info "Recording Configuration"
    read -p "Recording duration in seconds [30]: " RECORDING_DURATION
    RECORDING_DURATION=${RECORDING_DURATION:-30}

    read -p "Recording interval in seconds [1800 (30 min)]: " RECORDING_INTERVAL
    RECORDING_INTERVAL=${RECORDING_INTERVAL:-1800}

    read -p "Max video size in MB for Discord [10]: " VIDEO_MAX_SIZE_MB
    VIDEO_MAX_SIZE_MB=${VIDEO_MAX_SIZE_MB:-10}

    # Write .env file
    cat > .env << EOF
# Discord Bot Configuration
DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
DISCORD_CHANNEL_ID=${DISCORD_CHANNEL_ID}

# OBS WebSocket Configuration
OBS_HOST=${OBS_HOST}
OBS_PORT=${OBS_PORT}
OBS_PASSWORD=${OBS_PASSWORD}

# Recording Configuration
RECORDING_DURATION=${RECORDING_DURATION}
RECORDING_INTERVAL=${RECORDING_INTERVAL}
VIDEO_MAX_SIZE_MB=${VIDEO_MAX_SIZE_MB}
EOF

    print_success ".env file created successfully"
    echo
    print_warning "⚠️  Keep your .env file secure and never commit it to version control!"
else
    print_success ".env file found"
fi

# =============================================================================
#                          SOFTWARE STARTUP VERIFICATION
# =============================================================================

print_info "Checking required software..."

# 1. Check OBS
if ! process_exists "obs"; then
    print_warning "OBS is not running!"
    echo "Please ensure:"
    echo "1. OBS Studio is installed and running"
    echo "2. WebSocket Server is enabled (Tools → WebSocket Server Settings)"
    echo "3. Enable the server and note the port (default: 4455)"
    echo "4. Set a password if desired (update .env file accordingly)"
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "OBS is running"
fi

# 2. Quick OBS WebSocket test
print_info "Testing OBS WebSocket connection..."
source .env
TEST_RESULT=$(uv run python -c "
import sys
try:
    import obsws_python as obs
    client = obs.ReqClient(host='${OBS_HOST}', port=${OBS_PORT}, password='${OBS_PASSWORD}' if '${OBS_PASSWORD}' else None, timeout=3)
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1) || true

if [[ "$TEST_RESULT" == *"SUCCESS"* ]]; then
    print_success "OBS WebSocket connection successful"
else
    print_warning "Could not connect to OBS WebSocket"
    echo "Error: $TEST_RESULT"
    echo
    echo "Please check:"
    echo "1. OBS is running"
    echo "2. WebSocket Server is enabled in OBS"
    echo "3. Host, port, and password in .env match OBS settings"
    echo
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# =============================================================================
#                                LAUNCH BOT
# =============================================================================

print_info "Starting OBS Recording Discord Bot..."
echo
print_info "Bot Configuration:"
source .env
echo "  • Channel ID: ${DISCORD_CHANNEL_ID}"
echo "  • OBS Host: ${OBS_HOST}:${OBS_PORT}"
echo "  • Recording: ${RECORDING_DURATION}s every ${RECORDING_INTERVAL}s"
echo "  • Max video size: ${VIDEO_MAX_SIZE_MB} MB"
echo
print_info "Press Ctrl+C to stop the bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Run the bot
uv run python -m obs_rec

print_success "Bot stopped"
