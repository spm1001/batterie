#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Leak scan for the public shelf (bds-tevuhe, W3 of the estate rebuild).

The source repos stay private because their history names people; this repo is
public, and assemble.sh copies whatever the sources ship into it. So before the
assembled tree can be committed, every text file in it is scanned for what must
never reach a stranger: email addresses, OAuth client ids and secrets, tokens,
private keys, ITV hostnames, and the personal terms (people, private repos) in a
list that is itself private.

Built on the sharing scanner's patterns (trousse skill-forge scripts/scan.py),
narrowed to what can be judged without a human and run on every assemble.

Two properties keep it honest, both measured on every run:
  * A CANARY SELF-TEST first. Each pattern class, and the personal-terms layer
    when a term list is supplied, is fed a synthetic positive; if any class
    fails to fire, the scan fails before it scans anything. A scanner that has
    never gone red has never been tested, and one that silently stopped matching
    would pass every real leak.
  * An ALLOWLIST with a reason on every line (leak-scan-allow.txt). A hit it
    does not name fails the run; an allow line that matched nothing is reported,
    so stale entries surface instead of quietly widening the gate.

The personal-terms list comes from LEAK_SCAN_TERMS (a file path; CI materialises
it from an Actions secret). Without it that layer is inert, and the scan says so
on every run rather than passing in silence.

