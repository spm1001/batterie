#!/bin/bash
# Test OuterClaude/InnerClaude pattern with -tty flag
# Usage: ./test-outer-inner.sh <CLAUDE_CODE_OAUTH_TOKEN>
#
# Validates that:
# 1. -tty allocates a proper PTY
# 2. pipe-pane captures Claude's output
# 3. Claude responds to a simple prompt

set -e

TOKEN="${1:-$CLAUDE_CODE_OAUTH_TOKEN}"
if [ -z "$TOKEN" ]; then
    echo "Usage: $0 <CLAUDE_CODE_OAUTH_TOKEN>"
    echo "Or set CLAUDE_CODE_OAUTH_TOKEN env var"
    exit 1
fi

CAPTURE=$(mktemp /tmp/outer-inner-test.XXXXXX)
trap "rm -f '$CAPTURE'" EXIT

echo "Starting OuterClaude/InnerClaude test..."

sprite exec -tty bash -c "
CAPTURE=$CAPTURE  # Pass through to inner script

# Start tmux with pipe-pane capture
tmux new-session -d -s outerinner -x 150 -y 50
tmux pipe-pane -t outerinner -o 'cat >> $CAPTURE'

# Set up NVM
tmux send-keys -t outerinner 'export NVM_DIR=\"/.sprite/languages/node/nvm\" && . \"\\\$NVM_DIR/nvm.sh\" && nvm use default' Enter
sleep 3

# Export token
tmux send-keys -t outerinner 'export CLAUDE_CODE_OAUTH_TOKEN=$TOKEN' Enter
sleep 1

# Run Claude with test prompt
tmux send-keys -t outerinner 'claude -p \"Say exactly: OUTER_INNER_TEST_PASS\"' Enter
sleep 20

# Cleanup tmux
tmux kill-session -t outerinner 2>/dev/null || true

# Check result
if grep -q 'OUTER_INNER_TEST_PASS' $CAPTURE; then
    echo '=== TEST PASSED ==='
    echo 'OuterClaude successfully received InnerClaude response'
    exit 0
else
    echo '=== TEST FAILED ==='
    echo 'Captured output:'
    cat $CAPTURE | strings | tail -30
    exit 1
fi
"
