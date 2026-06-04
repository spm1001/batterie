# Cross-machine working-tree sweep

The engine: `scripts/repo-sweep.sh`. Finds every git repo under the given roots (on the local machine or a remote ssh host), and reports its state.

## Modes

```bash
S=skills/github-cleanup/scripts/repo-sweep.sh
"$S" local ~/Repos ~/.claude              # local roots — fetches each repo for a true reading
"$S" ssh hezza '$HOME/Repos' '$HOME/.claude'   # run the same engine on a remote host
"$S" --no-fetch local ~/Repos             # fast: dirty-only scan, skips the fetch
```

## Per-repo flags

| Flag | Meaning | Risk |
|------|---------|------|
| `DIRTY:n` | n uncommitted working-tree changes | exists only on disk — lost if the machine dies |
| `UNPUSHED:n` | n commits not on the remote | the real loss risk for committed work |
| `behind:n` | n commits the remote has that you don't | benign — fast-forwards cleanly |
| `stash:n` | n stash entries | easy to forget; review periodically |
| `NO-REMOTE` | no `origin` configured | can't be backed up to a remote at all |

## The stale-ref story (why the engine fetches by default)

Without a `git fetch`, ahead/behind is measured against each machine's *last* fetch — so a repo can read as "ahead" purely because its `origin` pointer is old. A marketplace clone once reported "7 ahead on Mac, 4 ahead on Hezza" and was in fact byte-identical to `origin/main` on both machines; nobody had fetched in weeks. The lesson: trust `--no-fetch` only for the `DIRTY` flag. For anything about sync state, fetch first.

## Triage rules

- `UNPUSHED` → push. If also `behind`, the branch has diverged — pull (rebase if the local commits are yours and unshared), then push.
- `DIRTY` → inspect *what changed* before acting. Real work gets committed; a stale "fossil" clone whose changes just mirror a direction the remote already took can be discarded (`git checkout`/`reset`). Tell them apart by checking whether the deletions/edits already happened on `origin`.
- `behind` only → fast-forward (`git pull --ff-only`). Zero risk.
- `NO-REMOTE` → decide if it deserves a backup home, or is genuinely throwaway.

## Version-bump guard (published plugins)

A content change to a Claude Code plugin that does not bump `.claude-plugin/plugin.json`'s version will not propagate to clients — they keep serving the old version. For any plugin repo flagged `DIRTY` or `UNPUSHED`, confirm the bump:

```bash
git -C "$repo" diff origin/main -- .claude-plugin/plugin.json | grep -q '"version"' \
  || echo "  warning: $repo has changes but version NOT bumped — clients won't update"
```

Run this across all plugin repos as part of a release sweep, not just one at a time.
