#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""publish.py — one-command shard release for the Batterie de Savoir suite.

The publish dance, as it actually is in mid-2026, has three layers — and two
of the three are already automated:

  - ASSEMBLE (vendor every repo into the batterie marketplace repo, which
    triggers the Desktop/org re-sync) is owned by assemble.yml CI: daily at
    07:00 UTC + workflow_dispatch, hardened with the version-ratchet quarantine.
  - PULL (bring THIS machine current) is owned by the /batterie:update skill.
  - PUSH (bump the SUITE version, commit, push the source repo + the suite
    bump, trigger assemble, confirm it went green) was owned by nobody. That
    manual gap is this script.

So publish.py is the PUSH engine, with the targeted single-plugin PULL bolted
on the end (so one command takes an edit all the way to live-on-this-machine).
It operates on the source repo via the cwd, and on the marketplace via `gh`
against the spm1001/batterie remote — no local batterie checkout needed.

Single-version cutover (bds-suwoho): every published plugin carries ONE suite
version, stamped by the assembler. So the bump target is ALWAYS the suite
version (batterie-de-savoir's plugin.json) — never the cwd repo's. Publishing
a non-batterie repo is a 2-repo push: the content change in cwd, then the
suite bump in batterie-de-savoir. Publishing batterie-de-savoir itself is one
commit (the suite bump IS its content change).

  uv run --script publish.py [--patch|--minor|--major] [-m MSG]
                             [--no-wait] [--no-pull] [--dry-run] [--repo DIR]

Defaults: --patch, watch-to-green, then pull. Escape hatches let you opt out
of either half per-invocation.

Exit codes:
    0 — published (and, unless --no-wait, the CI run went green)
    1 — a precondition failed, or the CI run went red (e.g. a version-ratchet
        quarantine — bump was forgotten elsewhere, or content drifted)
"""

import argparse
import calendar
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

BATTERIE_REMOTE = "spm1001/batterie"
WORKFLOW = "assemble.yml"
# The suite version lives in batterie-de-savoir's plugin.json — and this
# script ships in that repo (scripts/publish.py), so its own location finds
# the suite repo without a hardcoded path. Overridable via --suite-repo for tests.
SUITE_REPO_DEFAULT = Path(__file__).resolve().parent.parent

# Plugins that ship a uv-installed CLI. repo dir -> (cli binary, extras).
# Mirrors the table in skills/update/SKILL.md — the canonical "all plugins"
# version of the pull. Keep them in sync.
CLI_REPOS = {
    "bon": ("bon", "[dolt]"),
    "passe": ("passe", ""),
    "todoist-gtd": ("todoist", ""),
}


def die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---- pure logic (unit-tested) ------------------------------------------------

def bump_version(version: str, level: str) -> str:
    """Compute the next semver. Pure — the heart of the testable surface."""
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"not a 3-part numeric semver: {version!r}")
    major, minor, patch = (int(p) for p in parts)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown bump level: {level!r}")


def replace_version(text: str, new: str) -> str:
    """Targeted replace of the plugin.json version string, leaving every other
    byte untouched. NOT json.dumps — that would reformat sibling arrays (bon's
    `keywords`) and bury the bump under hundreds of spurious diff lines."""
    new_text, n = re.subn(
        r'("version"\s*:\s*")[^"]+(")',
        lambda m: m.group(1) + new + m.group(2),
        text,
        count=1,
    )
    if n != 1:
        raise ValueError(f"expected exactly one version field, replaced {n}")
    return new_text


# ---- side effects ------------------------------------------------------------

def run(cmd: list[str], *, cwd: Path | None = None, dry: bool = False,
        capture: bool = False) -> subprocess.CompletedProcess | None:
    """Echo then run. In dry mode, echo with a DRY marker and don't execute."""
    shown = " ".join(shlex.quote(c) for c in cmd)
    if dry:
        print(f"  DRY  {shown}")
        return None
    print(f"  $    {shown}")
    return subprocess.run(
        cmd, cwd=cwd, text=True,
        capture_output=capture, check=False,
    )


def checked(cp: subprocess.CompletedProcess | None, what: str) -> subprocess.CompletedProcess:
    """Fail loudly on a non-zero subprocess, surfacing captured stderr."""
    if cp is None:  # dry run
        return cp  # type: ignore[return-value]
    if cp.returncode != 0:
        if cp.stderr:
            print(cp.stderr, file=sys.stderr, end="")
        die(f"{what} failed (exit {cp.returncode})")
    return cp


def find_run_id(after_epoch: float, *, attempts: int = 15, delay: float = 2.0) -> str | None:
    """Find the workflow_dispatch run we just triggered. The run takes a few
    seconds to register, so poll briefly for a dispatch run created after our
    trigger timestamp."""
    for _ in range(attempts):
        cp = subprocess.run(
            ["gh", "-R", BATTERIE_REMOTE, "run", "list",
             "--workflow", WORKFLOW, "--event", "workflow_dispatch",
             "--limit", "5", "--json", "databaseId,createdAt,status"],
            text=True, capture_output=True, check=False,
        )
        if cp.returncode == 0:
            for r in sorted(json.loads(cp.stdout or "[]"),
                            key=lambda r: r["createdAt"], reverse=True):
                # timegm, NOT mktime: createdAt is UTC ("Z"), and mktime reads
                # the struct as LOCAL time — correct on a UTC box (hezza),
                # ~3600s early on a BST one (tube), where every run then fails
                # the freshness gate and the watch dies (seen 2x, 2026-07-06).
                created = calendar.timegm(time.strptime(
                    r["createdAt"], "%Y-%m-%dT%H:%M:%SZ"))
                # 30s grace: trigger->register lag plus clock skew.
                if created >= after_epoch - 30:
                    return str(r["databaseId"])
        time.sleep(delay)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="One-command shard release: bump, push, assemble, pull.")
    lvl = ap.add_mutually_exclusive_group()
    lvl.add_argument("--patch", dest="level", action="store_const", const="patch")
    lvl.add_argument("--minor", dest="level", action="store_const", const="minor")
    lvl.add_argument("--major", dest="level", action="store_const", const="major")
    # Line-buffer our own progress so it interleaves correctly with the
    # gh/git subprocesses' real-time output when stdout is a pipe (the skill
    # runs us piped). In a TTY Python line-buffers already; this fixes the pipe.
    sys.stdout.reconfigure(line_buffering=True)

    ap.set_defaults(level="patch")
    ap.add_argument("-m", "--message", help="commit message (default: chore(<plugin>): publish <version>)")
    ap.add_argument("--repo", type=Path, default=Path.cwd(),
                    help="source repo to publish (default: cwd)")
    ap.add_argument("--suite-repo", type=Path, default=SUITE_REPO_DEFAULT,
                    help="repo holding the suite version, the bump target "
                         "(default: this script's own repo; override for tests)")
    ap.add_argument("--no-wait", action="store_true",
                    help="trigger assemble but don't watch the run to green")
    ap.add_argument("--no-pull", action="store_true",
                    help="push only; don't bring this machine current")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan; touch nothing")
    args = ap.parse_args()
    dry = args.dry_run

    repo = args.repo.resolve()
    suite_repo = args.suite_repo.resolve()
    pj_path = repo / ".claude-plugin" / "plugin.json"
    if not pj_path.exists():
        die(f"no .claude-plugin/plugin.json under {repo} — not a plugin source repo")
    name = json.loads(pj_path.read_text())["name"]
    cli = CLI_REPOS.get(repo.name)

    # Single-version cutover (bds-suwoho): the bump target is ALWAYS the suite
    # version, which lives in batterie-de-savoir's plugin.json — never the cwd
    # repo's. The assembler stamps every vendored plugin to this one number, so
    # source repos' own plugin.json versions are local-dev-only: publishing bon
    # bumps the SUITE, not bon.
    suite_pj_path = suite_repo / ".claude-plugin" / "plugin.json"
    if not suite_pj_path.exists():
        die(f"no .claude-plugin/plugin.json under suite repo {suite_repo}")
    suite_text = suite_pj_path.read_text()
    suite_current = json.loads(suite_text)["version"]
    suite_new = bump_version(suite_current, args.level)
    is_suite = (repo == suite_repo)

    message = args.message or f"chore({name}): publish suite {suite_new}"
    suite_bump_msg = (f"chore(batterie): bump suite version to {suite_new}"
                      + ("" if is_suite else f" (carrying {name})"))

    print(f"Publish {name}: suite {suite_current} -> {suite_new}  ({args.level})")
    if is_suite:
        print(f"  repo:    {repo}  (== suite repo: one commit carries content + bump)")
    else:
        print(f"  content: {repo}")
        print(f"  suite:   {suite_repo}  (2-repo push: content first, then suite bump)")
    print(f"  commit:  {message!r}")
    print(f"  wait:    {'no' if args.no_wait else 'watch to green'}")
    print(f"  pull:    {'no' if args.no_pull else ('this machine' + (f' + reinstall {cli[0]}' if cli else ''))}")

    # What would be committed in the CONTENT repo — loud, because we stage
    # everything (-A) THERE so a one-step publish sweeps the content change.
    # The skill runs --dry-run first and shows this to a human before the real
    # run (bds-fifuko: never sweep unrelated WIP). The case-B suite bump is a
    # TARGETED plugin.json-only commit, so it can never sweep the suite repo's
    # own WIP — only the content repo gets -A.
    status = subprocess.run(["git", "-C", str(repo), "status", "--short"],
                            text=True, capture_output=True, check=False)
    pending = status.stdout.rstrip()
    print("  staging (git add -A in content repo) — these files plus the suite bump:")
    print("\n".join(f"    {ln}" for ln in pending.splitlines()) or "    (only the version bump)")

    # --- PUSH ---
    print("\n[push]")
    if is_suite:
        # One repo: the suite bump IS this repo's plugin.json; -A sweeps it
        # together with the content change in a single commit.
        if dry:
            print(f"  DRY  write suite version {suite_new} into {suite_pj_path}")
        else:
            suite_pj_path.write_text(replace_version(suite_text, suite_new))
        checked(run(["git", "-C", str(repo), "add", "-A"], dry=dry), "git add")
        checked(run(["git", "-C", str(repo), "commit", "-m", message], dry=dry,
                    capture=True), "git commit")
        checked(run(["git", "-C", str(repo), "push"], dry=dry, capture=True), "git push")
    else:
        # Two repos, content FIRST (bds-kodoli): if the suite bump (b) then
        # fails, the assembler quarantines the drifted content — a loud, caught
        # half-fail. The reverse (suite bumped, content unpushed) only re-ships
        # byte-identical content — harmless. So ordering makes the safe failure.
        # (a0) Lazy version convergence (bds-jomiwa): stamp the published
        # repo's own plugin.json to the suite version being minted, so its
        # CLI --version reads "the suite release that last changed this
        # repo". Only the repo BEING PUBLISHED is stamped — never siblings
        # (that would be the every-release multi-repo dance the japoca
        # decision rejected). The assembler stamps the VENDORED copy anyway;
        # this reaches the SOURCE copy that hatchling reads for the CLI.
        stamped = False
        content_pj = repo / ".claude-plugin" / "plugin.json"
        if content_pj.exists():
            pj_text = content_pj.read_text()
            if json.loads(pj_text).get("version") != suite_new:
                if dry:
                    print(f"  DRY  stamp suite version {suite_new} into {content_pj}")
                else:
                    content_pj.write_text(replace_version(pj_text, suite_new))
                stamped = True
        # (a) content repo — full -A sweep of the edit being shipped.
        if pending:
            checked(run(["git", "-C", str(repo), "add", "-A"], dry=dry), "git add (content)")
            checked(run(["git", "-C", str(repo), "commit", "-m", message], dry=dry,
                        capture=True), "git commit (content)")
            checked(run(["git", "-C", str(repo), "push"], dry=dry, capture=True), "git push (content)")
        elif stamped:
            # Tree was clean apart from the stamp we just wrote: commit it
            # TARGETED (never -A on a tree the caller left clean — bds-fifuko).
            # The push also carries any pre-committed unpushed content.
            checked(run(["git", "-C", str(repo), "commit", "-m", message,
                         "--", str(content_pj.relative_to(repo))], dry=dry,
                        capture=True), "git commit (version stamp)")
            checked(run(["git", "-C", str(repo), "push"], dry=dry, capture=True), "git push (content)")
        else:
            # No worktree changes — but a careful caller may have COMMITTED the
            # content by hand already. Skipping the push then ships a suite bump
            # while origin still holds the OLD content, and the eventual content
            # push drifts under an unbumped suite → ratchet quarantine at the
            # next assemble (seen live 2026-07-06: mise wheel fix vs 1.2.3).
            # Push anything already committed but unpushed.
            probe = subprocess.run(
                ["git", "-C", str(repo), "rev-list", "@{u}..HEAD", "--count"],
                text=True, capture_output=True, check=False,
            )
            ahead = (probe.stdout or "0").strip() if probe.returncode == 0 else "0"
            if ahead != "0":
                print(f"  ({repo.name}: {ahead} pre-committed unpushed commit(s) — pushing)")
                checked(run(["git", "-C", str(repo), "push"], dry=dry, capture=True), "git push (content)")
            else:
                print(f"  (no pending content in {repo.name} — suite bump only)")
        # (b) suite repo — TARGETED plugin.json-only commit (git commit -- PATH
        # commits that path's worktree state, ignoring any other staged/dirty
        # files in the suite repo; never -A here).
        suite_rel = str(suite_pj_path.relative_to(suite_repo))
        if dry:
            print(f"  DRY  write suite version {suite_new} into {suite_pj_path}")
        else:
            suite_pj_path.write_text(replace_version(suite_text, suite_new))
        checked(run(["git", "-C", str(suite_repo), "commit", "-m", suite_bump_msg,
                     "--", suite_rel], dry=dry, capture=True), "git commit (suite bump)")
        checked(run(["git", "-C", str(suite_repo), "push"], dry=dry, capture=True), "git push (suite)")

    print("\n[assemble]")
    trigger_epoch = time.time()
    checked(run(["gh", "-R", BATTERIE_REMOTE, "workflow", "run", WORKFLOW],
                dry=dry, capture=True), "workflow dispatch")

    if args.no_wait:
        print("  --no-wait: not watching. Check: "
              f"gh -R {BATTERIE_REMOTE} run watch <id> --exit-status")
    elif dry:
        print("  DRY  poll for the dispatched run, then: gh run watch <id> --exit-status")
    else:
        print("  waiting for the run to register...")
        run_id = find_run_id(trigger_epoch)
        if not run_id:
            die("triggered, but couldn't find the run to watch — check the "
                f"Actions tab for {BATTERIE_REMOTE}")
        print(f"  watching run {run_id} (assemble + lint; ~1-2 min)...")
        watch = subprocess.run(
            ["gh", "-R", BATTERIE_REMOTE, "run", "watch", run_id,
             "--exit-status", "--interval", "10"],
            text=True, check=False,
        )
        if watch.returncode != 0:
            die(f"assemble run {run_id} went RED — likely a version-ratchet "
                "quarantine (a plugin's content drifted without a bump). See: "
                f"gh -R {BATTERIE_REMOTE} run view {run_id} --log-failed")
        print("  green — shipped to the marketplace.")

    # --- PULL (this machine) ---
    if args.no_pull:
        print("\n[pull] skipped (--no-pull). When ready: /batterie:update")
    else:
        print("\n[pull] bringing this machine current")
        # Deliberately pinned to the public "batterie" marketplace — NOT the same
        # hardcode the /batterie:update and /batterie:version skills were freed of
        # (bds-lodita). Those are the *read/pull* side: they must see every plugin
        # installed locally, across any batterie-family marketplace. This is the
        # *push* side — it pushed one plugin to the single remote hardcoded above
        # (BATTERIE_REMOTE) and pulls that same plugin back from that marketplace.
        # Publishing to a private flavour would be a different remote + workflow
        # (a separate concern); generalising only this line would be incoherent.
        checked(run(["claude", "plugin", "marketplace", "update", "batterie"],
                    dry=dry, capture=True), "marketplace update")
        checked(run(["claude", "plugin", "update", f"{name}@batterie"],
                    dry=dry, capture=True), "plugin update")
        if cli:
            binary, extras = cli
            spec = f"{repo}{extras}"
            # --no-cache is load-bearing: uv reuses a cached *build* of the
            # local source and `uv cache clean` does NOT clear it, so a bump
            # that leaves src/ byte-identical (plugin.json-only) silently
            # reinstalls the old wheel (bon CLAUDE.md gotcha, verified
            # 2026-06-17). Install from the source tree, never installPath/PyPI.
            checked(run(["uv", "tool", "install", spec,
                         "--force", "--reinstall", "--no-cache"],
                        dry=dry, capture=True), f"reinstall {binary}")

    print("\nDone." + ("  (dry run — nothing changed)" if dry else ""))
    if not dry and not args.no_pull:
        print("Restart Claude Code (/exit then claude) to activate hook/skill "
              "changes — SessionStart hooks only fire on a full restart. "
              "(CLI reinstall is already live.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
