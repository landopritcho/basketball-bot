CREATE TABLE live_games (
    id INTEGER PRIMARY KEY,
    venue TEXT,
    title TEXT,
    broadcast_channel TEXT,
    home_team_id TEXT,
    away_team_id TEXT,
    home_team_score INTEGER,
    away_team_score INTEGER,
    display_clock TEXT,
    half TEXT,
    status_description TEXT,
    status_detail TEXT,
    status_short_detail TEXT
);
