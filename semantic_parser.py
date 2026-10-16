import re
from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from lark import Lark, Transformer
from lark.exceptions import UnexpectedInput, VisitError
from lark.visitors import CollapseAmbiguities

from team_search import normalize_search_text
from date_resolution import resolve_date_range

class TeamMentionRecognizer:

    def __init__(self, searcher):
        self.aliases = searcher.aliases
        self.team_names = searcher.team_names
        self.max_alias_words = max(
            (len(alias.split()) for alias in self.aliases),
            default=0
        )

    def find_mentions(self, text):
        words = list(re.finditer(r"\w+", text))
        mentions = []

        for first in range(len(words)):
            last_limit = min(
                len(words),
                first + self.max_alias_words,
            )

            for last in range(first + 1, last_limit + 1):
                start = words[first].start()
                end = words[last - 1].end()
                fragment = text[start:end]
                normalized = normalize_search_text(fragment)
                teams = self.aliases.get(normalized)

                if teams is None:
                    continue

                mentions.append({
                    "kind": "team",
                    "start": start,
                    "end": end,
                    "text": fragment,
                    "candidates": [
                        {
                            "team_id": team_id,
                            "name": self.team_names[team_id],
                            "matched_label": teams[team_id],
                        }
                        for team_id in sorted(teams)
                    ],
                })

        return mentions

class DateMentionRecognizer:

    def __init__(self):
        self.months = {
            name: number
            for number, name in enumerate(
                (
                    "january", "february", "march", "april",
                    "may", "june", "july", "august",
                    "september", "october", "november", "december",
                ),
                start=1,
            )
        }
        self.offsets = {"last": -1, "this": 0, "next": 1}
        month_names = "|".join(self.months)

        self.calendar_pattern = re.compile(
            rf"\b(?P<month>{month_names})"
            r"(?:\s+(?P<day>0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?"
            r"(?:(?:,\s*|\s+)(?P<year>[1-9]\d{3}))?"
            r"|\s+(?P<month_year>[1-9]\d{3}))?\b",
            re.IGNORECASE,
        )
        self.relative_pattern = re.compile(
            r"\b(?P<modifier>this|last|next)\s+"
            r"(?P<unit>day|week|month|year)\b",
            re.IGNORECASE,
        )

    def find_mentions(self, text):
        mentions = []

        for match in self.calendar_pattern.finditer(text):
            day = match.group("day")
            year = match.group("year") or match.group("month_year")

            mentions.append({
                "kind": "date",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
                "expression": {
                    "type": "calendar",
                    "month": self.months[match.group("month").casefold()],
                    "day": int(day) if day is not None else None,
                    "year": int(year) if year is not None else None,
                },
            })

        for match in self.relative_pattern.finditer(text):
            modifier = match.group("modifier").casefold()

            mentions.append({
                "kind": "date",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
                "expression": {
                    "type": "relative_calendar",
                    "unit": match.group("unit").casefold(),
                    "offset": self.offsets[modifier],
                },
            })

        return sorted(
            mentions,
            key=lambda mention: (mention["start"], -mention["end"]),
        )

_GRAMMAR = r"""
?start: request _END?

?request: "who"i "does"i team "play"i modifier* -> games
        | "who"i "plays"i modifier+ -> games
        | ("show"i "me"i? | "list"i) game_phrase -> show

?game_phrase: team "'s"i? site? _GAMES modifier* -> games
            | site? _GAMES modifier* -> games

?modifier: date_clause | site | upcoming

date_clause: ("on"i | "in"i | "during"i | "for"i)? date
team: TEAM
date: DATE

site: "home"i -> home
    | "away"i -> away
    | "neutral"i -> neutral

upcoming: "next"i

TEAM: /TEAM_\d+/
DATE: /DATE_\d+/
_GAMES: "games"i | "schedule"i
_END: /[?.!]+/

%import common.WS
%ignore WS
"""

class _QueryBuilder(Transformer):
    def __init__(self, mentions):
        super().__init__()
        self.mentions = mentions

    def team(self, children):
        mention = self.mentions[str(children[0])]
        return {"team_candidates": mention["candidates"]}

    def date(self, children):
        mention = self.mentions[str(children[0])]
        return {"date_expression": mention["expression"]}

    def date_clause(self, children):
        return children[0]

    def home(self, children):
        return {"site": "home"}

    def away(self, children):
        return {"site": "away"}

    def neutral(self, children):
        return {"site": "neutral"}

    def upcoming(self, children):
        return {"upcoming": True, "limit": 1}

    def show(self, children):
        return children[0]

    def games(self, children):
        fields = {}

        for fragment in children:
            for key, value in fragment.items():
                if key in fields and fields[key] != value:
                    raise ValueError(f"Conflicting values for {key}.")
                fields[key] = value

        query = {
            "kind": "games",
            "team_candidates": None,
            "date_expression": None,
            "site": None,
            "upcoming": False,
            "order": "ascending",
            "limit": None,
            **fields,
        }

        if query["site"] in {"home", "away"} and query["team_candidates"] is None:
            raise ValueError("Home or away requires a team reference.")

        return query

