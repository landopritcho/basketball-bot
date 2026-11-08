CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    location TEXT,
    name TEXT,
    abbreviation TEXT,
    display_name TEXT,
    short_display_name TEXT,
    primary_color TEXT,
    alternate_color TEXT,
    conference_id TEXT
);
