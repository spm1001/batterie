"""
Event bounds as clock times: parsing, reading on one clock, and the words a preview shows.

Split from tools/events_util.py (the 500-line module cap) when mise-mafori's
round-1 repair added the skipped-and-repeated-hour rules. The rule throughout:
the words a preview states must name the instants written, because the preview
message is also the confirm dialog's text (tools/elicit.py).
"""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_DATE_ONLY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_event_time(
    raw: str, param: str, tz: str | None, warnings: list[str],
    tz_reason: str | None = None,
) -> dict[str, Any]:
    """One event bound → Google start/end dict ({'date':…} or {'dateTime':…}).

    Bare date = all-day (Google's end date is EXCLUSIVE — a one-day event ends
    on the NEXT day's date). Naive datetime gets the resolved zone attached;
    offset-carrying datetimes pass through untouched. `tz_reason` is why tz
    is None (adapters.calendar.lookup_calendar_timezone): a failed lookup must
    not read as an empty diary in the UTC-fallback warning.

    Raises ValueError with teaching text on unparseable input.
    """
    text = raw.strip()
    if _DATE_ONLY_RE.fullmatch(text):
        return {"date": text}
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(
            f"{param} must be an ISO date or datetime — '2026-09-08' or "
            f"'2026-09-08T14:00' or '2026-09-08T14:00:00+01:00' — got {text!r}"
        ) from None
    # Always re-serialise: Google rejects seconds-less RFC3339 ('T13:00'),
    # which the preview used to echo happily and the confirmed insert then
    # 400'd on — after the human had approved it (mise-duralu).
    if dt.tzinfo is None:
        if tz:
            return {"dateTime": dt.isoformat(), "timeZone": tz}
        why = f"your calendar's timezone is unknown: {tz_reason}" if tz_reason else (
            "none could be resolved from your calendar")
        warnings.append(
            f"{param} has no timezone and {why} — treated as UTC. Pass an "
            "offset (e.g. +01:00) if that is wrong."
        )
        return {"dateTime": dt.replace(tzinfo=timezone.utc).isoformat()}
    return {"dateTime": dt.isoformat()}


def _readings(dt: datetime, zone: ZoneInfo) -> tuple[datetime, datetime]:
    """A naive time in `zone`, read with the offset before a change and after (PEP 495 fold)."""
    return dt.replace(tzinfo=zone, fold=0), dt.replace(tzinfo=zone, fold=1)


def _with_offsets(param: str, dt: datetime, zone: ZoneInfo) -> str:
    early, late = _readings(dt, zone)
    if early.utcoffset() == late.utcoffset():
        return f"{param} {early.isoformat()}"
    return f"{param} {early.isoformat()} (first) or {late.isoformat()} (second)"


def refuse_unclear_wall_times(
    bounds: list[tuple[str, str]], tz: str | None, warnings: list[str],
) -> None:
    """Raise when a naive bound names no instant, or two, in the user's zone.

    `bounds` is [(param, text)] for the naive datetime bounds of one event.
    The clocks skip an hour in spring and repeat one in autumn. A skipped time
    collapsed both bounds of a clash window to one instant ('Clashes: none' for
    a slot the preview called an hour long); a repeated one leaves which instant
    Google books to Google. Either way the words could not be the thing written
    (mise-mafori), so ask again — for BOTH bounds with offsets, because one
    offset and one wall-clock time is refused as a mixed pair. When the zone
    cannot be loaded the check is skipped, and a warning says so.
    """
    if not tz or not bounds:
        return
    try:
        zone = ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        warnings.append(
            f"The time zone {tz} could not be loaded on this machine, so times "
            "the clocks skip or repeat were not checked: across a clock change "
            "the booking could land an hour off. Pass offsets to be sure."
        )
        return
    parsed = [(param, text, datetime.fromisoformat(text)) for param, text in bounds]
    for param, text, dt in parsed:
        early, late = _readings(dt, zone)
        before, after = early.utcoffset(), late.utcoffset()
        if before is not None and after is not None and before < after:  # skipped
            change = (dt - after).replace(tzinfo=timezone.utc)  # an instant just before the change
            while change.astimezone(zone).utcoffset() != after:
                change += timedelta(minutes=1)
            raise ValueError(
                f"{param} {text} does not exist in {tz}: on {_day_words(dt.date())} "
                f"the clocks jump from {change + before:%H:%M} to {change + after:%H:%M}. "
                "Pick a time outside that gap."
            )
    for i, (param, text, dt) in enumerate(parsed):
        early, late = _readings(dt, zone)
        before, after = early.utcoffset(), late.utcoffset()
        if before is not None and after is not None and before > after:  # repeated
            others = "".join(
                f", with {_with_offsets(p, d, zone)}"
                for j, (p, _, d) in enumerate(parsed) if j != i
            )
            raise ValueError(
                f"{param} {text} happens twice in {tz} on {_day_words(dt.date())} "
                "(the clocks go back). Give both bounds with offsets: "
                f"{_with_offsets(param, dt, zone)}{others}."
            )


def bound_datetime(time_dict: dict[str, Any]) -> datetime:
    """A start/end dict → aware datetime, for ordering checks and clash windows.

    Naive dateTimes (zone attached separately) and bare dates are pinned to
    UTC — fine for ordering, wrong for a clash window (use zoned_datetime)
    and for display.
    """
    raw = time_dict.get("dateTime") or time_dict["date"]
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _day_words(day: date) -> str:
    return f"{_DAY_NAMES[day.weekday()]} {day.day} {_MONTH_NAMES[day.month - 1]} {day.year}"


