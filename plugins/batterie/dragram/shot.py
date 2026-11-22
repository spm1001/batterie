# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""dragram — proprioception: render a scenario to PNG and read back its state contract.

drag.js emits a JSON state contract into <script id="dragram-state"> on every relayout.
This reads it via `chromium --headless --dump-dom` (no deps, no Playwright) and screenshots
via `--screenshot` — giving Claude both pixels and precise *computed* geometry (block heights
are content-driven, so they can't be read from the .html alone) without a human looking.

The render runs from a file:// URL with NO ?edit — so no server is needed and no editor chrome
leaks into the shot. (serve.py is only for live drag-to-persist co-editing.)

Usage:
  uv run shot.py example             # state report + a PNG (path printed)
  uv run shot.py example --state     # state report only (no screenshot — faster)
  uv run shot.py example --png       # screenshot only
  uv run shot.py --comments          # every open comment the person left, across all diagrams (no browser)
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
import shutil
CHROMIUM = next((b for b in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")
                 if shutil.which(b)), "chromium")  # hezza had chromium; tube has google-chrome (2026-08-12)
MARK = {"ok": "✅", "fail": "❌", "warn": "⚠️", "probe": "\U0001f50d"}


def resolve(arg: str) -> Path:
    """Accept a full filename or a fuzzy fragment (e.g. 'example' or 'scenario-1')."""
    p = BASE / arg
    if p.is_file():
        return p
    hits = sorted(BASE.glob(f"*{arg}*.html"))
    have = [f.name for f in sorted(BASE.glob("*.html"))]
    if not hits:
        sys.exit(f"no scenario matching {arg!r}. have: {have}")
    if len(hits) > 1:
        sys.exit(f"ambiguous {arg!r}: {[f.name for f in hits]}")
    return hits[0]


def run_chromium(extra: list[str], url: str) -> str:
    r = subprocess.run(
        [CHROMIUM, "--headless", "--no-sandbox", *extra, url],
        capture_output=True, text=True, timeout=90,
    )
    return r.stdout


def dump_state(url: str) -> dict:
    dom = run_chromium(["--dump-dom"], url)
    m = re.search(r'<script[^>]*id="dragram-state"[^>]*>(.*?)</script>', dom, re.S)
    if not m:
        sys.exit("no #dragram-state in the dumped DOM — is drag.js emitting the contract?")
    return json.loads(m.group(1))


def out_dir() -> Path:
    """Honour $CLAUDE_JOB_DIR/tmp (bg jobs share /tmp and clobber each other)."""
    base = Path(os.environ.get("CLAUDE_JOB_DIR", "/tmp"))
    cand = base / "tmp"
    return cand if cand.is_dir() else (base if base.is_dir() else Path("/tmp"))


def report(state: dict) -> None:
    rendered = sum(1 for w in state["wires"] if w["rendered"])
    print(f"VERDICT  {state['verdict']}   "
          f"({len(state['nodes'])} nodes · {rendered}/{len(state['wires'])} wires drawn · "
          f"stage {state['stage']['w']}x{state['stage']['h']})")
    for c in state["checks"]:
        line = f"  {MARK.get(c['status'], '?')} {c['id']}: {c['description']}"
        if c.get("detail"):
            line += f"\n       -> {c['detail']}"
        print(line)
    print()
    print(json.dumps(state, indent=2, ensure_ascii=False))


def list_comments() -> None:
    """Open point-and-comment notes (data-comment) in every .html here, subfolders included — text
    only, no browser. Read with serve.py's own tag reader, so the listing and the writer agree.
    Resolve one by making the change and deleting its data-comment attribute."""
    import importlib.util
    from html import unescape
    spec = importlib.util.spec_from_file_location("dragram_serve", BASE / "serve.py")
    serve = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serve)
    found = 0
    for f in sorted(BASE.rglob("*.html")):
        for _, _, tag, at in serve.iter_tags(f.read_text(encoding="utf-8")):
            if "data-comment" not in at:
                continue
            v = lambda name: unescape(tag[at[name][0]:at[name][1]]) if name in at else "?"
            text = "\n".join("    " + line for line in v("data-comment").split("\n"))  # indented: can't fake a row
            print(f"{f.relative_to(BASE)}  #{v('id')}\n{text}")
            found += 1
    print(f"{found} open comment{'s' if found != 1 else ''}" +
          (" — resolve each by making the change and deleting its data-comment" if found else ""))


def main() -> None:
    try:  # force UTF-8 so the ✅/⚠️ marks never crash on a non-UTF-8 stdout (pipes, cron)
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    argv = sys.argv[1:]
    names = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if "--comments" in flags:
        list_comments()
        return
    if not names:
        sys.exit("usage: shot.py <scenario> [--state | --png]   |   shot.py --comments")

    f = resolve(names[0])
    url = f"file://{f}"
    do_png = "--state" not in flags
    do_state = "--png" not in flags

    state = dump_state(url)  # always — also carries the stage dims the screenshot needs
    if state.get("comments"):  # every mode says so, --png included: a render with open notes is a draft
        n = len(state["comments"])
        print(f"⚠️  {n} open comment{'s' if n != 1 else ''} in this diagram — a draft until resolved "
              f"(uv run shot.py --comments)\n")

    if do_png:
        w = state["stage"]["w"] or 1720
        h = state["stage"]["h"] or 1080
        dest = out_dir() / f"{f.stem}.png"
        run_chromium([f"--screenshot={dest}", f"--window-size={w},{h}",
                      "--force-device-scale-factor=2"], url)
        size = dest.stat().st_size if dest.exists() else 0
        print(f"PNG   {dest}   ({w}x{h} @2x, {size // 1024} KB)\n")

    if do_state:
        report(state)


if __name__ == "__main__":
    main()
