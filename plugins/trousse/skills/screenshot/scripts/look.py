#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyobjc-framework-Quartz"]
# ///
"""
Capture windows or screen to PNG files.

Usage:
    look.py [options] [output_path]
    look.py --list [--app NAME] [--categories] [--category NAME]

Options:
    --app NAME        Filter by application name (case-insensitive substring match)
    --title MATCH     Filter by window title (case-insensitive substring match)
    --list            List available windows instead of capturing
    --categories      Group window list by category (browsers, terminals, etc.)
    --category NAME   Filter to one category (browsers, terminals, editors, etc.)
    --screen          Capture entire screen instead of a window
    --max-size PX     Resize so largest dimension is at most PX (default: 1568)
    --native          Skip resizing, keep native resolution

Categories: browsers, terminals, editors, communication, documents, media, other

If no output path given, generates timestamped filename in current directory.

Examples:
    look.py                              # Capture frontmost window
    look.py --app Ghostty                # Capture Ghostty window
    look.py --title "LinkedIn"           # Capture window with LinkedIn in title
    look.py --screen                     # Capture entire screen
    look.py --list                       # List all windows
    look.py --list --categories          # List windows grouped by type
    look.py --list --category browsers   # List only browser windows
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime

# Max dimension for resizing. 1568px is optimal for Claude's vision API:
# - Images larger than this get resized server-side anyway
# - Pre-resizing avoids upload latency while preserving fidelity
# - Results in ~1,600 tokens per image
DEFAULT_MAX_SIZE = 1568

from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionAll,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
)


# App name -> category mapping (case-insensitive matching)
APP_CATEGORIES = {
    # Browsers
    'browsers': [
        'Google Chrome', 'Safari', 'Firefox', 'Arc', 'Brave Browser',
        'Microsoft Edge', 'Opera', 'Vivaldi', 'Chromium', 'Orion',
    ],
    # Terminals
    'terminals': [
        'Ghostty', 'Terminal', 'iTerm2', 'iTerm', 'Warp', 'Alacritty',
        'Hyper', 'kitty', 'WezTerm', 'Tabby',
    ],
    # Code editors
    'editors': [
        'Code', 'Visual Studio Code', 'Cursor', 'Sublime Text', 'Atom',
        'TextMate', 'BBEdit', 'Nova', 'Xcode', 'IntelliJ IDEA',
        'PyCharm', 'WebStorm', 'Android Studio', 'Zed',
    ],
    # Communication
    'communication': [
        'Slack', 'Microsoft Teams', 'Messages', 'Mail', 'Outlook',
        'Discord', 'Zoom', 'Telegram', 'WhatsApp', 'Signal',
        'FaceTime', 'Webex',
    ],
    # Documents and files
    'documents': [
        'Preview', 'Finder', 'Pages', 'Numbers', 'Keynote',
        'Microsoft Word', 'Microsoft Excel', 'Microsoft PowerPoint',
        'Adobe Acrobat', 'PDF Expert', 'Notes', 'TextEdit',
    ],
    # Media
    'media': [
        'Photos', 'Music', 'Spotify', 'VLC', 'QuickTime Player',
        'IINA', 'Plex', 'Apple TV', 'Podcasts',
    ],
}

# Build reverse lookup: app name -> category
_APP_TO_CATEGORY = {}
for category, apps in APP_CATEGORIES.items():
    for app in apps:
        _APP_TO_CATEGORY[app.lower()] = category

VALID_CATEGORIES = list(APP_CATEGORIES.keys()) + ['other']


def get_category(app_name):
    """Get category for an app name."""
    return _APP_TO_CATEGORY.get(app_name.lower(), 'other')


def get_windows(app_filter=None, title_filter=None, on_screen_only=False, category_filter=None):
    """Get list of capturable windows using CGWindowList (no AppleScript)."""
    windows = []
    options = kCGWindowListOptionOnScreenOnly if on_screen_only else kCGWindowListOptionAll
    window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

    for window in window_list:
        owner = window.get('kCGWindowOwnerName', '')
        name = window.get('kCGWindowName', '')
        wid = window.get('kCGWindowNumber', 0)
        layer = window.get('kCGWindowLayer', 0)
        bounds = window.get('kCGWindowBounds', {})

        # Only main windows (layer 0) with reasonable size
        # Filter out small panels, popovers, web inspectors (min 600x400)
        width = bounds.get('Width', 0)
        height = bounds.get('Height', 0)
        if layer == 0 and width >= 600 and height >= 400:
            # Apply filters
            if app_filter and app_filter.lower() not in owner.lower():
                continue
            if title_filter and title_filter.lower() not in name.lower():
                continue

            category = get_category(owner)
            if category_filter and category != category_filter:
                continue

            windows.append({
                'id': wid,
                'app': owner,
                'title': name or '(untitled)',
                'width': int(width),
                'height': int(height),
                'x': int(bounds.get('X', 0)),
                'y': int(bounds.get('Y', 0)),
                'category': category,
            })

    return windows


def capture_screen(output_path, main_only=True):
    """Capture entire screen using screencapture."""
    cmd = ['screencapture', '-x']
    if main_only:
        cmd.append('-m')
    cmd.append(output_path)

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def capture_window(window_id, output_path):
    """Capture a specific window by ID using screencapture."""
    cmd = ['screencapture', '-x', '-o', f'-l{window_id}', output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def resize_image(path, max_size):
    """Resize image so largest dimension is at most max_size using sips."""
    cmd = ['sips', '--resampleHeightWidthMax', str(max_size), path, '--out', path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def generate_filename(prefix="screenshot"):
    """Generate timestamped filename."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    return f"{timestamp}-{prefix}.png"


