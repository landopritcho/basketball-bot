CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    location TEXT,
    name TEXT,
    abbreviation TEXT,
    display_name TEXT,
    slug TEXT,
    primary_color TEXT,
    alternate_color TEXT,
    rank INTEGER CHECK (rank IS NULL OR rank between 1 and 25)
);
