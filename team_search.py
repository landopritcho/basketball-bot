import re

import duckdb
from rapidfuzz import fuzz, process

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Label, TextArea

def normalize_search_text(text):
    return " ".join(re.findall(r"\w+", text.casefold()))

class TeamSearch:
    def __init__(self, rows):
        self.team_names = {}
        self.aliases = {}

        for team_id, name, labels in rows:
            self.team_names[team_id] = name

            for label in sorted(labels):
                normalized = normalize_search_text(label)
                if normalized:
                    self.aliases.setdefault(normalized, {})[team_id] = label

        self.choices = sorted(self.aliases)

    def search(self, query, limit=10, score_cutoff=0):
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if not 0 <= score_cutoff <= 100:
            raise ValueError("score_cutoff must be between 0 and 100")
        
        normalized = normalize_search_text(query)
        if not normalized:
            return []

        method_order = {"exact": 0, "phrase": 1, "fuzzy": 2}

        def rank(match):
            return (
                method_order[match["method"]],
                -match["score"],
                match["name"].casefold(),
                match["team_id"],
            )

        matches = {}
        for alias, score, _ in process.extract_iter(
            normalized,
            self.choices,
            scorer=fuzz.WRatio,
            score_cutoff=score_cutoff,
        ):
            if alias == normalized:
                method = "exact"
            elif f" {normalized} " in f" {alias} ":
                method = "phrase"
            else:
                method = "fuzzy"

            for team_id, label in self.aliases[alias].items():
                candidate = {
                    "team_id": team_id,
                    "name": self.team_names[team_id],
                    "matched_label": label,
                    "score": score,
                    "method": method,
                }

                previous = matches.get(team_id)
                if previous is None or rank(candidate) < rank(previous):
                    matches[team_id] = candidate

        return sorted(matches.values(), key=rank)[:limit]

def load_team_search(database_path="data/basketball.duckdb"):
    with duckdb.connect(database_path, read_only=True) as connection:
        rows = connection.execute("""
            SELECT team_id, name, search_labels
            FROM teams
            ORDER BY team_id
        """).fetchall()

    return TeamSearch(rows)

def main():
    searcher = load_team_search()
    result_text = ""
    bindings = KeyBindings()

    @bindings.add("c-c")
    @bindings.add("c-d")
    def exit_search(event):
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
            f"Search {len(searcher.team_names):,} teams. "
            "Ctrl-C exits; results update as you type.",
            wrap_lines=False,
        ),
        input_field,
        Window(
            content=FormattedTextControl(lambda: result_text),
            height=10,
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

        matches = searcher.search(buffer.text, limit=10)
        result_text = "\n".join(
            f"{match['name']} (ID {match['team_id']}) | "
            f"{match['score']:.1f} | {match['method']} | "
            f"matched {match['matched_label']!r}"
            for match in matches
        )

        if not matches and buffer.text.strip():
            result_text = "No matching teams."

        application.invalidate()

    input_field.buffer.on_text_changed += update_results
    application.run()

if __name__ == "__main__":
    main()
