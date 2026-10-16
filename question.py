from datetime import datetime
from zoneinfo import ZoneInfo

import duckdb
from prompt_toolkit import PromptSession

from query_execution import bind_game_query, execute_game_query
from semantic_parser import SemanticParser
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

def format_game(game, zone):
    if game["tipoff_utc"] is not None:
        when = game["tipoff_utc"].astimezone(zone).strftime(
            "%Y-%m-%d %I:%M:%S %p %Z"
        )
    elif game["calendar_date"] is not None:
        when = f"{game['calendar_date'].isoformat()} - Time TBD"
    else:
        when = game['source_status_detail'] or "Date/time TBD"

    away = game["away_team_name"]
    home = game["home_team_name"]

    if game["neutral_site"] is False:
        matchup = f"{away} @ {home}"
    elif game["neutral_site"] is True:
        matchup = f"{away} vs {home} | neutral"
    else:
        matchup = f"{away} vs {home} | Home/away designation TBD"

    venue = game["venue"] or "Venue TBD"
    return f"{when} | {matchup} | {venue}"

def print_answer(answer, zone):
    season = answer["season"]
    games = answer["games"]
    uncertain = answer["uncertain_games"]
    heading = answer["team_name"] or "All teams"

    print(f"\n{heading} | Season: {season - 1}-{season % 100:02d}")

    if games:
        for game in games:
            print(format_game(game, zone))
    elif uncertain:
        print("No confirmed matching games.")
    else:
        print("No matching games recorded.")

    if uncertain:
        print("\nThese games may match; some schedule information is unconfirmed:")
        for game in uncertain:
            print(format_game(game, zone))
            print(f"  {' '.join(game['uncertain_reasons'])}")

    print()

def main():
    zone = ZoneInfo(TIMEZONE)
    session = PromptSession()

    try:
        with duckdb.connect(DATABASE_PATH, read_only=True) as connection:
            parser = SemanticParser(load_team_search(DATABASE_PATH))

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

                try:
                    meanings = parser.parse(question)
                    if len(meanings) != 1:
                        raise ValueError(
                            "The question has multiple interpretations. "
                            "Please rephrase it more specifically."
                        )

                    meaning = meanings[0]
                    candidates = meaning["team_candidates"]

                    if candidates is not None and len(candidates) > 1:
                        team = choose_team(session, candidates)
                        if team is None:
                            continue
                        meaning = {**meaning, "team_candidates": [team]}

                    query = bind_game_query(
                        meaning,
                        SEASON,
                        reference_time,
                        timezone=zone.key,
                    )
                    answer = execute_game_query(connection, query)
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
