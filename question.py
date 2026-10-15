from datetime import datetime
from zoneinfo import ZoneInfo

import duckdb
from prompt_toolkit import PromptSession

from schedule_parser import resolve_schedule_question
from schedule_queries import (
    get_next_game,
    get_team_schedule,
    get_team_schedule_in_range,
)
from team_search import load_team_search

DATABASE_PATH = "data/basketball.duckdb"
SEASON = 2027
TIMEZONE = "America/Chicago"

def choose_team(session, candidates):
    print("Which team did you mean?")

    for number, team in enumerate(candidates, start=1):
        print(f"{number}. {team['name']}")

    while True:
        choice = session.prompt("Team number (Enter cancels): ").strip()

        if not choice:
            return None

        if choice.isdecimal():
            number = int(choice)
            if 1 <= number <= len(candidates):
                return candidates[number - 1]

        print(f"Enter a number from 1 to {len(candidates)}")

def execute_request(connection, request, reference_time, zone):
    if request["intent"] == "next_game":
        game = get_next_game(
            connection,
            request["team_id"],
            SEASON,
            reference_time,
            timezone=zone.key,
        )
        return {
            "team_name": request["team_name"],
            "season": SEASON,
            "games": [] if game is None else [game],
        }

    if request["intent"] != "team_schedule":
        raise ValueError(f"Unsupported intent: {request['intent']}")

    if request["date_range"] is not None:
        return get_team_schedule_in_range(
            connection,
            request["team_id"],
            SEASON,
            request["date_range"],
        )

    return get_team_schedule(connection, request["team_id"], SEASON)

def format_game(game, zone):
    if game["tipoff_utc"] is None:
        when = game["source_status_detail"] or "Date/time TBD"
    else:
        when = game["tipoff_utc"].astimezone(zone).strftime(
            "%Y-%m-%d %I:%M:%S %p %Z"
        )

    site = game["site"] or "Location TBD"
    venue = game["venue"] or "Venue TBD"

    return f"{when} | {game['opponent_team_name']} | {site} | {venue}"

def print_answer(answer, zone):
    season = answer["season"]
    games = answer["games"]
    uncertain = answer.get("uncertain_games", [])

    print(
        f"\n{answer['team_name']} | "
        f"Season: {season - 1}-{season % 100:02d}"
    )

    if games:
        for game in games:
            print(format_game(game, zone))
    elif uncertain:
        print("No confirmed matching games.")
    else:
        print("No matching games recorded.")

    if uncertain:
        print("\nThese games may match; their date or tipoff is unconfirmed:")
        for game in uncertain:
            print(format_game(game, zone))

    print()

def main():
    zone = ZoneInfo(TIMEZONE)
    session = PromptSession()

    try:
        with duckdb.connect(DATABASE_PATH, read_only=True) as connection:
            searcher = load_team_search(DATABASE_PATH)

            print(
                f"Basketball schedules: {SEASON-1}-{SEASON % 100:02d}."
                "Enter a question; 'quit' exits."
            )

            while True:
                question = session.prompt("> ").strip()

                if question.casefold() in {"quit", "exit"}:
                    break
                if not question:
                    continue

                reference_time = datetime.now(zone)
                resolved = resolve_schedule_question(
                    question,
                    searcher,
                    reference_time,
                    timezone=zone.key,
                    season=SEASON,
                )

                if resolved["status"] == "choose_team":
                    team = choose_team(session, resolved["candidates"])
                    if team is None:
                        continue

                    request = {
                        **resolved["request"],
                        "team_id": team["team_id"],
                        "team_name": team["name"],
                    }
                elif resolved["status"] == "ready":
                    request = resolved["request"]
                else:
                    print(resolved["message"])
                    continue

                try:
                    answer = execute_request(
                        connection,
                        request,
                        reference_time,
                        zone,
                    )
                except (ValueError, OverflowError) as error:
                    print(f"Cannot answer: {error}")
                    continue

                print_answer(answer, zone)

    except (EOFError, KeyboardInterrupt):
        print()
    except duckdb.Error as error:
        print(f"Database error: {error}")

if __name__ == "__main__":
    main()