Usage: leak-scan.py <dir> [<dir> …]     exit 0 clean, 1 on a leak or a failed self-test
"""
import fnmatch
import os
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALLOW_FILE = HERE / "leak-scan-allow.txt"

PATTERNS = {
    # id: (regex, synthetic positive for the self-test)
    "email": (r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])",
              "write to canary.person@example-leak.org today"),
    "oauth-client-id": (r"\b\d{6,}-[a-z0-9]{20,}\.apps\.googleusercontent\.com\b",
                        "client 123456789012-abcdefghijklmnopqrstuvwxyz012345.apps.googleusercontent.com"),
    "oauth-client-secret": (r"\bGOCSPX-[A-Za-z0-9_-]{10,}", "secret GOCSPX-CanaryCanaryCanary12"),
    "github-token": (r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "token ghp_" + "C" * 36),
    "slack-token": (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", "slack xoxb-canary-canary-canary"),
    "anthropic-key": (r"\bsk-ant-[A-Za-z0-9_-]{20,}", "key sk-ant-canarycanarycanarycanary"),
    "private-key": (r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----"),
    "itv-host": (r"(?i)\b(?:[a-z0-9-]+\.)+itv\.com\b", "see https://Canary-Internal.ITV.com/wiki"),
}
# RFC 2606 documentation domains are never a leak: examples and tests use them
# on purpose. Anything else a doc invents (company.com, app.com…) goes on the
# allowlist by name, so each one was looked at once.
DOC_DOMAINS = re.compile(r"@(?:[a-z0-9-]+\.)*example\.(?:com|org|net)$", re.I)
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".pyc"}
# Wheels carry the private repos' source, so they are opened and their text
# members scanned, reported as <wheel>!<member>. uv.lock is scanned like any file.


def load_terms():
    path = os.environ.get("LEAK_SCAN_TERMS")
    if not path:
        # Locally an inert personal-term layer is a stated gap; in CI it would be
        # a green run that never checked the one class only a private list can
        # catch, so CI refuses to run without it (essayeur finding, 27 Sep).
        if os.environ.get("CI") == "true":
            sys.exit("FAIL: leak-scan — LEAK_SCAN_TERMS is not set in CI; add the LEAK_SCAN_TERMS_TXT secret (one private term per line)")
        return None
    terms = [l.strip() for l in Path(path).read_text().splitlines()]
    return [t for t in terms if t and not t.startswith("#")]


def compile_all(terms):
    rx = {pid: re.compile(p) for pid, (p, _) in PATTERNS.items()}
    if terms:
        # A space in a term also matches '.', '_' or '-', so "Jo Bloggs" catches
        # jo.bloggs@, jo_bloggs and jo-bloggs (a dotted address slipped through, 27 Sep).
        alts = (re.escape(t).replace(r"\ ", r"[\s._-]") for t in terms)
        rx["personal-term"] = re.compile(r"(?i)(?<![\w-])(?:" + "|".join(alts) + r")(?![\w-])")
    return rx


def self_test(rx, terms):
    samples = {pid: s for pid, (_, s) in PATTERNS.items()}
    if terms:
        samples["personal-term"] = f"a note about {terms[0]} here"
        spaced = next((t for t in terms if " " in t), None)
        if spaced:
            samples["personal-term (dotted)"] = f"mail {spaced.replace(' ', '.')}@example.com"
            rx = {**rx, "personal-term (dotted)": rx["personal-term"]}
    missed = [pid for pid, s in samples.items() if not rx[pid].search(s)]
    if missed:
        print(f"FAIL: leak-scan self-test — no match on the canary for: {', '.join(missed)}", file=sys.stderr)
        return False
    print(f"  OK leak-scan self-test: {len(samples)} classes fired on their canaries"
          + ("" if terms else " (personal-term layer INERT: LEAK_SCAN_TERMS not set)"))
    return True


def load_allow():
    rules = []
    for n, line in enumerate(ALLOW_FILE.read_text().splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4 or not parts[3].strip():
            sys.exit(f"FAIL: {ALLOW_FILE.name}:{n} needs four tab-separated fields: glob, class, match, reason")
        glob, cls, match = parts[0], parts[1], parts[2]
        if cls == "*":
            sys.exit(f"FAIL: {ALLOW_FILE.name}:{n} names class '*' — an allow line must name the one class it accepts")
        if match == "*" and "*" in glob.rsplit("/", 1)[-1]:
            sys.exit(f"FAIL: {ALLOW_FILE.name}:{n} accepts any match in files matching {glob!r} — a match of '*' needs a glob naming one file")
        rules.append({"glob": glob, "cls": cls, "match": match, "reason": parts[3], "line": n, "used": 0})
    return rules


def allowed(rules, rel, cls, text):
    for r in rules:
        if fnmatch.fnmatch(rel, r["glob"]) and r["cls"] in (cls, "*") and (r["match"] in ("*", text)):
            r["used"] += 1
            return True
    return False


def canaries_not_allowlisted(rules, rx, terms):
    """The allowlist must not be able to admit a canary: otherwise one broad line
    silences a class while the self-test above still reports it firing."""
    samples = {pid: s for pid, (_, s) in PATTERNS.items()}
    if terms:
        samples["personal-term"] = f"a note about {terms[0]} here"
    leaked = []
    for pid, s in samples.items():
        hit = rx[pid].search(s).group(0)
        if any(fnmatch.fnmatch("canary/probe.md", r["glob"]) and r["cls"] == pid and r["match"] in ("*", hit)
               for r in rules):
            leaked.append(pid)
    if leaked:
        print(f"FAIL: leak-scan — the allowlist would admit the canary for: {', '.join(leaked)}", file=sys.stderr)
        return False
    return True


def texts(base):
    """(relative name, text) for every scannable file under base, wheel members included."""
    for f in sorted(base.rglob("*")):
        if not f.is_file() or f.suffix in SKIP_SUFFIXES or ".git" in f.parts:
            continue
        rel = f"{base.name}/{f.relative_to(base)}"
        if f.suffix == ".whl":
            with zipfile.ZipFile(f) as z:
                for member in z.namelist():
                    try:
                        yield f"{rel}!{member}", z.read(member).decode()
                    except UnicodeDecodeError:
                        continue
            continue
        try:
            yield rel, f.read_text()
        except (UnicodeDecodeError, OSError):
            continue


def main(dirs):
    terms = load_terms()
    rx = compile_all(terms)
    if not self_test(rx, terms):
        return 1
    rules = load_allow()
    if not canaries_not_allowlisted(rules, rx, terms):
        return 1
    hits, scanned = [], 0
    for d in dirs:
        base = Path(d)
        items = [(base.name, base.read_text())] if base.is_file() else texts(base)
        for rel, text in items:
            scanned += 1
            for n, line in enumerate(text.splitlines(), 1):
                for cls, r in rx.items():
                    for m in r.finditer(line):
                        if cls == "email" and DOC_DOMAINS.search(m.group(0)):
                            continue
                        if not allowed(rules, rel, cls, m.group(0)):
                            hits.append(f"{rel}:{n}: [{cls}] {m.group(0)}")
    for r in rules:
        if not r["used"]:
            print(f"  WARN {ALLOW_FILE.name}:{r['line']} matched nothing this run — stale? ({r['glob']} {r['cls']})")
    if hits:
        print(f"FAIL: leak-scan — {len(hits)} hit(s) in {scanned} files not on the allowlist:", file=sys.stderr)
        for h in hits[:200]:
            print(f"  {h}", file=sys.stderr)
        return 1
    print(f"  OK leak-scan: {scanned} files clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) if len(sys.argv) > 1 else "usage: leak-scan.py <dir> [<dir> …]")
