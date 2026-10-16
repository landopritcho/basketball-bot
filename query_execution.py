from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from schedule_queries import get_game_calendar_date
from semantic_parser import resolve_date_expression

@dataclass(frozen=True)
class GameQuery:

    season: int
    team_id: str | None = None
    start_utc: datetime | None = None
    end_utc: datetime | None = None
    upcoming_after: datetime | None = None
    site: Literal["home", "away", "neutral"] | None = None
    order: Literal["ascending", "descending"] = "ascending"
    limit: int | None = None
    timezone: str = "America/Chicago"

    def __post_init__(self):
        if self.site not in {None, "home", "away", "neutral"}:
            raise ValueError("Unsupported site filter.")
        if self.site in {"home", "away"} and self.team_id is None:
            raise ValueError("Home or away requires a team.")
        if self.order not in {"ascending", "descending"}:
            raise ValueError("Unsupported ordering.")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be positive.")
        if (self.start_utc is None) != (self.end_utc is None):
            raise ValueError("A date range requires both boundaries.")

        for value in (self.start_utc, self.end_utc, self.upcoming_after):
            if value is not None:
                if value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError("Query datetimes must include a timezone.")

        if (
            self.start_utc is not None
            and self.end_utc is not None
            and self.start_utc >= self.end_utc
        ):
            raise ValueError("The start must precede the end.")

def bind_game_query(meaning, season, reference_time, timezone="America/Chicago"):
    if meaning["kind"] != "games":
        raise ValueError("Unsupported query kind.")

    teams = meaning["team_candidates"]
    if teams is not None and len(teams) != 1:
        raise ValueError("Select exactly one candidate team before binding.")

    date_range = resolve_date_expression(
        meaning["date_expression"],
        season,
        reference_time,
        timezone=timezone,
    )

    return GameQuery(
        season=season,
        team_id=None if teams is None else teams[0]["team_id"],
        start_utc=None if date_range is None else date_range["start_utc"],
        end_utc=None if date_range is None else date_range["end_utc"],
        upcoming_after=(
            reference_time.astimezone(UTC) if meaning["upcoming"] else None
        ),
        site=meaning["site"],
        order=meaning["order"],
        limit=meaning["limit"],
        timezone=timezone,
    )

def compile_candidate_query(query):
    conditions = ["season = ?"]
    parameters = [query.season]

    if query.team_id is not None:
        conditions.append("(home_team_id = ? OR away_team_id = ?)")
        parameters.extend([query.team_id, query.team_id])

    if query.site in {"home", "away"}:
        column = "home_team_id" if query.site == "home" else "away_team_id"
        conditions.append(f"({column} = ? AND neutral_site IS NOT TRUE)")
        parameters.append(query.team_id)
    elif query.site == "neutral":
        conditions.append("neutral_site IS NOT FALSE")

    if query.start_utc is not None:
        conditions.append(
            "(tipoff_utc IS NULL OR "
            "(tipoff_utc >= ? AND tipoff_utc < ?))"
        )
        parameters.extend([query.start_utc, query.end_utc])

    if query.upcoming_after is not None:
        conditions.append("status = 'STATUS_SCHEDULED'")
        conditions.append("(tipoff_utc IS NULL OR tipoff_utc > ?)")
        parameters.append(query.upcoming_after)

    sql = f"""
        SELECT
            game_id, season,
            home_team_id, home_team_name,
            away_team_id, away_team_name,
            timezone('UTC', source_datetime_utc) AS source_datetime_utc,
            time_valid,
            timezone('UTC', tipoff_utc) AS tipoff_utc,
            neutral_site, venue, status, source_status_detail
        FROM games
        WHERE {" AND ".join(conditions)}
        ORDER BY game_id
    """

    return sql, parameters

def _precedes(left, right):
    left_game, _, latest = left
    right_game, earliest, _ = right

    if latest is None or earliest is None:
        return False
    if latest != earliest:
        return latest < earliest
    if left_game["tipoff_utc"] is None:
        return True
    return (
        right_game["tipoff_utc"] is not None
        and left_game["game_id"] < right_game["game_id"]
    )

