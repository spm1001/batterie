#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Scan which ad / martech / analytics tags fire on a website.

Drives a clean headless Chrome on this host (DoH straight to 1.1.1.1, set by a
machine-wide managed policy) so ControlD DNS filtering and uBlock can't hide the
ad-tech. Captures all network requests via `passe`, then groups the domains by
vendor against a known taxonomy and flags anything it doesn't recognise for you
to identify by hand.

Usage:
    tag_scan.py URL [options]

Options:
    --accept "TEXT"   Click a cookie-banner button with this visible text before
                      capturing (e.g. "Accept all cookies"). Scout the real text
                      first with: passe --cdp http://127.0.0.1:PORT run -c
                      'goto URL; ax-find button'. Omit to capture the pre-consent state.
    --wait N          Seconds to wait after accept for tags to fire (default: 8).
    --port N          CDP port for the DoH Chrome instance (default: 9333).
    --out FILE        Where to write the raw capture jsonl (default: a temp file).
    --screenshot FILE Save a post-capture screenshot (JPEG).
    --json            Emit the grouped result as JSON instead of a text report.

Examples:
    tag_scan.py https://www.virginmedia.com/ --accept "Accept all cookies"
    tag_scan.py https://example.com --json
    tag_scan.py https://shop.example.com --accept "I Accept" --wait 12 --screenshot /tmp/s.jpg

Precondition: the DoH managed policy must be installed (see SKILL.md). The script
checks for it and tells you the one-line fix if it's missing.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections import defaultdict
from urllib.parse import urlsplit

POLICY_PATH = "/etc/chromium/policies/managed/doh-escape-hatch.json"
PROFILE_DIR = os.path.expanduser("~/.chromium-doh")

