#!/usr/bin/env bash
# ardoise.sh — Run Claude on a blank slate
#
# Creates a temporary HOME with auth + onboarding state but no config,
# skills, hooks, or plugins. Two modes:
#
#   Interactive (default):  Opens Claude TUI as a fresh user would see it.
#   Print (-p):             Runs claude -p for automated/scripted use.
#
# Usage:
#   ardoise.sh                                    # Interactive, CWD=/tmp
#   ardoise.sh /path/to/dir                       # Interactive, specific dir
#   ardoise.sh -p "prompt"                        # Print mode, one-shot
#   ardoise.sh -p --max-turns 5 -- "prompt"       # Print mode with flags
#   echo "prompt" | ardoise.sh -p --stdin         # Print mode, stdin
#
# Cross-platform (Linux + macOS).

set -euo pipefail

# ── Parse args ────────────────────────────────────────────────────────

PRINT_MODE=false
CLAUDE_ARGS=()
PROMPT=""
USE_STDIN=false
START_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--print)
            PRINT_MODE=true
            shift
            ;;
        --)
            shift
            PROMPT="${1:-}"
            [[ -n "$PROMPT" ]] && shift
            break
            ;;
        --stdin)
            USE_STDIN=true
            shift
            ;;
        --max-turns|--output-format|--system-prompt|--tools|--model)
            if [[ $# -lt 2 ]]; then
                echo "Error: $1 requires a value" >&2
                exit 1
            fi
            CLAUDE_ARGS+=("$1" "$2")
            shift 2
            ;;
        --dangerously-skip-permissions)
            CLAUDE_ARGS+=("$1")
            shift
            ;;
        -*)
            CLAUDE_ARGS+=("$1")
            shift
            ;;
        *)
            if [[ "$PRINT_MODE" == true && -z "$PROMPT" ]]; then
                PROMPT="$1"
            elif [[ "$PRINT_MODE" == false && -z "$START_DIR" ]]; then
                START_DIR="$1"
            else
                PROMPT="$1"
            fi
            shift
            ;;
    esac
done

START_DIR="${START_DIR:-/tmp}"

# Validate: print mode needs a prompt or stdin
if [[ "$PRINT_MODE" == true && "$USE_STDIN" == false && -z "$PROMPT" ]]; then
    echo "Usage: ardoise.sh -p [claude-flags] [--] \"prompt\"" >&2
    echo "       echo \"prompt\" | ardoise.sh -p --stdin [claude-flags]" >&2
    exit 1
fi

# ── Find claude binary ───────────────────────────────────────────────

CLAUDE_BIN=$(command -v claude 2>/dev/null) || {
    echo "Error: claude not found in PATH" >&2
    exit 1
}

CLAUDE_REAL=$(readlink -f "$CLAUDE_BIN")

# ── Find credentials ─────────────────────────────────────────────────

REAL_CLAUDE_DIR="$HOME/.claude"
if [[ ! -f "$REAL_CLAUDE_DIR/.credentials.json" ]]; then
    echo "Error: No credentials at $REAL_CLAUDE_DIR/.credentials.json" >&2
    echo "Run: claude login" >&2
    exit 1
fi

# ── Build isolated HOME ──────────────────────────────────────────────

SANDBOX_HOME=$(mktemp -d)
cleanup() { rm -rf "$SANDBOX_HOME"; }
trap cleanup EXIT

mkdir -p "$SANDBOX_HOME/.claude"

# Auth
cp "$REAL_CLAUDE_DIR/.credentials.json" "$SANDBOX_HOME/.claude/.credentials.json"

# claude.json — copy real one (has onboarding state + feature flags), strip project data
if [[ -f "$REAL_CLAUDE_DIR/claude.json" ]]; then
    cp "$REAL_CLAUDE_DIR/claude.json" "$SANDBOX_HOME/.claude/claude.json"
    python3 - "$SANDBOX_HOME/.claude/claude.json" "$START_DIR" << 'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    cfg = json.load(f)
for key in ["projects", "githubRepoPaths", "skillUsage", "clientDataCache",
            "groveConfigCache"]:
    cfg.pop(key, None)
cfg["officialMarketplaceAutoInstallAttempted"] = True
cfg["officialMarketplaceAutoInstalled"] = False
start_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp"
cfg["projects"] = {
    start_dir: {
        "allowedTools": [],
        "mcpContextUris": [],
        "mcpServers": {},
        "enabledMcpjsonServers": [],
        "disabledMcpjsonServers": [],
        "hasTrustDialogAccepted": True,
        "hasCompletedProjectOnboarding": True,
        "projectOnboardingSeenCount": 0,
        "hasClaudeMdExternalIncludesApproved": False,
        "hasClaudeMdExternalIncludesWarningShown": False,
    }
}
with open(sys.argv[1], "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF

    # Claude reads config from $HOME/.claude.json (symlink), not .claude/claude.json
    ln -s "$SANDBOX_HOME/.claude/claude.json" "$SANDBOX_HOME/.claude.json"
fi

# ── Construct minimal PATH ───────────────────────────────────────────

CLAUDE_DIR=$(dirname "$CLAUDE_REAL")
CLEAN_PATH="${CLAUDE_DIR}:/usr/local/bin:/usr/bin:/bin"

SYMLINK_DIR=$(dirname "$CLAUDE_BIN")
if [[ "$SYMLINK_DIR" != "$CLAUDE_DIR" ]]; then
    CLEAN_PATH="${SYMLINK_DIR}:${CLEAN_PATH}"
fi

# ── Env vars ──────────────────────────────────────────────────────────

ENV_VARS=(
    HOME="$SANDBOX_HOME"
    PATH="$CLEAN_PATH"
    CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY=1
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
    CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
    ENABLE_CLAUDEAI_MCP_SERVERS=false
)

# ── Run ───────────────────────────────────────────────────────────────

if [[ "$PRINT_MODE" == true ]]; then
    # Print mode: claude -p, TERM=dumb, CWD=/tmp
    CMD_PARTS=(claude -p)
    if [[ ${#CLAUDE_ARGS[@]} -gt 0 ]]; then
        CMD_PARTS+=("${CLAUDE_ARGS[@]}")
    fi

    if [[ "$USE_STDIN" == true ]]; then
        env -i "${ENV_VARS[@]}" TERM="${TERM:-dumb}" \
            bash -c 'cd /tmp && exec "$@"' _ "${CMD_PARTS[@]}"
    else
        env -i "${ENV_VARS[@]}" TERM="${TERM:-dumb}" \
            bash -c 'cd /tmp && exec "$@"' _ "${CMD_PARTS[@]}" "$PROMPT"
    fi
else
    # Interactive mode: claude TUI, real TERM, chosen CWD
    exec env -i "${ENV_VARS[@]}" TERM="${TERM:-xterm-256color}" \
        bash -c 'cd "$1" && exec claude' _ "$START_DIR"
fi
