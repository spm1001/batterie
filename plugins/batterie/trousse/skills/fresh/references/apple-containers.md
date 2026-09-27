# Apple Containerization (macOS microVMs)

When ardoise's context isolation isn't enough — when you need the inner Claude unable to read host files at all — Apple Containerization provides lightweight Linux microVMs on macOS (Apple Silicon only).

## When to use containers vs ardoise

| Need | Use |
|------|-----|
| Claude can't *discover* your config | Ardoise (context isolation) |
| Claude can't *read* host files even if it guesses paths | Containers (security isolation) |
| Running untrusted code | Containers |
| Testing plugin install, "new user" experience | Ardoise |
| Evals, surveys, design research | Ardoise |

The two compose: you could run ardoise inside a container for belt-and-braces, but in practice you pick one based on threat model. Ardoise is ~2s overhead; containers add ~650ms cold start on top.

## Apple Container CLI

**Repo:** https://github.com/apple/container
**Released:** 2026-02-03 (v0.9.0) — Apache 2.0
**Install:** `brew install container`

Each container is its own microVM (Virtualization.framework + lightweight Linux kernel). Not shared-kernel like Docker — stronger isolation.

### Core commands

```bash
# Build
container build --tag NAME PATH
container build --build-arg KEY=VAL --tag NAME PATH

# Run
container run --rm IMAGE CMD                # Ephemeral
container run -d --name N IMAGE             # Detached
container run --env-file F IMAGE CMD        # Pass env vars from file

# Lifecycle
container start|stop|delete NAME
container list [--all]

# Interact
container exec -i -t NAME CMD              # NOT -it (separate flags)
container exec NAME CMD
```

### Key differences from Docker

| Docker | Apple Container |
|--------|----------------|
| `docker` | `container` |
| Shared kernel (namespaces) | Separate microVM per container |
| Linux + macOS hosts | macOS only (Apple Silicon) |
| `docker-compose` | Not available |
| Dockerfile | Containerfile (same syntax) |

### Performance (Apple M4, 24GB)

| Metric | Time |
|--------|------|
| Cold start | ~650ms |
| Warm start | ~420ms |
| Exec | ~80ms |

### Rosetta for x86_64 images

```bash
softwareupdate --install-rosetta --agree-to-license
```

arm64 images run natively.

## Claude workspace image

A Containerfile for a Claude-ready Linux environment:

```dockerfile
FROM ubuntu:24.04
ARG CLAUDE_CODE_VERSION=latest

RUN apt-get update && apt-get install -y \
    curl git ssh bash ca-certificates python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22.x
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs

# uv (global)
RUN curl -LsSf https://astral.sh/uv/install.sh | env CARGO_HOME=/usr/local sh

# Claude Code
RUN if [ "$CLAUDE_CODE_VERSION" = "latest" ]; then \
        npm install -g @anthropic-ai/claude-code; \
    else \
        npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}; \
    fi

# Non-root user
RUN useradd -m -s /bin/bash claude
RUN mkdir -p /home/claude/.claude \
    && echo '{"trustedDirectories":["/home/claude"]}' > /home/claude/.claude/settings.local.json \
    && chown -R claude:claude /home/claude

USER claude
WORKDIR /home/claude
```

### Auth at runtime (never bake tokens into images)

```bash
# Create temp env file, pass it, delete it
echo "CLAUDE_CODE_OAUTH_TOKEN=$TOKEN" > /tmp/sandbox-env
container run --env-file /tmp/sandbox-env claude-workspace claude -p "hello"
rm /tmp/sandbox-env
```

On macOS, store the token in Keychain:
```bash
security add-generic-password -a sandbox -s CLAUDE_CODE_OAUTH_TOKEN -w "<token>" -U
TOKEN=$(security find-generic-password -s CLAUDE_CODE_OAUTH_TOKEN -w)
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `container: command not found` | `brew install container` or build from source |
| Build fails with Rosetta error | `softwareupdate --install-rosetta --agree-to-license` |
| Claude exits silently | Token invalid/expired — get fresh one with `claude setup-token` |
| `container exec` says "no such container" | Name is prefixed: `sandbox-NAME` not `NAME` |
| `-it` flag rejected | Use `-i -t` (separate flags, not combined) |
