"""
Guards that keep the trailing-contact-block rule off machine-generated mail.

talon_signature._strip_trailing_contact_block cuts everything below a short
"name block" when 3+ URLs follow it. That discriminator is inverted for SaaS
notification mail (Microsoft, Atlassian, GitHub, Google): there the trailing
URLs ARE the content — the call to action, the account link. A Microsoft
invitation lost its Accept-invitation link and 4 of its 5 real links to it,
silently, because 41% of the characters survived the ratio test (mise-kubolo,
2026-09-23). Split from talon_signature.py, which is size-ratcheted; the
catastrophic-strip revert lives here for the same reason.
"""

import re

# A markdown link with anchor text, not an image: '[Accept invitation](https://...'.
# Only HTML-converted bodies carry these; a plain-text signature's links are bare.
_ANCHORED_LINK = re.compile(r'(?<!!)\[[^\]\n]*[A-Za-z][^\]\n]*\]\(https?://')
_LETTER = re.compile(r'[A-Za-z]')


def has_anchored_link(text: str) -> bool:
    """True when the text holds a call-to-action style link with anchor text."""
    return bool(_ANCHORED_LINK.search(text))


def is_texty(line: str) -> bool:
    """A name/title line has letters and is not markdown table furniture ('|  |')."""
    return bool(_LETTER.search(line)) and not line.startswith('|')


_URL_HOST = re.compile(r'https?://(?:www\.)?([^/\s)>|\]]+)')


def link_loss_warnings(discarded: str) -> list[str]:
    """Name the links a signature strip threw away, whatever the character ratio.

    A ratio test cannot see this loss: the invitation kept 41% of its
    characters and 1 of 6 links (mise-kubolo). Real contact blocks will warn
    too; the hosts let the reader tell a LinkedIn footer from a call to action.
    """
    hosts = list(dict.fromkeys(_URL_HOST.findall(discarded)))
    if not hosts:
        return []
    return [
        f"Signature strip removed a trailing block holding {len(_URL_HOST.findall(discarded))} "
        f"link(s) ({', '.join(hosts[:5])}{', ...' if len(hosts) > 5 else ''}). If those were "
        "content, not a contact block, read the message in Gmail."
    ]


# Catastrophic-strip REVERT thresholds (mise-rejula, 2026-07). Warning alone
# wasn't enough: a single-message briefing was cut to 6% at an early section
# header and the eaten body was unrecoverable through mise. When signature/
# contact stripping BOTH keeps less than REVERT_RATIO of the pre-signature
# body AND removes more than REVERT_MIN_CHARS in absolute terms, revert to
# the un-stripped body — the heuristic almost certainly ate real content.
# The absolute floor is load-bearing: it distinguishes a genuine compact
# signature (a few hundred chars, correctly stripped) from an eaten payload,
# so short-reply-plus-signature cases are NOT reverted. Do NOT drop the floor
# to a pure ratio guard — that re-adds signatures to short replies. Under-
# stripping a signature is far safer than eating the body (see the walk-
# backwards rationale in talon_signature._strip_trailing_contact_block).
REVERT_RATIO = 0.35
REVERT_MIN_CHARS = 1000


def revert_if_catastrophic(
    baseline: str, body: str, warnings: list[str]
) -> tuple[str, list[str]]:
    """Return (baseline, net warning) when the strip ate the body, else (body, warnings).

    On a revert the strip's own warnings are dropped: they narrate a removal
    (links discarded, a low kept ratio) that never reached the caller, so one
    line with the net result replaces them (mise-vomika).
    """
    removed = len(baseline) - len(body)
    if baseline and removed > REVERT_MIN_CHARS and len(body) / len(baseline) < REVERT_RATIO:
        return baseline, [
            f"Signature strip would have kept only {100 * len(body) / len(baseline):.0f}% "
            "— skipped, full body kept."
        ]
    return body, warnings


# A reply's attribution line, left behind once its '>' lines are gone.
REPLY_PREAMBLE = re.compile(r'^On .{10,80} wrote:\s*$', re.MULTILINE)


def drop_orphaned_preamble(text: str) -> str:
    """Remove the reply preamble only when it is the last thing left (mise-pugina).

    Gmail writes 'On … wrote:' as one 60+ char line, which talon reads as too
    long to sit in a signature, so a '-- ' above an orphaned preamble was never
    examined. But a preamble with unquoted text below it heads inline answers,
    and it is the line that stops talon cutting from a sign-off through them,
    so that one stays until after talon (essayeur refutation of 9b2212a).
    """
    text = text.rstrip()
    last = None
    for last in REPLY_PREAMBLE.finditer(text):
        pass
    if last is None or text[last.end():].strip():
        return text
    return text[:last.start()].rstrip()
