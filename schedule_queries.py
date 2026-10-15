import re
import argparse
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import duckdb

def get_team_schedule(connection, team_id, season):
    team_id = str(team_id)
    team = connection.execute(
        "SELECT name FROM teams WHERE team_id = ?",
        [team_id],
    ).fetchone()

    if team is None:
        raise ValueError(f"Unknown team ID: {team_id}")

    result = connection.execute("""
        SELECT
            game_id,
            season,
            home_team_id,
            home_team_name,
            away_team_id,
            away_team_name,
            timezone('UTC', source_datetime_utc) AS source_datetime_utc,
            time_valid,
            timezone('UTC', tipoff_utc) AS tipoff_utc,
            neutral_site,
            venue,
            status,
            source_status_detail
        FROM games
        WHERE season = ?
            AND (home_team_id = ? OR away_team_id = ?)
        ORDER BY source_datetime_utc, game_id
    """, [season, team_id, team_id])

    columns = [column[0] for column in result.description]
    games = []

    for row in result.fetchall():
        game = dict(zip(columns, row, strict=True))

        for field in ("source_datetime_utc", "tipoff_utc"):
            if game[field] is not None:
                game[field] = game[field].replace(tzinfo=UTC)

        is_home = game["home_team_id"] == team_id
        game["opponent_team_id"] = (
            game["away_team_id"] if is_home else game["home_team_id"]
        )
        game["opponent_team_name"] = (
            game["away_team_name"] if is_home else game["home_team_name"]
        )

        if game["neutral_site"] is True:
            game["site"] = "neutral"
        elif game["neutral_site"] is False:
            game["site"] = "home" if is_home else "away"
        else:
            game["site"] = None

        games.append(game)

    return {
        "team_id": team_id,
        "team_name": team[0],
        "season": season,
        "games": games,
    }

def _game_calendar_date(game, zone):
    if game["tipoff_utc"] is not None:
        return game["tipoff_utc"].astimezone(zone).date()

    match = re.fullmatch(
        r"(\d{1,2})/(\d{1,2})\s*-\s*TBD",
        (game["source_status_detail"] or "").strip(),
        flags=re.IGNORECASE,
    )

    if match is None or game["source_datetime_utc"] is None:
        raise ValueError(
            f"Cannot determine the schedule date for game {game['game_id']}"
        )

    month, day = map(int, match.groups())
    source_day = game["source_datetime_utc"].astimezone(UTC).date()
    candidates = []

    for year in (source_day.year - 1, source_day.year, source_day.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue

    if not candidates:
        raise ValueError(
            f"Invalid schedule date for game {game['game_id']}"
        )

    return min(
        candidates,
        key=lambda candidate: abs((candidate - source_day).days),
    )

def get_next_game(
    connection,
    team_id,
    season,
    reference_time,
    timezone="America/Chicago",
):
    if not isinstance(reference_time, datetime):
        raise TypeError("reference_time must be a datetime")
    if reference_time.tzinfo is None or reference_time.utcoffset() is None:
        raise ValueError("reference_time must include a timezone")

    zone = ZoneInfo(timezone)
    reference_utc = reference_time.astimezone(UTC)
    today = reference_time.astimezone(zone).date()
    schedule = get_team_schedule(connection, team_id, season)
    upcoming = []

    for game in schedule["games"]:
        if game["status"] != "STATUS_SCHEDULED":
            continue

        tipoff = game["tipoff_utc"]

        if tipoff is not None and tipoff <= reference_utc:
            continue

        game_day = _game_calendar_date(game, zone)

        if game_day < today:
            continue

        if tipoff is None and game_day == today:
            raise ValueError(
                f"Game {game['game_id']} is scheduled today with a TBD "
                "tipoff; cannot determine whether it is still upcoming."
            )

        upcoming.append((game_day, game))

    if not upcoming:
        return None

    first_day = min(game_day for game_day, game in upcoming)
    first_games = [
        game for game_day, game in upcoming
        if game_day == first_day
    ]

    if len(first_games) == 1:
        return first_games[0]

    if any(game["tipoff_utc"] is None for game in first_games):
        raise ValueError(
            "Multiple games are scheduled on the next game date, "
            "and TBD tipoffs prevent determining their order."
        )

    return min(first_games, key=lambda game: game["tipoff_utc"])

def get_team_schedule_in_range(connection, team_id, season, date_range):
    schedule = get_team_schedule(connection, team_id, season)
    zone = ZoneInfo(date_range["timezone"])
    start = date_range["start_utc"]
    end = date_range["end_utc"]
    matches = []
    uncertain = []

    for game in schedule["games"]:
        tipoff = game["tipoff_utc"]

        if tipoff is not None:
            if start <= tipoff < end:
                matches.append(game)
            continue

        try:
            game_day = _game_calendar_date(game, zone)
        except ValueError:
            uncertain.append(game)
            continue

        day_start = datetime.combine(
            game_day, time.min, tzinfo=zone
        ).astimezone(UTC)
        day_end = datetime.combine(
            game_day + timedelta(days=1), time.min, tzinfo=zone
        ).astimezone(UTC)

        if start <= day_start and day_end <= end:
            matches.append(game)
        elif day_start < end and start < day_end:
            uncertain.append(game)

    return {
        **schedule,
        "games": matches,
        "uncertain_games": uncertain,
    }

def main():
    parser = argparse.ArgumentParser(description="Print a team's schedule")
    parser.add_argument("team_id")
    parser.add_argument("--season", type=int, default=2027)
    arguments = parser.parse_args()

    with duckdb.connect("data/basketball.duckdb", read_only=True) as connection:
        try:
            schedule = get_team_schedule(
                connection,
                arguments.team_id,
                arguments.season,
            )
        except ValueError as error:
            parser.error(str(error))

    print(schedule["team_name"])
    print(
        f"Season: {arguments.season - 1}-{arguments.season % 100:02d} "
        f"| Games: {len(schedule['games'])}"
    )

    if not schedule["games"]:
        print("No games recorded for this season.")
        return

    timezone = ZoneInfo('America/Chicago')

    for game in schedule["games"]:
        if game["tipoff_utc"] is None:
            when = game["source_status_detail"] or "Time TBD"
        else:
            when = game["tipoff_utc"].astimezone(timezone).strftime(
                "%Y-%m-%d %I:%M %p %Z"
            )

        site = game["site"] or "Location TBD"
        venue = game["venue"] or "Venue TBD"

        print(
            f"{when} | {game['opponent_team_name']} | {site} | {venue}"
        )

if __name__ == "__main__":
    main()
