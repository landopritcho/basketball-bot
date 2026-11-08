CREATE TABLE upcoming_games (
    id INTEGER PRIMARY KEY,
    tipoff INTEGER,
    long_description TEXT,
    abbreviated_description TEXT,
    venue TEXT,
    title TEXT,
    broadcast_channel TEXT,
    home_team_id TEXT,
    away_team_id TEXT
);