def execute_game_query(connection, query):
    zone = ZoneInfo(query.timezone)
    team_name = None

    if query.team_id is not None:
        team = connection.execute(
            "SELECT name FROM teams WHERE team_id = ?", [query.team_id]
        ).fetchone()
        if team is None:
            raise ValueError(f"Unknown team ID: {query.team_id}")
        team_name = team[0]

    sql, parameters = compile_candidate_query(query)
    result = connection.execute(sql, parameters)
    columns = [column[0] for column in result.description]
    candidates = []

    for row in result.fetchall():
        game = dict(zip(columns, row, strict=True))
        for field in ("source_datetime_utc", "tipoff_utc"):
            if game[field] is not None:
                game[field] = game[field].replace(tzinfo=UTC)

        is_home = game["home_team_id"] == query.team_id
        game["site"] = None

        if game["neutral_site"] is True:
            game["site"] = "neutral"
        elif game["neutral_site"] is False and query.team_id is not None:
            game["site"] = "home" if is_home else "away"

        if query.team_id is not None:
            opponent = "away" if is_home else "home"
            game["opponent_team_id"] = game[f"{opponent}_team_id"]
            game["opponent_team_name"] = game[f"{opponent}_team_name"]

        reasons = []
        if query.site is not None and game["neutral_site"] is None:
            reasons.append("The home/away/neutral designation is unknown.")

        try:
            game_day = get_game_calendar_date(game, zone)
        except ValueError:
            game_day = None

        game["calendar_date"] = game_day
        tipoff = game["tipoff_utc"]

        if tipoff is not None:
            earliest = latest = tipoff
        elif game_day is not None:
            earliest = datetime.combine(
                game_day, time.min, tzinfo=zone
            ).astimezone(UTC)
            latest = datetime.combine(
                game_day + timedelta(days=1), time.min, tzinfo=zone
            ).astimezone(UTC)

            if query.start_utc is not None:
                if earliest >= query.end_utc or latest <= query.start_utc:
                    continue
                if earliest < query.start_utc or latest > query.end_utc:
                    reasons.append(
                        "The TBD tipoff may fall outside the date range."
                    )

            if query.upcoming_after is not None:
                if latest <= query.upcoming_after:
                    continue
                if earliest <= query.upcoming_after:
                    reasons.append("The TBD tipoff may have already passed.")
        else:
            earliest = latest = None
            if query.start_utc is not None or query.upcoming_after is not None:
                reasons.append("The schedule date is unknown.")

        game["uncertainty_reasons"] = reasons
        candidates.append((game, earliest, latest))

    descending = query.order == "descending"
    missing_bound = (datetime.max if descending else datetime.min).replace(
        tzinfo=UTC
    )
    bound_index = 2 if descending else 1

    ordered = sorted(
        candidates,
        key=lambda entry: (
            entry[bound_index] if entry[bound_index] is not None else missing_bound,
            entry[0]["game_id"],
        ),
        reverse=descending,
    )

    if query.limit is not None:
        selected = ordered[:query.limit]

        for index, entry in enumerate(selected):
            if entry[0]["uncertainty_reasons"] or any(
                not (
                    _precedes(other, entry)
                    if descending else _precedes(entry, other)
                )
                for other in ordered[index + 1:]
            ):
                raise ValueError(
                    "Missing schedule dates, tipoffs, or site information prevent "
                    "determining the requested games in order."
                )

        games = [entry[0] for entry in selected]
        uncertain_games = []
    else:
        ordered = (
            [entry for entry in ordered if entry[1] is not None]
            + [entry for entry in ordered if entry[1] is None]
        )
        games = [
            game for game, _, _ in ordered
            if not game["uncertainty_reasons"]
        ]
        uncertain_games = [
            game for game, _, _ in ordered
            if game["uncertainty_reasons"]
        ]

    return {
        "query": query,
        "team_id": query.team_id,
        "team_name": team_name,
        "season": query.season,
        "games": games,
        "uncertain_games": uncertain_games,
    }
