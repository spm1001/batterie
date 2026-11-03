"""update_event's attendee merge — split from tools/update_event.py at its
500-line cap when optional attendees arrived (mise-en-space-naseto)."""

from typing import Any

from tools.update_event_preview import Edit


def merged_attendees(edit: Edit) -> list[dict[str, Any]]:
    """The FULL attendees array to patch (patch replaces arrays wholesale).

    Existing guests keep every field except a demoted `optional`; new guests
    are appended. A guest-less event you organise gaining guests (a hold
    becoming a meeting) also gains you as an accepted guest — the API, unlike
    the Calendar UI, never adds the organiser, and create_event does the same.
    """
    demote = {e.lower() for e in edit.made_optional}
    merged: list[dict[str, Any]] = []
    for attendee in edit.event.get("attendees", []):
        entry = dict(attendee)
        if entry.get("email", "").lower() in demote:
            entry["optional"] = True
        merged.append(entry)
    merged += [{"email": e} for e in edit.emails]
    merged += [{"email": e, "optional": True} for e in edit.added_optional]
    # adds_organiser is is_hold_becoming_meeting: you organise it, no guests yet.
    me = edit.event.get("organizer", {}).get("email", "")
    if (edit.adds_organiser and me
            and me.lower() not in {a.get("email", "").lower() for a in merged}):
        merged.append({"email": me, "responseStatus": "accepted"})
    return merged
