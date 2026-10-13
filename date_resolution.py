import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateparser import DateDataParser

from time import perf_counter

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Label, TextArea

_OFFSETS = {"last": -1, "this": 0, "next": 1}

_WEEKDAYS = {
    name: index
    for index, names in enumerate((
        ("monday", "mon"),
        ("tuesday", "tue", "tues"),
        ("wednesday", "wed"),
        ("thursday", "thu", "thur", "thurs"),
        ("friday", "fri"),
        ("saturday", "sat"),
        ("sunday", "sun"),
    ))
    for name in names
}

def _month_start(day, offset=0):
    month_index = day.year * 12 + day.month - 1 + offset
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)

def _calendar_range(day, granularity, zone, offset=0):
    if granularity == "day":
        start = day + timedelta(days=offset)
        end = start + timedelta(days=1)
    elif granularity == "week":
        start = (
            day - timedelta(days=day.weekday())
            + timedelta(weeks=offset)
        )
        end = start + timedelta(days=7)
    elif granularity == "month":
        start = _month_start(day, offset)
        end = _month_start(start, 1)
    elif granularity == "year":
        start = date(day.year + offset, 1, 1)
        end = date(start.year + 1, 1, 1)
    else:
        return None

    start_local = datetime.combine(start, time.min, tzinfo=zone)
    end_local = datetime.combine(end, time.min, tzinfo=zone)

    return {
        "start_utc": start_local.astimezone(UTC),
        "end_utc": end_local.astimezone(UTC),
        "granularity": granularity,
        "kind": "calendar",
        "timezone": zone.key,
    }

def resolve_date_range(
    text,
    reference_time,
    timezone="America/Chicago",
):
    if not isinstance(reference_time, datetime):
        raise TypeError("reference_time must be a datetime")
    if reference_time.tzinfo is None or reference_time.utcoffset() is None:
        raise ValueError("reference_time must include a timezone")

    zone = ZoneInfo(timezone)
    reference = reference_time.astimezone(zone)
    today = reference.date()
    query = " ".join(text.casefold().split()).rstrip(".!?")

    if not query:
        return None

    calendar_match = re.fullmatch(
        r"(this|last|next) (day|week|month|year)",
        query,
    )
    if calendar_match:
        modifier, granularity = calendar_match.groups()
        return _calendar_range(
            today,
            granularity,
            zone,
            offset=_OFFSETS[modifier],
        )

    weekday_match = re.fullmatch(
        r"(?:(this|last|next) )?(" + "|".join(_WEEKDAYS) + r")",
        query,
    )
    if weekday_match:
        modifier, weekday = weekday_match.groups()
        week_start = today - timedelta(days=today.weekday())
        target = week_start + timedelta(
            weeks=_OFFSETS[modifier or "this"],
            days=_WEEKDAYS[weekday],
        )
        return _calendar_range(target, "day", zone)

    rolling_match = re.fullmatch(r"(?:past|last) (\d+) days?", query)
    if rolling_match:
        days = int(rolling_match.group(1))
        if days < 1:
            raise ValueError("A rolling window must contain at least one day")

        end = reference.astimezone(UTC)
        return {
            "start_utc": end - timedelta(days=days),
            "end_utc": end,
            "granularity": "day",
            "kind": "rolling",
            "timezone": zone.key,
        }

    parser = DateDataParser(
        languages=["en"],
        settings={
            "RELATIVE_BASE": reference,
            "TIMEZONE": timezone,
            "RETURN_AS_TIMEZONE_AWARE": True,
            "RETURN_TIME_AS_PERIOD": True,
            "DATE_ORDER": "MDY",
            "PREFER_LOCALE_DATE_ORDER": False,
            "PARSERS": ["relative-time", "absolute-time"],
        },
    )
    parsed = parser.get_date_data(query)

    if parsed.date_obj is None or parsed.period == "time":
        return None

    granularity = parsed.period
    if re.search(r"^in\s+|\b(?:ago|from now)$", query):
        granularity = "day"

    parsed_day = parsed.date_obj.astimezone(zone).date()
    return _calendar_range(parsed_day, granularity, zone)

def main():
    zone = ZoneInfo('America/Chicago')
    reference_time = datetime.now(zone)
    result_text = "Enter a date phrase."
    bindings = KeyBindings()

    @bindings.add("c-c")
    @bindings.add("c-d")
    def exit_preview(event):
        event.app.exit()

    def accept_input(buffer):
        if buffer.text.strip().casefold() in {"quit", "exit"}:
            application.exit()
        return True

    input_field = TextArea(
        height=1,
        prompt="> ",
        multiline=False,
        wrap_lines=False,
        accept_handler=accept_input,
    )

    body = HSplit([
        Label(
            f"Reference: {reference_time:%Y-%m-%d %I:%M:%S %p %Z}",
            wrap_lines=False,
        ),
        Label(
            "Date preview updates as you type. Ctrl-C exits.",
            wrap_lines=False,
        ),
        input_field,
        Window(
            content=FormattedTextControl(lambda: result_text),
            height=6,
            wrap_lines=False,
        ),
    ])

    application = Application(
        layout=Layout(body, focused_element=input_field),
        key_bindings=bindings,
        full_screen=False,
    )

    def update_results(buffer):
        nonlocal result_text

        if not buffer.text.strip():
            result_text = "Enter a date phrase."
            application.invalidate()
            return

        started = perf_counter()

        try:
            result = resolve_date_range(
                buffer.text,
                reference_time,
                timezone=zone.key,
            )
        except (ValueError, OverflowError) as error:
            result_text = f"Cannot interpret input: {error}"
        else:
            elapsed_ms = (perf_counter() - started) * 1000

            if result is None:
                result_text = "No date range recognized yet."
            else:
                start = result["start_utc"].astimezone(zone)
                end = result["end_utc"].astimezone(zone)

                result_text = "\n".join([
                    f"Start (inclusive): {start:%Y-%m-%d %H:%M:%S %Z}",
                    f"End   (exclusive): {end:%Y-%m-%d %H:%M:%S %Z}",
                    f"UTC start: {result['start_utc'].isoformat()}",
                    f"UTC end:   {result['end_utc'].isoformat()}",
                    f"Type: {result['kind']} | "
                    f"Granularity: {result['granularity']}",
                    f"Parse time: {elapsed_ms:.2f} ms",
                ])

        application.invalidate()

    input_field.buffer.on_text_changed += update_results
    application.run()

if __name__ == "__main__":
    main()
