import re
from datetime import UTC, date, datetime, time
from date_resolution import resolve_date_range
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"(?:who|when) does (?P<team>.+?) play"
        r"(?: (?P<tail>.+))?",

        r"(?:(?:show(?: me)?|list) )?"
        r"(?P<team>.+?)(?:'s)? (?:full )?(?:schedule|games)"
        r"(?: (?P<tail>.+))?",
    )
)

_MONTH_PREFIX = re.compile(
    r"^in (?=(?:january|february|march|april|may|june|july|"
    r"august|september|october|november|december)\b)",
    re.IGNORECASE,
)

def parse_schedule_question(text):
    question = " ".join(text.replace("’", "'").split()).rstrip(".!?")

    for pattern in _PATTERNS:
        match = pattern.fullmatch(question)
        if match is not None:
            break
    else:
        return None

    team_text = match.group("team").strip()
    tail = (match.group("tail") or "").strip()

    if tail.casefold() in {"next", "next game", "next matchup"}:
        return {
            "intent": "next_game",
            "team_text": team_text,
            "date_text": None,
        }
    
    date_text = re.sub(
        r"^(?:on|during|for) ",
        "",
        tail,
        flags=re.IGNORECASE,
    )
    date_text = _MONTH_PREFIX.sub("", date_text)

    if date_text.casefold() in {
        "",
        "this season",
        "the full season",
        "full season",
    }:
        date_text = None

    return {
        "intent": "team_schedule",
        "team_text": team_text,
        "date_text": date_text,
    }

def _resolve_date_in_season(text, reference_time, timezone, season):
    date_range = resolve_date_range(
        text,
        reference_time,
        timezone=timezone,
    )

    if date_range is None or season is None:
        return date_range

    zone = ZoneInfo(timezone)
    season_start = date(season - 1, 7, 1)
    season_end = date(season, 7, 1)
    normalized = " ".join(text.casefold().split()).rstrip(".!?")

    if (
        re.fullmatch(r"[a-z]+", normalized)
        and date_range["granularity"] == "month"
    ):
        month = date_range["start_utc"].astimezone(zone).month
        year = season - 1 if month >= 7 else season

        date_range = resolve_date_range(
            f"{normalized} {year}",
            reference_time,
            timezone=timezone,
        )

        if date_range is None:
            return None

    start_utc = datetime.combine(
        season_start, time.min, tzinfo=zone
    ).astimezone(UTC)
    end_utc = datetime.combine(
        season_end, time.min, tzinfo=zone
    ).astimezone(UTC)

    if (
        date_range["end_utc"] <= start_utc
        or date_range["start_utc"] >= end_utc
    ):
        raise ValueError(
            f"{text!r} falls outside the selected season "
            f"{season - 1}-{season % 100:02d} "
            f"(July 1, {season - 1} through June 30, {season})."
        )

    return date_range

def resolve_schedule_question(
    text,
    searcher,
    reference_time,
    timezone="America/Chicago",
    *,
    season=None,
):
    request = parse_schedule_question(text)

    if request is None:
        return {
            "status": "unsupported",
            "message": "I couldn't recognize a schedule question.",
        }

    date_range = None

    if request["date_text"] is not None:
        try:
            date_range = _resolve_date_in_season(
                request["date_text"],
                reference_time,
                timezone=timezone,
                season=season,
            )
        except (ValueError, OverflowError) as error:
            return {
                "status": "invalid_date",
                "message": f"Cannot interpret the date: {error}",
            }

        if date_range is None:
            return {
                "status": "invalid_date",
                "message": (
                    f"Cannot interpret the date: "
                    f"{request['date_text']!r}"
                ),
            }

    request = {
        **request,
        "date_range": date_range,
    }

    matches = searcher.search(request["team_text"], limit=10)
    exact_matches = [
        match for match in matches
        if match["method"] == "exact"
    ]

    if not matches:
        return {
            "status": "unknown_team",
            "message": f"No teams found for {request['team_text']!r}.",
        }

    if len(exact_matches) != 1:
        return {
            "status": "choose_team",
            "request": request,
            "candidates": exact_matches or matches[:5],
        }

    team = exact_matches[0]

    return {
        "status": "ready",
        "request": {
            **request,
            "team_id": team["team_id"],
            "team_name": team["name"],
        },
    }
