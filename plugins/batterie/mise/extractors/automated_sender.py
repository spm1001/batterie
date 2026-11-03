"""Is this message machine-sent? Read from its headers (mise-woluso).

Signature stripping assumes a person signed the message. Machine mail has no
personal signature, and its tail is often the reason it was sent: a Google
Cloud notice's list of affected projects (mise-serewe), the second comment of
a Jira Service Desk ticket holding an API secret (mise-monesi), a newsletter's
last stories, a calendar invite's guest list. Every wrong strip in a census of
73 contact-block firings over 216 real threads (3 Nov 2026) was machine mail;
every human-signature strip was right.

The From address alone misses two of those field reports, so the headers
decide: a Google Group rewrites From ("'Google Cloud' via mit-group") but keeps
the sender in Reply-To and X-Original-Sender, and Jira sends from a human-
looking support@ address with Auto-Submitted and Precedence: bulk set.
Precedence: list does NOT count: Google Groups stamps it on human mail too.
Out-of-office replies carry Auto-Submitted and so count as machine mail; their
signature then stays, which costs a few lines and loses nothing.
"""

import re

# A no-reply style mailbox: noreply@, no-reply@, no_reply@ (Apple), CloudPlatform-noreply@,
# comments-noreply@, do-not-reply@, notifications@ (GitHub), mailer-daemon@. Over-matching
# (a person's 'jane.notifications-lead@') only keeps that person's signature.
_NO_REPLY = re.compile(
    r"(?:^|[<\s\"'])[\w.+-]*(?:no[-_]?reply|do[-_]?not[-_]?reply|notifications?|mailer-daemon)[\w.+-]*@",
    re.IGNORECASE,
)


def _value(headers: dict[str, str], name: str) -> str:
    """A header's token, without an RFC 3834 comment or parameters: 'No (manual)' -> 'no'."""
    return re.split(r"[(;]", headers.get(name, ""), maxsplit=1)[0].strip().lower()


def automated_reason(headers: dict[str, str]) -> str | None:
    """The header evidence that a message is machine-sent, or None for a person.

    `headers` is keyed by canonical header name, as adapters.gmail parses them.
    """
    submitted = _value(headers, "Auto-Submitted")
    if submitted and submitted != "no":
        return f"Auto-Submitted: {submitted}"
    precedence = _value(headers, "Precedence")
    if precedence in ("bulk", "junk"):
        return f"Precedence: {precedence}"
    for name in ("From", "Reply-To", "X-Original-Sender"):
        if _NO_REPLY.search(headers.get(name, "")):
            return f"no-reply address in {name}"
    return None