def _zone_words(bound: dict[str, Any], dt: datetime) -> str:
    if bound.get("timeZone"):
        return f" {bound['timeZone']}"
    offset = dt.utcoffset()
    if offset is None:
        return ""
    return " UTC" if not offset else f" UTC{dt.isoformat()[-6:]}"


def _named_zone(bound: dict[str, Any]) -> ZoneInfo | None:
    name = bound.get("timeZone")
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _on_clock(bound: dict[str, Any], clock: Any) -> datetime:
    """A dateTime bound read on one clock: `clock` (a zone or offset) when given.

    A naive dateTime is first placed in its own timeZone, else in `clock`;
    one with no zone information anywhere is left as given. describe_when
    names one zone for the whole span, so both bounds must be read on that
    zone's clock: each bound in its own offset said '00:30–01:30 UTC+01:00'
    for a two-hour booking across the October clock change, and the dialog
    carried those words to an accept (mise-mafori).
    """
    dt = datetime.fromisoformat(bound["dateTime"])
    if dt.tzinfo is None:
        own = _named_zone(bound) or clock
        if own is None:
            return dt
        dt = dt.replace(tzinfo=own)
    return dt.astimezone(clock) if clock is not None else dt


def _happens_twice(dt: datetime) -> bool:
    """Does this wall-clock time occur twice in its zone (the hour the clocks go back)?"""
    if dt.tzinfo is None:
        return False
    return dt.replace(fold=1 - dt.fold).utcoffset() != dt.utcoffset()


def zoned_datetime(time_dict: dict[str, Any]) -> datetime:
    """A start/end dict → aware datetime in the event's own zone.

    For windows that must name the right instant, such as the clash check:
    a naive dateTime means wall-clock in its timeZone, so pinning it to UTC
    (bound_datetime) asks about the wrong hour whenever the zone is not UTC.
    """
    raw = time_dict.get("dateTime")
    zone = time_dict.get("timeZone")
    if raw and zone:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            try:
                return dt.replace(tzinfo=ZoneInfo(zone))
            except ZoneInfoNotFoundError:
                pass
    return bound_datetime(time_dict)


def describe_when(start: dict[str, Any], end: dict[str, Any]) -> str:
    """A start/end pair in short words — 'Sun 4 Oct 2026 04:00–04:15 Europe/London'.

    For preview messages, which are also the confirm dialog's text and must
    fit its 74-column lines (tools/elicit.py). The weekday is there because
    a wrong-day booking is the mistake a human catches at a glance. Bounds
    that do not parse are shown as given rather than guessed at.
    """
    try:
        if "date" in start:
            first = date.fromisoformat(start["date"])
            last = date.fromisoformat(end["date"]) - timedelta(days=1)  # Google's end is exclusive
            if last <= first:
                return f"{_day_words(first)}, all day"
            return f"{_day_words(first)} – {_day_words(last)}, all day"
        zone = _named_zone(start)
        s = _on_clock(start, zone)
        e = _on_clock(end, zone if zone is not None else s.tzinfo)
    except (KeyError, TypeError, ValueError):
        return f"{start.get('dateTime') or start.get('date')} – {end.get('dateTime') or end.get('date')}"
    # On the morning the clocks go back, 01:30 Europe/London names two instants
    # an hour apart; a span touching that hour says which, or '00:30–01:30'
    # reads as one hour while two are written (mise-mafori, round 1).
    marked = zone is not None and (_happens_twice(s) or _happens_twice(e))
    if marked:
        first, last = f"{s:%H:%M} {s.tzname()}", f"{e:%H:%M} {e.tzname()}"
    else:
        first, last = f"{s:%H:%M}", f"{e:%H:%M}"
    dash = " – " if marked and any(str(d.tzname())[:1] in "+-" for d in (s, e)) else "–"
    if s.date() == e.date():
        span = f"{_day_words(s.date())} {first}{dash}{last}"
    else:
        span = f"{_day_words(s.date())} {first} – {_day_words(e.date())} {last}"
    return span + _zone_words(start, s) + ("" if marked else _length_note(s, e))


def _length_note(s: datetime, e: datetime) -> str:
    """' (3h, clocks go back)' when a span's real length is not its clock reading.

    A span containing a clock change, with neither bound in the changed hour,
    otherwise reads wrong without a word: 00:30–02:30 on 25 Oct in London is
    three hours. Kept short for the dialog's 74 columns. A span already marked
    BST/GMT carries the change in its abbreviations instead.
    """
    if s.tzinfo is None or e.tzinfo is None:
        return ""
    real = e.astimezone(timezone.utc) - s.astimezone(timezone.utc)
    shown = e.replace(tzinfo=None) - s.replace(tzinfo=None)
    if real == shown or real <= timedelta(0):
        return ""
    hours, minutes = divmod(int(real.total_seconds()) // 60, 60)
    if not minutes:
        length = f"{hours}h"
    elif not hours:
        length = f"{minutes}m"
    else:
        length = f"{hours}h{minutes:02d}m"
    return f" ({length}, clocks go {'back' if real > shown else 'forward'})"
