---
name: claude-survey
description: Survey naive Claude instances for design research — polls isolated Claudes on instinctive responses to DSL, API, or CLI design questions. INVOKE BEFORE finalizing naming, verb choice, or grammar decisions. Triggers on 'survey Claudes', 'what would a naive Claude write', 'poll model instincts', 'test what Claudes naturally do'. (user)
---

# Claude Survey

Poll isolated Claude instances to discover what model weights naturally produce — before your documentation teaches them otherwise.

## Core Principle

**Documentation shapes behavior. To know what Claudes naturally write, you must test without documentation.** This means physically isolating the test Claudes from all project context, global CLAUDE.md, and skill files.

## When to Use

- Designing a CLI verb vocabulary (which verbs feel natural?)
- Choosing between API naming conventions
- Validating whether existing naming matches model instincts
- Before investing in aliases or error hints — check if the base grammar is right
- Any "what would Claude naturally do?" question

## When NOT to Use

- Testing whether documentation is effective (that's a different experiment — give them the docs)
- Evaluating code quality or correctness
- Questions with objectively right answers (use tests, not surveys)

## Isolation

Survey scripts use `ardoise.sh` (in `trousse/scripts/`) in print mode (`-p`) for isolation. This handles all context leakage via three mechanisms:

| Mechanism | What it blocks |
|-----------|---------------|
| `env -i` | All inherited env vars including `CLAUDECODE=1` (nesting detection) |
| `HOME=<tmpdir>` with only `.credentials.json` + stripped `claude.json` | CLAUDE.md, settings, hooks, skills, MCP config |
| `cd /tmp` | Project CLAUDE.md, git repo context |

The old approach (physically `mv` CLAUDE.md aside with trap/restore) is superseded — `ardoise.sh` achieves the same isolation without touching real files.

### The `--tools` vs `--allowed-tools` Trap

| Flag | Effect |
|------|--------|
| `--tools ""` | No tools offered to model. Pure text response. |
| `--allowed-tools ""` | Tools offered but all blocked. Model tries, gets rejected, **burns a turn**. With `--max-turns 1`, you get `Error: Reached max turns`. |

Always use `--tools ""` for surveys.

### Background: Six Layers of Context Leakage

These are the layers `ardoise.sh` blocks. Documented here for understanding, not because you need to handle them manually:

| Layer | How it leaks | How ardoise.sh blocks it |
|-------|-------------|-------------------------------|
| Global `~/.claude/CLAUDE.md` | Always loaded from `$HOME` | Fake HOME has no CLAUDE.md |
| Project `CLAUDE.md` | Loaded from CWD/parents | CWD is `/tmp` (no repo) |
| Plugin cache / skills | Skill registry under `$HOME` | Fake HOME has no plugins/ |
| `~/.claude/settings.json` | Hooks config | Fake HOME has no settings |
| `CLAUDECODE=1` env var | Nesting detection / resistance | `env -i` scrubs it |
| Tools | Model burns turns on tool attempts | Pass `--tools ""` in survey scripts |

## Methodology

### 1. Use a Fictional Tool Name

Even with CLAUDE.md hidden, model training data may contain the real tool. Use a bland, meaningless name:

| Good | Bad | Why bad |
|------|-----|---------|
| `xt` | `webbot` | "web" + "bot" primes for web automation vocabulary |
| `zq` | `browsectl` | "browse" + "ctl" primes for browser + control patterns |
| `kd` | `pagerunner` | Compound words prime for both parts |

**Caveat:** Even bland names prime slightly. `xt` was associated with "extract" by test subjects. Note this in analysis but don't over-correct — the priming is mild.

### 2. Structured JSON Responses

Ask for JSON to enable programmatic analysis. Define the schema in the prompt:

```
Respond with ONLY a JSON object, no markdown fencing, no explanation:
{
  "invocation": "the full command(s) you would type",
  "verbs_used": ["list", "of", "verbs"],
  "key_field": "specific answer to your research question",
  ...
}
```

**Expect ~20-40% parse failures.** The model wraps in markdown fences, adds preamble, or produces malformed JSON. The analysis script handles this with regex extraction as fallback.

### 3. Multiple Runs Per Scenario

Models are stochastic. n=1 tells you nothing about the distribution.

| n | Good for |
|---|----------|
| 3 | Quick sanity check, finding obvious patterns |
| 10 | Design decisions — shows distribution and outliers |
| 20+ | Publication-quality claims (rarely needed) |

### 4. Multiple Scenarios

Don't test one task — test several that exercise different aspects:

- Simple case (one-liner)
- Multi-step workflow
- Error recovery / ambiguous situation
- Edge case that reveals assumptions

### 5. Prompt Design

- State what the tool does in ONE sentence
- Say "you have NEVER seen documentation" and "you have NO access to files"
- Say "write what you'd TRY FIRST"
- Don't explain the DSL grammar — that's what you're testing
- Don't use the real tool name anywhere in the prompt

## Running a Survey

### Quick Probe (verify isolation)

```bash
${CLAUDE_SKILL_DIR}/scripts/probe.sh
```

Runs 5 checks: project context visibility, domain knowledge, name priming, file access, baseline instinct. Review output before running full survey.

### Full Survey

```bash
${CLAUDE_SKILL_DIR}/scripts/survey.sh <scenarios_file> [runs_per_scenario]
```

The scenarios file is bash — declare an associative array:

```bash
# my-scenarios.sh
declare -A SCENARIOS
SCENARIOS[simple]='You have a CLI tool called "xt" for ... Write the command to ...'
SCENARIOS[complex]='You have a CLI tool called "xt" for ... Write the commands to ...'

# Fields to extract in JSON (customize per survey)
JSON_FIELDS='{
  "invocation": "the full command(s)",
  "verb_used": "the main verb",
  "your_specific_field": "description"
}'
```

### Analysis

```bash
${CLAUDE_SKILL_DIR}/scripts/analyze.py <output_dir>
```

Reads all JSON files, extracts with fallback regex, produces per-scenario frequency tables with percentage bars.

## Interpreting Results

### Saturation

If 3/3 agree on a choice, you've likely reached saturation for that question. If all 3 differ, you need more samples.

### Prompt Echo vs. Instinct

Watch for the prompt's word choice leaking into responses. If your prompt says "open a URL" and 60% write `open`, that's prompt echo. Vary the prompt wording across scenarios to distinguish.

### Parse Error Bias

High parse failure rates (>50%) mean your valid responses are a biased subsample — the model may have produced different content when it chose to explain rather than output JSON. Note this in conclusions.

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Using real tool name | Model has training data about it | Fictional name |
| `--allowed-tools ""` | Model burns turns on tool attempts | `--tools ""` |
| Manual `mv` CLAUDE.md | Fragile, trap can fail | Use `ardoise.sh` (env scrub) |
| `--system-prompt` alone | CLAUDE.md still loads | Use `ardoise.sh` |
| Testing in project directory | Project context leaks | Use `ardoise.sh` (runs from /tmp) |
| n=1 per scenario | No distribution signal | Minimum n=3, prefer n=10 |
| Subagents instead of `claude -p` | Inherit full parent context | Always use `claude -p` via `ardoise.sh` |
| Compound tool name | Primes model with components | Bland 2-letter name |
