"""Every cache that holds a fact about WHICH account is answering, cleared in one call.

An identity switch (the library facade's Mise(), the sync client's dead-grant
swap) must drop all of them together. They used to be cleared one by one at
each site, and the calendar timezone was missed at both, so a process that
switched accounts booked the second account's events in the first account's
zone (mise-lagame). A new identity-derived cache gets its clear added here,
once, rather than at every switch site.
"""

from adapters.calendar import clear_timezone_cache
from adapters.people import clear_profile_cache
from cues_util import clear_user_email_cache


def clear_identity_caches() -> None:
    """Forget the account's email, directory profiles (and refusal) and diary zone."""
    clear_user_email_cache()
    clear_profile_cache()
    clear_timezone_cache()
