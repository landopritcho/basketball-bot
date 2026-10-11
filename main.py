import json
from urllib.parse import urlencode
from urllib.request import urlopen
from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import duckdb

BASE_TIMEZONE = "America/Chicago"

BASE_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
)

def fetch_json(path, **parameters):
    url = f"{BASE_URL}/{path}?{urlencode(parameters)}"

    with urlopen(url, timeout=30) as response:
        return json.load(response)

def extract_game(event):
    if len(event["competitions"]) != 1:
        raise ValueError(f"Unexpected competition count: {event['id']}")

    competition = event["competitions"][0]
    teams = {
        competitor["homeAway"]: competitor["team"]
        for competitor in competition["competitors"]
    }

    if len(competition["competitors"]) != 2 or set(teams) != {"home", "away"}:
        raise ValueError(f"Unexpected team assignments: {event['id']}")

    timestamp = datetime.fromisoformat(competition["date"])
    if timestamp.tzinfo is None:
        raise ValueError(f"TimeStamp has no timezone: {event['id']}")

    timestamp = timestamp.astimezone(UTC)
    time_valid = competition.get("timeValid")

    return {
        "game_id": event["id"],
        "season": event["season"]["year"],
        "home_team_id": teams["home"]["id"],
        "home_team_name": teams["home"]["displayName"],
        "away_team_id": teams["away"]["id"],
        "away_team_name": teams["away"]["displayName"],
        "source_datetime_utc": timestamp,
        "time_valid": time_valid,
        "tipoff_utc": timestamp if time_valid is True else None,
        "neutral_site": competition.get("neutralSite"),
        "venue": competition.get("venue", {}).get("fullName"),
        "status": competition["status"]["type"]["name"],
        "source_status_detail": competition["status"]["type"].get("detail"),
    }

def save_schedule(games):
    if not games:
        raise ValueError("Refusing to replace the schedule with no games")

    data_directory = Path("data")
    data_directory.mkdir(exist_ok=True)

    with duckdb.connect(str(data_directory / "basketball.duckdb")) as connection:
        connection.execute("SET TimeZone = 'UTC'")
        connection.execute("BEGIN TRANSACTION")

        connection.execute("""
            CREATE OR REPLACE TABLE games (
                game_id VARCHAR PRIMARY KEY,
                season INTEGER,
                home_team_id VARCHAR,
                home_team_name VARCHAR,
                away_team_id VARCHAR,
                away_team_name VARCHAR,
                source_datetime_utc TIMESTAMPTZ,
                time_valid BOOLEAN,
                tipoff_utc TIMESTAMPTZ,
                neutral_site BOOLEAN,
                venue VARCHAR,
                status VARCHAR,
                source_status_detail VARCHAR
            )
        """)

        connection.executemany("""
            INSERT INTO games VALUES (
                $game_id,
                $season,
                $home_team_id,
                $home_team_name,
                $away_team_id,
                $away_team_name,
                $source_datetime_utc,
                $time_valid,
                $tipoff_utc,
                $neutral_site,
                $venue,
                $status,
                $source_status_detail,
            )
        """, games)

        connection.execute("COMMIT")
        connection.execute("""
            COPY games TO 'data/schedule.parquet' (FORMAT PARQUET)
        """)

    print(f"Saved {len(games)} games to DuckDB and Parquet")

def main():
    season = 2027
    season_type = 2

    directory = fetch_json("teams", limit=1000, groups=50)
    teams = directory["sports"][0]["leagues"][0]["teams"]
    
    if not teams:
        raise ValueError("ESPN returned an empty team directory")

    print(f"Season: {season - 1}-{season % 100:02d}")
    print(f"Teams: {len(teams)}")

    games_by_id = {}
    duplicate_count = 0

    for index, entry in enumerate(teams, start=1):
        team = entry["team"]
        print(
            f"[{index}/{len(teams)}] Fetching {team['displayName']}",
            flush=True,
        )

        schedule = fetch_json(
            f"teams/{team['id']}/schedule",
            season=season,
            seasontype=season_type,
        )

        requested = schedule["requestedSeason"]
        if requested["year"] != season or requested["type"] != season_type:
            raise ValueError(
                f"Unexpected season for {team['displayName']}: {requested}"
            )

        for event in schedule["events"]:
            game = extract_game(event)

            if game["season"] != season:
                raise ValueError(
                    f"Unexpected season for game {game['game_id']}"
                )

            previous = games_by_id.get(game["game_id"])
            if previous is not None:
                if previous != game:
                    differences = [
                        field for field in game if previous[field] != game[field]
                    ]
                    raise ValueError(
                        f"Conflicting records for game {game['game_id']} "
                        f"while fetching {team['displayName']}: "
                        f"{', '.join(differences)}"
                    )

                duplicate_count += 1
            else:
                games_by_id[game["game_id"]] = game

        print(f"    Returned {len(schedule['events'])} games")

    games = sorted(
        games_by_id.values(),
        key=lambda game: (game["source_datetime_utc"], game["game_id"]),
    )

    print(f"Unique games: {len(games)}")
    print(f"Duplicate appearances removed: {duplicate_count}")
    save_schedule(games)

    timezone = ZoneInfo("America/Chicago")

    for game in games:
        tipoff = game["tipoff_utc"]

        if tipoff is None:
            when = "Time TBD"
        else:
            when = tipoff.astimezone(timezone).strftime(
                "%Y-%m-%d %I:%M %p %Z"
            )

        matchup = f"{game['away_team_name']} @ {game['home_team_name']}"
        if game["neutral_site"]:
            matchup = (
                f"{game['away_team_name']} vs {game['home_team_name']}"
            )

        print(game["game_id"], when, matchup)

if __name__ == "__main__":
    main()