class ScheduleGrammar:

    def __init__(self):
        self.parser = Lark(
            _GRAMMAR,
            parser="earley",
            ambiguity="explicit",
        )

    def parse(self, annotated_text, mentions):
        try:
            tree = self.parser.parse(annotated_text)
        except UnexpectedInput as error:
            raise ValueError(
                "The completed question does not match the supported grammar."
            ) from error

        builder = _QueryBuilder(mentions)
        candidates = []
        last_error = None

        for interpretation in CollapseAmbiguities().transform(tree):
            try:
                candidate = builder.transform(interpretation)
            except VisitError as error:
                if not isinstance(error.orig_exc, ValueError):
                    raise
                last_error = error.orig_exc
                continue

            if candidate not in candidates:
                candidates.append(candidate)

        if not candidates:
            raise ValueError(
                str(last_error) if last_error else "No valid interpretation."
            )

        return candidates

class SemanticParser:

    def __init__(self, searcher, max_tokenizations=128):
        if max_tokenizations < 1:
            raise ValueError("max_tokenizations must be positive")

        self.teams = TeamMentionRecognizer(searcher)
        self.dates = DateMentionRecognizer()
        self.grammar = ScheduleGrammar()
        self.max_tokenizations = max_tokenizations

    def _annotated_inputs(self, text, mentions):
        by_start = {}

        for marker, mention in mentions.items():
            by_start.setdefault(mention["start"], []).append(
                (marker, mention)
            )

        starts = sorted(by_start)
        pending = [(0, ())]
        count = 0

        while pending:
            position, parts = pending.pop()

            if position == len(text):
                count += 1
                if count > self.max_tokenizations:
                    raise ValueError(
                        "Too many possible phrase combinations; "
                        "please make the question more specific."
                    )
                yield "".join(parts)
                continue

            next_start = next(
                (start for start in starts if start > position),
                len(text),
            )
            fragment = text[position:next_start].replace("’", "'").casefold()
            pending.append((next_start, parts + (fragment,)))

            for marker, mention in reversed(by_start.get(position, [])):
                pending.append((
                    mention["end"],
                    parts + (f" {marker} ",),
                ))

    def parse(self, text):
        if not text.strip():
            raise ValueError("Enter a schedule question.")

        spans = sorted(
            self.teams.find_mentions(text) + self.dates.find_mentions(text),
            key=lambda mention: (
                mention["start"],
                -mention["end"],
                mention["kind"],
            ),
        )
        mentions = {
            f"{mention['kind'].upper()}_{number}": mention
            for number, mention in enumerate(spans)
        }
        candidates = []

        for annotated_text in self._annotated_inputs(text, mentions):
            try:
                interpretations = self.grammar.parse(annotated_text, mentions)
            except ValueError:
                continue

            for interpretation in interpretations:
                if interpretation not in candidates:
                    candidates.append(interpretation)

        if not candidates:
            raise ValueError(
                "No complete interpretation of the question was found."
            )

        return candidates

def resolve_date_expression(
    expression,
    season,
    reference_time,
    timezone="America/Chicago",
):
    if not isinstance(reference_time, datetime):
        raise TypeError("reference_time must be a datetime")
    if reference_time.tzinfo is None or reference_time.utcoffset() is None:
        raise ValueError("reference_time must include a timezone")

    zone = ZoneInfo(timezone)

    if expression is None:
        return None

    if expression["type"] == "calendar":
        month = expression["month"]
        year = expression["year"]
        day = expression["day"]

        if year is None:
            year = season - 1 if month >= 7 else season

        start = date(year, month, 1 if day is None else day)
        duration = monthrange(year, month)[1] if day is None else 1
        end = start + timedelta(days=duration)

        result = {
            "start_utc": datetime.combine(
                start, time.min, tzinfo=zone
            ).astimezone(UTC),
            "end_utc": datetime.combine(
                end, time.min, tzinfo=zone
            ).astimezone(UTC),
            "granularity": "month" if day is None else "day",
            "kind": "calendar",
            "timezone": zone.key,
        }

    elif expression["type"] == "relative_calendar":
        modifier = {-1: "last", 0: "this", 1: "next"}.get(
            expression["offset"]
        )
        unit = expression["unit"]

        if modifier is None or unit not in {"day", "week", "month", "year"}:
            raise ValueError("Unsupported relative calendar expression.")

        result = resolve_date_range(
            f"{modifier} {unit}",
            reference_time,
            timezone=timezone,
        )

        if result is None:
            raise ValueError("Could not resolve the calendar expression.")

    else:
        raise ValueError(f"Unsupported date expression: {expression['type']}")

    season_start = datetime(
        season - 1, 7, 1, tzinfo=zone
    ).astimezone(UTC)
    season_end = datetime(
        season, 7, 1, tzinfo=zone
    ).astimezone(UTC)

    if result["end_utc"] <= season_start or result["start_utc"] >= season_end:
        raise ValueError(
            f"The requested dates fall outside season "
            f"{season - 1}-{season % 100:02d}."
        )

    return result