def main():
    parser = argparse.ArgumentParser(
        description='Capture windows or screen to PNG files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('output', nargs='?', help='Output PNG path (auto-generated if omitted)')
    parser.add_argument('--app', help='Filter by application name')
    parser.add_argument('--title', help='Filter by window title')
    parser.add_argument('--list', action='store_true', help='List available windows')
    parser.add_argument('--categories', action='store_true', help='Group window list by category')
    parser.add_argument('--category', choices=VALID_CATEGORIES, help='Filter to one category')
    parser.add_argument('--screen', action='store_true', help='Capture entire screen')
    parser.add_argument('--max-size', type=int, default=DEFAULT_MAX_SIZE, help=f'Max dimension in pixels (default: {DEFAULT_MAX_SIZE})')
    parser.add_argument('--native', action='store_true', help='Keep native resolution (skip resize)')

    args = parser.parse_args()

    # List mode
    if args.list or args.categories or args.category:
        windows = get_windows(
            app_filter=args.app,
            title_filter=args.title,
            category_filter=args.category
        )
        if not windows:
            filter_desc = []
            if args.app:
                filter_desc.append(f"app='{args.app}'")
            if args.title:
                filter_desc.append(f"title='{args.title}'")
            if args.category:
                filter_desc.append(f"category='{args.category}'")
            print(f"No windows found" + (f" matching {', '.join(filter_desc)}" if filter_desc else ""))
            return 1

        # Grouped output by category
        if args.categories:
            from collections import defaultdict
            by_category = defaultdict(list)
            for w in windows:
                by_category[w['category']].append(w)

            # Print in consistent order
            for cat in VALID_CATEGORIES:
                if cat in by_category:
                    print(f"\n{cat.title()}:")
                    for w in by_category[cat]:
                        print(f"  [{w['id']}] {w['app']}: {w['title']} ({w['width']}x{w['height']})")
            print(f"\nTotal: {len(windows)} windows")
        else:
            # Flat output
            print(f"Available windows ({len(windows)}):")
            for w in windows:
                print(f"  [{w['id']}] {w['app']}: {w['title']} ({w['width']}x{w['height']})")
        return 0

    # Generate output path if not provided
    output_path = args.output
    if not output_path:
        # Default to /tmp/claude-screenshots/ for ephemeral captures
        # Use explicit path for persistent/documentation captures
        tmp_dir = '/tmp/claude-screenshots'
        os.makedirs(tmp_dir, exist_ok=True)
        prefix = "screen" if args.screen else (args.app or args.title or "window")
        # Sanitize prefix for filename
        prefix = "".join(c if c.isalnum() or c in '-_' else '-' for c in prefix.lower())
        output_path = os.path.join(tmp_dir, generate_filename(prefix))

    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Capture
    if args.screen:
        print(f"Capturing screen...")
        success = capture_screen(output_path)
        if not success:
            print("Failed to capture screen", file=sys.stderr)
            return 1
    else:
        # Find target window
        windows = get_windows(app_filter=args.app, title_filter=args.title)
        if not windows:
            filter_desc = []
            if args.app:
                filter_desc.append(f"app='{args.app}'")
            if args.title:
                filter_desc.append(f"title='{args.title}'")
            print(f"No windows found" + (f" matching {', '.join(filter_desc)}" if filter_desc else ""))
            return 1

        # Take first match (could add interactive selection later)
        window = windows[0]
        print(f"Capturing: {window['app']} - {window['title']} ({window['width']}x{window['height']})")

        success = capture_window(window['id'], output_path)
        if not success:
            print("Failed to capture window - check Screen Recording permissions", file=sys.stderr)
            return 1

    # Resize if needed
    if not args.native and args.max_size:
        resize_image(output_path, args.max_size)

    # Report result
    size = os.path.getsize(output_path)
    print(f"Saved: {output_path} ({size:,} bytes)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
