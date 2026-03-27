#!/usr/bin/env bash
# probe.sh — Verify Claude isolation before running a survey
# Uses ardoise.sh for env-scrubbed isolation.

set -euo pipefail

# Find ardoise.sh (sibling in trousse/scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ARDOISE="$SCRIPT_DIR/../../../scripts/ardoise.sh"
if [ ! -x "$ARDOISE" ]; then
  ARDOISE="$(dirname "$SCRIPT_DIR")/../../scripts/ardoise.sh"
fi
if [ ! -x "$ARDOISE" ]; then
  echo "Error: ardoise.sh not found" >&2
  exit 1
fi

SYSPROMPT="You are a helpful assistant. You have no tools available. Respond with text only."

ask() {
  echo "$1" | "$ARDOISE" -p --stdin \
    --max-turns 1 \
    --tools "" \
    --system-prompt "$SYSPROMPT" \
    --output-format text \
    2>/dev/null
}

echo ""
echo "=== Probe 1: Project context ==="
ask 'What project are you working in? Do you see any CLAUDE.md or SKILL.md files? List everything you know about your environment.'
echo -e "\n"

echo "=== Probe 2: Domain knowledge ==="
echo -n "Enter a domain term to test (e.g. 'passe', 'bon', your tool name): "
read -r TERM 2>/dev/null || TERM="passe"
ask "Do you know what \"$TERM\" is? What does it do? Be specific — if guessing, say so."
echo -e "\n"

echo "=== Probe 3: Tool name priming ==="
echo -n "Enter the fictional tool name you'll use in the survey (e.g. 'xt'): "
read -r TOOLNAME 2>/dev/null || TOOLNAME="xt"
ask "What does the tool \"$TOOLNAME\" do? Have you heard of it? What associations does the name bring to mind?"
echo -e "\n"

echo "=== Probe 4: File access ==="
ask 'Can you read files on disk? Can you list directories? Can you run shell commands? Report exactly what you can and cannot do right now.'
echo -e "\n"

echo "=== Probe 5: Baseline instinct ==="
ask "You have a CLI tool called \"$TOOLNAME\" for browser automation. It connects to Chrome and lets you script browser actions with a line-based DSL. You have never seen docs for it. Write a command to navigate to https://example.com and take a screenshot. Just write the command."
echo -e "\n"

echo "=== DONE ==="
echo ""
echo "Review above. If probes 1-4 show no domain knowledge and no file access, isolation is clean."