# Convenience labelling subset. NOT canonical — the full, human-maintained
# taxonomy lives in ../references/tag-taxonomy.md. Anything unmatched here is
# reported as UNKNOWN so you investigate it (that's the point of the tool).
# Matched by substring against the request's registrable-ish hostname.
TAXONOMY = [
    # (substring, vendor, category)
    ("googletagmanager.com", "Google Tag Manager", "Tag management"),
    ("cookielaw.org", "OneTrust (CMP)", "Consent / CMP"),
    ("onetrust.com", "OneTrust (CMP)", "Consent / CMP"),
    ("consensu.org", "IAB TCF CMP", "Consent / CMP"),
    ("cookiebot.com", "Cookiebot (CMP)", "Consent / CMP"),
    ("google-analytics.com", "Google Analytics (GA4)", "Analytics"),
    ("analytics.google.com", "Google Analytics (GA4)", "Analytics"),
    ("stats.g.doubleclick.net", "Google Analytics → DoubleClick", "Analytics"),
    ("omtrdc.net", "Adobe Analytics", "Analytics"),
    ("demdex.net", "Adobe Audience Manager", "CDP / identity"),
    ("segment.com", "Segment", "CDP / identity"),
    ("segment.io", "Segment", "CDP / identity"),
    ("zeotap.com", "Zeotap", "CDP / identity"),
    ("rlcdn.com", "LiveRamp", "CDP / identity"),
    ("id5-sync.com", "ID5", "CDP / identity"),
    ("connect.facebook.net", "Meta Pixel", "Paid-media pixel"),
    ("facebook.com/tr", "Meta Pixel", "Paid-media pixel"),
    ("bat.bing.com", "Microsoft / Bing UET", "Paid-media pixel"),
    ("analytics.tiktok.com", "TikTok Pixel", "Paid-media pixel"),
    ("ads.tiktok.com", "TikTok Ads", "Paid-media pixel"),
    ("licdn.com", "LinkedIn Insight", "Paid-media pixel"),
    ("snapchat.com", "Snap Pixel", "Paid-media pixel"),
    ("sc-static.net", "Snap Pixel", "Paid-media pixel"),
    ("pinterest", "Pinterest Tag", "Paid-media pixel"),
    ("googleadservices.com", "Google Ads", "Paid-media pixel"),
    ("googlesyndication.com", "Google Ads / AdSense", "Paid-media pixel"),
    ("g.doubleclick.net", "Google / DoubleClick", "Paid-media pixel"),
    ("adnxs.com", "Xandr / AppNexus", "Programmatic"),
    ("creativecdn.com", "RTB House", "Programmatic"),
    ("criteo", "Criteo", "Programmatic"),
    ("adsrvr.org", "The Trade Desk", "Programmatic"),
    ("casalemedia.com", "Index Exchange", "Programmatic"),
    ("pubmatic.com", "PubMatic", "Programmatic"),
    ("rubiconproject.com", "Magnite / Rubicon", "Programmatic"),
    ("openx.net", "OpenX", "Programmatic"),
    ("taboola.com", "Taboola", "Programmatic"),
    ("outbrain.com", "Outbrain", "Programmatic"),
    ("dwin1.com", "Awin (affiliate)", "Affiliate"),
    ("awin1.com", "Awin (affiliate)", "Affiliate"),
    ("roeye.com", "R.O.EYE Lantern (affiliate)", "Affiliate"),
    ("roeyecdn.com", "R.O.EYE Lantern (affiliate)", "Affiliate"),
    ("prf.hn", "Impact / Partnerize (affiliate)", "Affiliate"),
    ("tradedoubler.com", "Tradedoubler (affiliate)", "Affiliate"),
    ("linksynergy.com", "Rakuten (affiliate)", "Affiliate"),
    ("webgains.com", "Webgains (affiliate)", "Affiliate"),
    ("optimizely.com", "Optimizely", "Experience / testing"),
    ("contentsquare.net", "Contentsquare", "Experience / testing"),
    ("hotjar.com", "Hotjar", "Experience / testing"),
    ("fullstory.com", "FullStory", "Experience / testing"),
    ("mouseflow.com", "Mouseflow", "Experience / testing"),
    ("glassbox", "Glassbox", "Experience / testing"),
    ("dynamicyield.com", "Dynamic Yield", "Experience / testing"),
    ("visualwebsiteoptimizer.com", "VWO", "Experience / testing"),
    ("qualtrics.com", "Qualtrics (survey)", "Survey / feedback"),
    ("medallia.com", "Medallia (survey)", "Survey / feedback"),
    ("usabilla.com", "Usabilla (survey)", "Survey / feedback"),
    ("speedcurve.com", "SpeedCurve (RUM)", "Performance RUM"),
    ("nr-data.net", "New Relic (RUM)", "Performance RUM"),
    ("newrelic.com", "New Relic (RUM)", "Performance RUM"),
    ("browser-intake", "Datadog RUM", "Performance RUM"),
    ("sentry", "Sentry", "Performance RUM"),
    ("jquery.com", "jQuery (library)", "Infra / libs"),
    ("jsdelivr.net", "jsDelivr CDN", "Infra / libs"),
    ("unpkg.com", "unpkg CDN", "Infra / libs"),
    ("storyblok", "Storyblok (CMS)", "Infra / libs"),
]


def cdp_up(port: int) -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
        return True
    except Exception:
        return False


