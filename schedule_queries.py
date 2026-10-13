import argparse
from datetime import UTC, date
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
