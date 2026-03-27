#!/bin/bash
# Wrapper for image generation - loads API key at runtime
# Portable: checks env var first, then macOS Keychain
# This keeps the secret out of shell profiles and config files

# 1. Already in environment (Sprite/Linux, or explicit export)
if [ -n "$GEMINI_API_KEY" ]; then
  : # Already set, use it
# 2. macOS Keychain
elif command -v security &>/dev/null; then
  export GEMINI_API_KEY="$(security find-generic-password -a "$USER" -w -s "gemini-api-key" 2>/dev/null)"
fi

# 3. Still empty? Fail with platform-appropriate help
if [ -z "$GEMINI_API_KEY" ]; then
  echo "Error: GEMINI_API_KEY not found" >&2
  echo "Get a key from: https://aistudio.google.com/apikey" >&2
  if command -v security &>/dev/null; then
    echo "macOS: security add-generic-password -a \"\$USER\" -s \"gemini-api-key\" -w \"your-key\"" >&2
  else
    echo "Linux/Sprite: export GEMINI_API_KEY=\"your-key\" in ~/.bashrc or use fly secrets" >&2
  fi
  exit 1
fi

exec ~/.claude/.venv/bin/python "$(dirname "$0")/generate.py" "$@"