def ensure_chrome(port: int) -> None:
    """Launch a headless DoH Chrome on `port` if one isn't already there."""
    if cdp_up(port):
        return
    chromium = (
        subprocess.run(["which", "chromium"], capture_output=True, text=True).stdout.strip()
        or "chromium"
    )
    os.makedirs(PROFILE_DIR, exist_ok=True)
    log = open(os.path.join(tempfile.gettempdir(), f"tamis-chrome-{port}.log"), "ab")
    subprocess.Popen(
        [
            chromium,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={PROFILE_DIR}",
            "--disable-gpu",
            "--window-size=1440,900",
            "about:blank",
        ],
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    for _ in range(20):
        time.sleep(0.5)
        if cdp_up(port):
            return
    sys.exit(f"tamis: Chrome did not come up on port {port} — see {log.name}")


def run_capture(url, port, accept, wait, out, screenshot):
    steps = [f"capture --bodies {out}", f"goto {url}", "wait 3"]
    if accept:
        steps += [f'click "{accept}"', f"wait {wait}"]
    else:
        steps.append(f"wait {wait}")
    if screenshot:
        steps.append(f"screenshot --fast {screenshot}")
    script = "\n".join(steps) + "\n"
    proc = subprocess.run(
        ["passe", "--cdp", f"http://127.0.0.1:{port}", "run", "-"],
        input=script,
        capture_output=True,
        text=True,
    )
    return proc.stderr  # passe prints the capture summary to stderr


def classify(host):
    for sub, vendor, cat in TAXONOMY:
        if sub in host:
            return vendor, cat
    return None, None


def main():
    ap = argparse.ArgumentParser(description="Scan ad/martech/analytics tags on a site.")
    ap.add_argument("url")
    ap.add_argument("--accept")
    ap.add_argument("--wait", type=int, default=8)
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--out")
    ap.add_argument("--screenshot")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(POLICY_PATH):
        print(
            "tamis: DoH policy missing — ControlD will hide the ad-tech.\n"
            "Install it (once, needs sudo):\n"
            f"  echo '{{\"DnsOverHttpsMode\":\"secure\",\"DnsOverHttpsTemplates\":\"https://1.1.1.1/dns-query\"}}' "
            f"| sudo tee {POLICY_PATH}\n"
            "Then re-run. (Without it, blocked domains resolve to 0.0.0.0.)",
            file=sys.stderr,
        )
        sys.exit(2)

    ensure_chrome(args.port)
    out = args.out or tempfile.mkstemp(prefix="tamis-", suffix=".jsonl")[1]
    summary = run_capture(args.url, args.port, args.accept, args.wait, out, args.screenshot)

    hosts = {}  # host -> count
    consent = None
    with open(out) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                u = json.loads(line).get("url", "")
            except json.JSONDecodeError:
                continue
            if not u:
                continue
            h = urlsplit(u).netloc.lower()
            if h:
                hosts[h] = hosts.get(h, 0) + 1
            if "gcs=G100" in u and consent is None:
                consent = "denied (G100)"
            if "gcs=G111" in u:
                consent = "granted (G111)"

    by_cat = defaultdict(list)
    unknown = []
    for h in sorted(hosts):
        vendor, cat = classify(h)
        if vendor:
            by_cat[cat].append((h, vendor, hosts[h]))
        else:
            unknown.append((h, hosts[h]))

    if args.json:
        print(json.dumps({
            "url": args.url,
            "consent": consent,
            "requests": sum(hosts.values()),
            "unique_hosts": len(hosts),
            "by_category": {c: [{"host": h, "vendor": v, "hits": n} for h, v, n in rows]
                            for c, rows in by_cat.items()},
            "unknown": [{"host": h, "hits": n} for h, n in unknown],
            "capture_file": out,
        }, indent=2))
        return

    print(f"\n=== Tag scan: {args.url} ===")
    print(f"vantage: this host (DoH→1.1.1.1) — geo-targeted tags may differ; see SKILL.md")
    if consent:
        print(f"consent state observed: {consent}")
    print(f"{sum(hosts.values())} requests, {len(hosts)} unique hosts\n")
    for cat in sorted(by_cat):
        print(f"## {cat}")
        for h, v, n in sorted(by_cat[cat], key=lambda r: -r[2]):
            print(f"  {v:<34} {h}  ({n})")
        print()
    if unknown:
        print("## UNKNOWN — identify by hand (fetch the script, web-search the domain)")
        for h, n in sorted(unknown, key=lambda r: -r[1]):
            print(f"  {h}  ({n})")
        print()
    print(f"raw capture: {out}")
    if summary and "requests" in summary:
        pass  # passe's own summary already went to our stderr stream


if __name__ == "__main__":
    main()
